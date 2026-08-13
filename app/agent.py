# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
from zoneinfo import ZoneInfo

import httpx
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.cloud import storage
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.rss_manager import add_rss_source, fetch_live_rss_content, get_rss_sources
from app.template_manager import (
    apply_template_selection,
    get_active_template,
    get_template_options,
)

MODEL = "gemini-3.6-flash"

AGENT_ENGINE_RESOURCE_NAME = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/397519156454/locations/us-east1/reasoningEngines/1655864511430656000",
)

# 1. Build system prompt using A2uiSchemaManager v0.8 and BasicCatalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are BrewCraft, a specialized concierge and portfolio intelligence assistant. "
        "You leverage cross-session memory via Vertex AI Memory Bank to persist visitor intent signals, "
        "including: topic interests (AI, agentic systems, cybersecurity, specialty coffee origins), "
        "interaction history (blogs, keynotes, awards, past brewing queries), and transaction data "
        "(consultations, advisory services, book purchases, bean orders)."
    ),
    workflow_description=(
        "Analyze requests and return structured UI when appropriate. You can fetch and present UI templates "
        "using fetch_ui_template_options, apply a UI template with user consent via apply_ui_template_with_consent, "
        "write and execute Python scripts in a secure sandbox, capture lead inquiries using submit_lead_inquiry, "
        "download image/video assets via download_media_asset, generate visuals via generate_portfolio_visual, "
        "generate video clips via generate_portfolio_video, search portfolio assets, and fetch live blog posts."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


def search_coffee_catalog(
    query: str = "", roast_level: str = "", max_price: float = 0.0
) -> str:
    """Searches the specialty coffee catalog for beans matching criteria.

    Args:
        query: General search query, origin, or flavor note (e.g., 'Ethiopia', 'berry', 'chocolate').
        roast_level: Filter by roast level ('light', 'medium', 'dark').
        max_price: Maximum price limit in USD per 12oz bag.

    Returns:
        Formatted catalog matches with tasting notes, origin, roast, and price.
    """
    catalog = [
        {
            "name": "Ethiopia Yirgacheffe Worka",
            "origin": "Ethiopia",
            "roast": "light",
            "notes": "Jasmine, bergamot, blueberry, bright acidity",
            "price": 22.0,
        },
        {
            "name": "Colombia Huila Reserve",
            "origin": "Colombia",
            "roast": "medium",
            "notes": "Red apple, caramel, milk chocolate, balanced",
            "price": 19.5,
        },
        {
            "name": "Guatemala Antigua Pastoral",
            "origin": "Guatemala",
            "roast": "medium-dark",
            "notes": "Dark chocolate, toasted almond, orange zest",
            "price": 18.0,
        },
        {
            "name": "Kenya Nyeri AA Peaberry",
            "origin": "Kenya",
            "roast": "light",
            "notes": "Black currant, grapefruit, juicy tomato, cane sugar",
            "price": 24.5,
        },
    ]

    results = []
    for item in catalog:
        if roast_level and roast_level.lower() not in item["roast"].lower():
            continue
        if max_price > 0 and item["price"] > max_price:
            continue
        if query and not (
            query.lower() in item["name"].lower()
            or query.lower() in item["origin"].lower()
            or query.lower() in item["notes"].lower()
        ):
            continue
        results.append(
            f"• {item['name']} ({item['origin']}) - {item['roast'].capitalize()} Roast - "
            f"${item['price']:.2f} | Notes: {item['notes']}"
        )

    if not results:
        return f"No beans found matching query '{query}' (roast: {roast_level}, max price: ${max_price:.2f})."
    return "Found matching specialty coffee beans:\n" + "\n".join(results)


def calculate_brew_recipe(
    method: str, coffee_grams: float, water_ratio: float = 16.0
) -> str:
    """Calculates water target, bloom amount, and grind recommendation for a brew method.

    Args:
        method: Brew method name (e.g., 'V60', 'Espresso', 'AeroPress', 'French Press').
        coffee_grams: Amount of ground coffee in grams.
        water_ratio: Water-to-coffee ratio (default: 16.0 for 1:16 pour over).

    Returns:
        A detailed brew recipe with water target, bloom, and grind recommendations.
    """
    total_water = coffee_grams * water_ratio
    bloom_water = coffee_grams * 2.5

    grind_guides = {
        "v60": "Medium-fine (like sea salt)",
        "espresso": "Fine (like powdered sugar)",
        "aeropress": "Medium-fine",
        "french press": "Coarse (like breadcrumbs)",
        "chemex": "Medium-coarse",
    }
    grind = grind_guides.get(method.lower(), "Medium")

    return (
        f"☕ Brew Recipe for {method.upper()} ({coffee_grams}g coffee):\n"
        f"• Total Water: {total_water:.1f}g (Ratio 1:{water_ratio:.1f})\n"
        f"• Bloom Stage: {bloom_water:.1f}g water for 45 seconds\n"
        f"• Recommended Grind: {grind}\n"
        f"• Water Temp: 200°F - 205°F (93°C - 96°C)"
    )


def search_portfolio_and_assets(topic: str = "", category: str = "") -> str:
    """Searches portfolio assets including blogs, keynotes, research talks, and industry awards.

    Args:
        topic: Topic of interest (e.g., 'AI', 'agentic systems', 'cybersecurity', 'coffee tech').
        category: Asset category filter (e.g., 'blog', 'talk', 'award', 'whitepaper').

    Returns:
        List of matching portfolio assets with relevance rankings.
    """
    assets = [
        {
            "title": "Architecting Autonomous Agentic Systems with Gemini ADK",
            "topic": "agentic systems",
            "category": "blog",
            "summary": "Deep dive into multi-agent orchestration, function calling, and cross-session memory bank integration.",
            "link": "https://example.com/blogs/agentic-systems",
        },
        {
            "title": "Zero-Trust Cybersecurity in Agent Workflows",
            "topic": "cybersecurity",
            "category": "talk",
            "summary": "Keynote on safeguarding agent permissions, secret sanitization, and enterprise compliance.",
            "link": "https://example.com/talks/cybersecurity-agents",
        },
        {
            "title": "AI Innovation Award 2025: Next-Gen Enterprise Agents",
            "topic": "AI",
            "category": "award",
            "summary": "Recognized for pioneering production-grade multi-turn reasoning and personalization.",
            "link": "https://example.com/awards/ai-innovation-2025",
        },
        {
            "title": "BrewCraft: AI-Driven Precision Coffee Extraction",
            "topic": "coffee tech",
            "category": "whitepaper",
            "summary": "Applying sensory algorithms and IoT sensor feeds to coffee brew parameter calculation.",
            "link": "https://example.com/papers/brewcraft-ai",
        },
    ]

    results = []
    for asset in assets:
        if category and category.lower() not in asset["category"].lower():
            continue
        if topic and not (
            topic.lower() in asset["topic"].lower()
            or topic.lower() in asset["title"].lower()
            or topic.lower() in asset["summary"].lower()
        ):
            continue
        results.append(
            f"• [{asset['category'].upper()}] {asset['title']} (Topic: {asset['topic']})\n"
            f"  Summary: {asset['summary']}\n"
            f"  Link: {asset['link']}"
        )

    if not results:
        return f"No portfolio assets found for topic '{topic}' and category '{category}'."
    return "Matched Portfolio Assets:\n" + "\n\n".join(results)


def get_services_and_consultations(service_type: str = "") -> str:
    """Retrieves available consulting packages, advisory services, and publication offerings.

    Args:
        service_type: Optional filter (e.g., 'consultation', 'advisory', 'book', 'workshop').

    Returns:
        Available services, pricing, and fast-track conversion details.
    """
    services = [
        {
            "name": "1-on-1 AI & Agentic Architecture Strategy Session",
            "type": "consultation",
            "details": "60-minute deep dive on designing autonomous agent workflows and memory architecture.",
            "price": "$350",
            "action": "Fast-track booking link available.",
        },
        {
            "name": "Enterprise Cybersecurity & Agent Audit",
            "type": "advisory",
            "details": "Comprehensive evaluation of enterprise agent security, data boundaries, and authorization.",
            "price": "$2,500",
            "action": "Request customized proposal.",
        },
        {
            "name": "Building Agentic Systems with Gemini (Hardcover & eBook)",
            "type": "book",
            "details": "Practical guide covering ADK, Memory Bank, RAG, and Cloud Run production deployments.",
            "price": "$49.99",
            "action": "Instant digital download or physical order.",
        },
    ]

    results = []
    for s in services:
        if service_type and service_type.lower() not in s["type"].lower():
            continue
        results.append(
            f"• {s['name']} [{s['type'].upper()}] - {s['price']}\n"
            f"  Details: {s['details']}\n"
            f"  Flow: {s['action']}"
        )

    return "Available Services & Offerings:\n" + "\n\n".join(results)


def submit_lead_inquiry(
    name: str,
    email: str,
    topic_interest: str = "General Inquiry",
    message: str = "",
    service_type: str = "general",
) -> str:
    """Submits a visitor lead inquiry or consultation booking request.

    Args:
        name: Full name of the visitor or client.
        email: Contact email address.
        topic_interest: Topic interest (e.g., 'AI', 'agentic systems', 'cybersecurity', 'coffee tech').
        message: Specific inquiry details, project summary, or booking request message.
        service_type: Type of inquiry ('consultation', 'advisory', 'speaking', 'general').

    Returns:
        Confirmation message and reference tracking ID for the submitted lead.
    """
    lead_id = f"LEAD-{int(datetime.datetime.now().timestamp())}"
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)
    leads_file = os.path.join(data_dir, "leads.json")

    leads = []
    if os.path.exists(leads_file):
        try:
            with open(leads_file, "r", encoding="utf-8") as f:
                leads = json.load(f)
        except Exception:
            leads = []

    new_lead = {
        "lead_id": lead_id,
        "name": name,
        "email": email,
        "topic_interest": topic_interest,
        "service_type": service_type,
        "message": message,
        "submitted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    leads.append(new_lead)

    with open(leads_file, "w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2)

    return (
        f"✅ Lead inquiry submitted successfully! Reference ID: {lead_id}.\n"
        f"Harsh Verma will follow up at {email} regarding your {service_type} inquiry on '{topic_interest}'."
    )


def download_media_asset(media_url: str, filename: str = "") -> str:
    """Downloads an image or video asset from a URL and saves it to local media storage.

    Args:
        media_url: Public URL of the image or video to download.
        filename: Optional filename to save as (e.g. 'keynote_diagram.png', 'demo_video.mp4').

    Returns:
        Confirmation message with local saved path and file size.
    """
    try:
        media_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "media")
        os.makedirs(media_dir, exist_ok=True)

        if not filename:
            filename = media_url.split("/")[-1].split("?")[0] or f"asset_{int(datetime.datetime.now().timestamp())}.bin"

        save_path = os.path.join(media_dir, filename)

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(media_url)
            resp.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(resp.content)

        file_size_kb = len(resp.content) / 1024
        return (
            f"📥 Media asset downloaded successfully!\n"
            f"• Saved To: {save_path}\n"
            f"• File Size: {file_size_kb:.1f} KB\n"
            f"• Content Type: {resp.headers.get('content-type', 'unknown')}"
        )
    except Exception as e:
        return f"Failed to download media asset from '{media_url}': {str(e)}"


def generate_portfolio_visual(prompt: str, tool_context: ToolContext = None) -> str:
    """Generates an image for portfolio blogs, book covers, award highlights, or coffee tech items using gemini-3.1-flash-lite-image in global location.

    Args:
        prompt: Detailed description of the image to generate (e.g. 'A futuristic AI coffee roasting lab with glowing blue sensors').

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage.
    """
    try:
        client = genai.Client(vertexai=True, project="qwiklabs-gcp-04-623529d65701", location="global")
        res = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=f"Generate an image for portfolio asset: {prompt}",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        for part in res.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

        if not image_bytes:
            return "Failed to generate image bytes."

        object_name = f"generated_asset_{int(datetime.datetime.now().timestamp())}.jpg"

        # 1. Save artifact to Playground's Artifacts panel if tool_context is provided
        if tool_context and hasattr(tool_context, "save_artifact"):
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=object_name, artifact=image_part)

        # 2. Upload image bytes to hardcoded public Cloud Storage bucket
        bucket_name = "brewcraft-portfolio-media-qwiklabs-gcp-04-623529d65701"
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"
        return f"🎨 Visual generated successfully!\n• Public URL: {public_url}"
    except Exception as e:
        return f"Image generation failed: {str(e)}"


def generate_portfolio_video(prompt: str, tool_context: ToolContext = None) -> str:
    """Generates a short video for portfolio items, keynote demos, or coffee roasting visuals using Google's Omni model (gemini-omni-flash-preview) in global location.

    Args:
        prompt: Detailed description of the video to generate (e.g. 'A 5-second cinematic clip of coffee beans roasting in slow motion with rising steam').

    Returns:
        The public HTTPS URL of the uploaded video in Cloud Storage.
    """
    try:
        client = genai.Client(vertexai=True, project="qwiklabs-gcp-04-623529d65701", location="global")
        res = client.models.generate_content(
            model="gemini-omni-flash-preview",
            contents=f"Generate a short video for portfolio asset: {prompt}",
            config=types.GenerateContentConfig(
                response_modalities=["VIDEO"],
            ),
        )

        video_bytes = None
        mime_type = "video/mp4"
        for part in res.candidates[0].content.parts:
            if part.inline_data:
                video_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

        if not video_bytes:
            return "Failed to generate video bytes."

        object_name = f"generated_video_{int(datetime.datetime.now().timestamp())}.mp4"

        # 1. Save artifact to Playground's Artifacts panel if tool_context is provided
        if tool_context and hasattr(tool_context, "save_artifact"):
            video_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=object_name, artifact=video_part)

        # 2. Upload video bytes to hardcoded public Cloud Storage bucket
        bucket_name = "brewcraft-portfolio-media-qwiklabs-gcp-04-623529d65701"
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"
        return f"🎥 Video generated successfully!\n• Public URL: {public_url}"
    except Exception as e:
        return f"Video generation failed: {str(e)}"


def register_rss_feed_source(name: str, feed_url: str, category: str = "Tech & AI") -> str:
    """Registers a new RSS or Atom feed source for real-time blog post and research article fetching.

    Args:
        name: Name of the blog, publisher, or author (e.g. 'Harsh Verma AI Blog', 'Google DeepMind Blog').
        feed_url: Valid RSS or Atom feed XML URL (e.g. 'https://blog.google/technology/ai/rss/').
        category: Subject category (e.g. 'AI', 'Cybersecurity', 'Agentic Systems', 'Coffee Tech').

    Returns:
        Confirmation status and feed summary details.
    """
    res = add_rss_source(name=name, feed_url=feed_url, category=category)
    return res["message"]


def fetch_live_tech_and_rss_content(query: str = "", category: str = "", limit: int = 5) -> str:
    """Fetches and parses live articles and posts from all registered RSS feed sources in real time.

    Args:
        query: Search term or keyword (e.g. 'agentic', 'cybersecurity', 'ADK', 'brewing').
        category: Subject category filter (e.g. 'AI', 'Cybersecurity').
        limit: Maximum number of articles to return.

    Returns:
        Live parsed articles with titles, publication dates, summaries, and links.
    """
    return fetch_live_rss_content(query=query, category=category, limit=limit)


def fetch_ui_template_options() -> str:
    """Fetches and displays modern UI template options for the project interface.

    Returns:
        List of 2-3 curated UI templates (Sleek Dark Mode Artisan, Glassmorphism Tech Hub, Neo-Brutalist Dashboard).
    """
    options = get_template_options()
    active = get_active_template().get("active_template", {}).get("id")
    lines = []
    for opt in options:
        is_current = " [ACTIVE]" if opt["id"] == active else ""
        lines.append(
            f"🎨 {opt['name']}{is_current} (ID: '{opt['id']}')\n"
            f"• Description: {opt['description']}\n"
            f"• Styles: BG: {opt['styles']['bg_color']} | Accent: {opt['styles']['accent_color']} | Font: {opt['styles']['font_family']}"
        )
    return "Available Project UI Templates:\n\n" + "\n\n".join(lines)


def apply_ui_template_with_consent(
    template_id: str, user_consent_confirmed: bool = False
) -> str:
    """Applies a project UI template after verifying user consent in the UI.

    Args:
        template_id: ID of the template ('artisan-dark', 'glassmorphism-tech', 'neo-brutalist').
        user_consent_confirmed: Must be True if the user explicitly agreed/consented to changing the UI theme/template.

    Returns:
        Confirmation status or consent prompt.
    """
    res = apply_template_selection(
        template_id=template_id, user_consent_confirmed=user_consent_confirmed
    )
    if res.get("requires_consent"):
        return f"⚠️ {res['message']}"
    if res.get("success"):
        return f"✨ {res['message']}"
    return f"❌ Error: {res.get('error')}"


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: After each turn, send the session to Memory Bank for extraction."""
    await callback_context.add_session_to_memory()
    return None


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME,
    ),
    instruction=instruction,
    tools=[
        search_coffee_catalog,
        calculate_brew_recipe,
        search_portfolio_and_assets,
        get_services_and_consultations,
        submit_lead_inquiry,
        download_media_asset,
        generate_portfolio_visual,
        generate_portfolio_video,
        register_rss_feed_source,
        fetch_live_tech_and_rss_content,
        fetch_ui_template_options,
        apply_ui_template_with_consent,
        PreloadMemoryTool(),
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
