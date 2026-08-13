---
name: ui-template-management
description: Guide and workflow for fetching, previewing, and selecting modern UI templates (Sleek Dark Mode Artisan, Glassmorphism Coffee & Tech Hub, Minimalist Neo-Brutalist Dashboard) with user consent.
---

# UI Template Management Skill

This skill provides a structured workflow for fetching, comparing, and applying high-quality UI templates for the BrewCraft portfolio application and web interface.

## Workflow

1. **Fetch & Present 2-3 Options**:
   When the user requests UI customization or template updates, use the `fetch_ui_templates` tool to retrieve 2-3 curated UI templates with rich aesthetic options:
   - **Option 1: Dark Mode Artisan Luxury** (Deep charcoal `#0B0F19`, warm espresso accents `#D97706`, glowing cyan highlights).
   - **Option 2: Vibrant Glassmorphism Tech Hub** (Frosted glass panels, subtle gradients `#4F46E5` -> `#EC4899`, modern blur effects).
   - **Option 3: Neo-Brutalist High-Contrast Dashboard** (Bold typography, sharp borders, high-impact monochrome & vivid amber).

2. **Solicit User Consent**:
   Present the options to the user with detailed descriptions, CSS variables, visual hierarchy specs, and layout structures. Always ask for explicit confirmation before changing the active template.

3. **Apply Selected Template**:
   When consent is confirmed, call `download_and_apply_ui_template` to persist the chosen template into `data/active_template.json` and update `app/static/theme.css` or frontend styling tokens.
