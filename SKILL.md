---
name: pptx-avant-garde-architect
description: Blueprints, OOXML Morph choreography rules, 16-system editorial design tokens, and anti-collision geometry for AI agents building high-craft .pptx presentations. Derived from Ddos-spec/deck-monolith. Note: source toolkit is in early WIP development.
---

# Avant-Garde PowerPoint Architect (`pptx-avant-garde-architect`)

> **Notice:** Extracted from `Ddos-spec/deck-monolith` (early WIP development). Always verify generated `.pptx` files open cleanly in PowerPoint or LibreOffice Impress before delivering.

When asked to build or upgrade a PowerPoint presentation (`.pptx`), **do not** output centered bullet walls, default PowerPoint templates, distorted aspect ratios, or uniform dark gradients. Apply this workflow instead.

## 1. Non-Negotiable Presentation Laws

1. **Fixed `16:9` Coordinate Canvas:** Design on `33.87 x 19.05 cm` (`12192000 x 6858000 EMU`, `1 cm = 360000 EMU`). Leave >= `1.4 cm` outer safe margins (`x: 1.6..32.27`, `y: 1.0..18.05`).
2. **Never Distort Images:** Always fit images using preserved aspect ratios (`w = min(max_w, max_h * aspect)`, `h = w / aspect`). Never stretch a `4:3` or square photo into a `16:9` box unless intentionally cropping.
3. **One Focal Hierarchy Per Slide:** Every slide needs a clear primary anchor (display headline, giant metric, or visual plate) + supporting metadata. Keep body copy concise (`<= 45 words` per text zone).
4. **Native PowerPoint Morph (`!!` Prefix Actor Matching):**
   - Attach `<p159:morph option="byObject"/>` (with `<p:fade/>` fallback) inside `<p:transition>`.
   - Give persistent background rules, headlines, focal artwork, and metric cards identical `<p:cNvPr name="!!..."/>` IDs across consecutive slides (`!!actor-title`, `!!actor-cover-art`, `!!scene-rule`, `!!actor-badge`). Moving or resizing that shape between Slide N and Slide N+1 creates fluid native PowerPoint motion without overlapping animation timelines.

```xml
<p:transition xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
              xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main"
              xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
              xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main"
              spd="med" p14:dur="850" advClick="1">
  <mc:AlternateContent>
    <mc:Choice Requires="p159"><p159:morph option="byObject"/></mc:Choice>
    <mc:Fallback><p:fade/></mc:Fallback>
  </mc:AlternateContent>
</p:transition>
```

## 2. Select One Design System (Never Reuse One Dark Theme for Everything)

Pick **one** coherent system per deck based on audience and domain (full hex tokens in `README.md` and `studio_engine/expand_to_avant_garde_15.py`):

- **Executive / Finance / Consulting:**
  - `ft_salmon_financial`: BG `#F6DEC8`, Card `#FDF5ED`, Ink `#111827`, Accent `#7F1D1D` / `#0F766E`, Georgia serif display
  - `swiss_grid_white`: BG `#F8F7F4`, Card `#FFFFFF`, Ink `#111827`, Accent `#E0311B` / `#1D4ED8`, exposed hairline grid
  - `vignelli_canon_band`: BG `#F9F8F6`, top crimson `#B91C1C` header band + sapphire `#1E3A8A` rule + 3-column lower grid
- **Editorial / Brand / Real Estate / Lifestyle:**
  - `kinfolk_warm_editorial`: BG `#F4EFE6`, Card `#FAF7F1`, Ink `#1C1917`, Accent `#9A3412` / `#3F6212`, serif + wide margins
  - `japanese_ma_zen`: BG `#FAF8F2`, vermilion `#DC2626` index square, vertical right-side label rail, asymmetric negative space
  - `botanical_sage_organic`: BG `#EBF1EC`, Deep Forest `#143326`, Terracotta `#C2410C`, rounded picture frames
  - `luxury_atelier_noir`: BG `#141312`, Champagne Gold `#D4AF37` `1.1 cm` inset hairline border, centered fashion serif
- **Tech / AI / SaaS / Hardware / Creative Agencies:**
  - `apple_bento_modular`: BG `#F1F5F9`, 4 rounded surface tiles (`#FFFFFF`, `#0F172A`, `#2563EB`), clean KPI + visual split
  - `architectural_blueprint`: BG `#0B2545`, Cyan `#38BDF8` CAD grid + Amber `#F59E0B` callouts
  - `cyber_pulse_quantum`: BG `#070B19`, Cyan `#06B6D4` + Violet `#A855F7` framing brackets
  - `bauhaus_constructivist`: BG `#F7F3E8`, Vermilion `#E03C1F` + Cobalt `#1D4ED8` + Ochre `#EAB308` geometric solids
  - `neo_brutalist_acid`: BG `#FEF3C7`, `#09090B` solid offset card shadows (`+0.28 cm` X/Y), thick borders

## 3. Rhythm Across Slides (`>= 4` Structural Roles)

Never repeat the exact same layout two slides in a row. Alternate roles while keeping `!!actor-*` names intact so Morph flows across layout changes:

1. **Act I — Cover / Thesis Framing:** High-contrast headline (`32–44 pt`), tracked category kicker, primary visual plate.
2. **Act II — Asymmetric Flip + Proof:** Flip text and image horizontally (`role % 2 == 1`), reveal ghost index numeral or metric cards.
3. **Act III — Matrix / Split Comparison:** Structured multi-column comparison, 50/50 pigment block, or 3-column caption strip.
4. **Act IV — Synthesis / Diptych Stack:** Multi-card Bento/table summary or dual-image spread with executive takeaway.

## 4. OOXML Hygiene Checklist (Prevents Corrupt `.pptx` Errors)

- Unescape XML entities (`&amp;`, `&quot;`) before rendering or double-escaping with `xml.sax.saxutils.escape`.
- When mutating `<p:sldIdLst>`, declare `xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"` directly on `<p:sldIdLst>` and ensure unique numeric `id` attributes (`>= 256`) and unique `rId*` keys in `ppt/_rels/presentation.xml.rels`.
- Never write non-OOXML files (like `.json`) inside the `.pptx` archive without valid `[Content_Types].xml` entries—PowerPoint COM rejects unmapped parts with `E_FAIL`.
- Keep `<p:sld>` child element order strict: `<p:cSld>` -> `<p:clrMapOvr>` -> `<p:transition>` -> `<p:timing>`.
- When sampling reference decks from `src/data/decks.json` (`GET /api/decks.json`), filter by `category` / `industry` / `designFamily` to grab verified `colors`, `fonts`, `avgShapesPerSlide`, and working `.pptx` structure examples.
