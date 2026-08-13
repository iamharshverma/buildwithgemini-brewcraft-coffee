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
from typing import Any, Dict, List, Optional
import feedparser

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SOURCES_FILE = os.path.join(DATA_DIR, "rss_sources.json")

DEFAULT_SOURCES = [
    {
        "id": "google-blog",
        "name": "Google Research & AI Blog",
        "feed_url": "https://blog.google/technology/ai/rss/",
        "category": "AI & Agentic Systems",
        "added_at": "2026-08-01T00:00:00Z",
    },
    {
        "id": "devto-ai",
        "name": "Dev.to AI & Machine Learning",
        "feed_url": "https://dev.to/feed/tag/ai",
        "category": "AI & Software Architecture",
        "added_at": "2026-08-01T00:00:00Z",
    },
]


def ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(SOURCES_FILE):
        save_rss_sources(DEFAULT_SOURCES)


def get_rss_sources() -> List[Dict[str, Any]]:
    ensure_data_dir()
    try:
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_SOURCES


def save_rss_sources(sources: List[Dict[str, Any]]) -> None:
    ensure_data_dir()
    with open(SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2)


def add_rss_source(name: str, feed_url: str, category: str = "General") -> Dict[str, Any]:
    sources = get_rss_sources()
    # Check for duplicate feed_url
    for s in sources:
        if s["feed_url"].strip().lower() == feed_url.strip().lower():
            return {"status": "exists", "source": s, "message": f"Feed URL '{feed_url}' is already registered."}

    # Validate feed by parsing it
    parsed = feedparser.parse(feed_url)
    if parsed.bozo and not parsed.entries:
        return {
            "status": "error",
            "message": f"Could not parse valid RSS/Atom entries from URL '{feed_url}'. Please verify the URL.",
        }

    new_source = {
        "id": f"feed-{len(sources) + 1}-{int(datetime.datetime.now().timestamp())}",
        "name": name.strip() or parsed.feed.get("title", "Untitled Feed"),
        "feed_url": feed_url.strip(),
        "category": category.strip() or "Tech & AI",
        "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "entry_count": len(parsed.entries),
    }

    sources.append(new_source)
    save_rss_sources(sources)
    return {"status": "success", "source": new_source, "message": f"Successfully added RSS feed '{new_source['name']}'!"}


def fetch_live_rss_content(query: str = "", category: str = "", limit: int = 5) -> str:
    sources = get_rss_sources()
    if not sources:
        return "No RSS sources registered yet. Please add an RSS feed source first."

    all_items = []

    for src in sources:
        if category and category.lower() not in src["category"].lower():
            continue

        try:
            feed = feedparser.parse(src["feed_url"])
            for entry in feed.entries[:limit]:
                title = entry.get("title", "Untitled")
                link = entry.get("link", "#")
                published = entry.get("published", entry.get("updated", "Recent"))
                summary = entry.get("summary", entry.get("description", ""))
                # Strip HTML tags simply if present
                import re
                clean_summary = re.sub("<[^<]+?>", "", summary)[:200]

                if query:
                    q = query.lower()
                    if q not in title.lower() and q not in clean_summary.lower() and q not in src["name"].lower():
                        continue

                all_items.append(
                    {
                        "source": src["name"],
                        "category": src["category"],
                        "title": title,
                        "link": link,
                        "published": published,
                        "summary": clean_summary.strip() + "...",
                    }
                )
        except Exception as e:
            continue

    if not all_items:
        return f"No live articles matched query '{query}' across registered RSS feeds."

    all_items = all_items[:limit]
    formatted = []
    for item in all_items:
        formatted.append(
            f"• [{item['category']}] {item['title']}\n"
            f"  Source: {item['source']} | Published: {item['published']}\n"
            f"  Summary: {item['summary']}\n"
            f"  Link: {item['link']}"
        )

    return f"📰 Live Tech & RSS Content ({len(formatted)} items):\n\n" + "\n\n".join(formatted)
