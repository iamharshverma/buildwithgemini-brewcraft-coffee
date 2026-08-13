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

TEMPLATES_CATALOG = {
    "artisan-dark": {
        "id": "artisan-dark",
        "name": "Sleek Dark Mode Artisan Luxury",
        "description": "Deep obsidian & espresso background with glowing amber micro-animations and gold accents. Designed for high-end portfolio showcase.",
        "styles": {
            "bg_color": "#0B0F19",
            "card_bg": "rgba(30, 41, 59, 0.7)",
            "accent_color": "#D97706",
            "primary_text": "#F8FAFC",
            "font_family": "Outfit, Inter, sans-serif",
            "border_radius": "12px",
        },
        "preview_url": "https://storage.googleapis.com/brewcraft-portfolio-media-qwiklabs-gcp-04-623529d65701/artisan_dark_preview.png",
    },
    "glassmorphism-tech": {
        "id": "glassmorphism-tech",
        "name": "Vibrant Glassmorphism Coffee & Tech Hub",
        "description": "Modern translucent frosted glass panels with dynamic indigo-to-rose gradients and subtle glow borders.",
        "styles": {
            "bg_color": "linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)",
            "card_bg": "rgba(255, 255, 255, 0.08)",
            "accent_color": "#818CF8",
            "primary_text": "#F1F5F9",
            "font_family": "Inter, system-ui, sans-serif",
            "border_radius": "16px",
            "backdrop_filter": "blur(16px)",
        },
        "preview_url": "https://storage.googleapis.com/brewcraft-portfolio-media-qwiklabs-gcp-04-623529d65701/glassmorphism_preview.png",
    },
    "neo-brutalist": {
        "id": "neo-brutalist",
        "name": "Minimalist Modern Neo-Brutalist Dashboard",
        "description": "Bold typography, crisp 2px black borders, high-impact monochrome layout with energetic electric-amber highlights.",
        "styles": {
            "bg_color": "#F8FAFC",
            "card_bg": "#FFFFFF",
            "accent_color": "#F59E0B",
            "primary_text": "#0F172A",
            "font_family": "Roboto, Space Grotesk, sans-serif",
            "border_radius": "4px",
            "border_style": "2px solid #0F172A",
        },
        "preview_url": "https://storage.googleapis.com/brewcraft-portfolio-media-qwiklabs-gcp-04-623529d65701/neo_brutalist_preview.png",
    },
}


def get_template_options() -> list[dict]:
    """Returns available UI template options."""
    return list(TEMPLATES_CATALOG.values())


def apply_template_selection(template_id: str, user_consent_confirmed: bool) -> dict:
    """Applies and saves the selected UI template if user consent is confirmed."""
    if template_id not in TEMPLATES_CATALOG:
        return {
            "success": False,
            "error": f"Invalid template ID '{template_id}'. Available: {list(TEMPLATES_CATALOG.keys())}",
        }

    if not user_consent_confirmed:
        template = TEMPLATES_CATALOG[template_id]
        return {
            "success": False,
            "requires_consent": True,
            "message": (
                f"Consent required to switch UI template to '{template['name']}'. "
                f"Please confirm: 'Yes, apply {template['name']} UI template'."
            ),
            "template_preview": template,
        }

    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)
    active_template_file = os.path.join(data_dir, "active_template.json")

    chosen = TEMPLATES_CATALOG[template_id]
    active_data = {
        "active_template": chosen,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "user_consent_confirmed": True,
    }

    with open(active_template_file, "w", encoding="utf-8") as f:
        json.dump(active_data, f, indent=2)

    return {
        "success": True,
        "message": f"Successfully applied UI template: '{chosen['name']}'!",
        "active_template": chosen,
    }


def get_active_template() -> dict:
    """Gets the currently active UI template."""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    active_template_file = os.path.join(data_dir, "active_template.json")
    if os.path.exists(active_template_file):
        try:
            with open(active_template_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "active_template": TEMPLATES_CATALOG["artisan-dark"],
        "user_consent_confirmed": True,
    }
