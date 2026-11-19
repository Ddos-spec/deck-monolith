---
name: pptx-avant-garde-architect
description: DNA-preserving organic layer deconstruction, native PowerPoint Morph choreography, continuous proportion layout planning, and .pptx quality auditing for AI agents. Derived from Deckhouse (WIP dev toolkit).
---

# Avant-Garde PowerPoint Architect (`pptx-avant-garde-architect`)

> **Notice:** Extracted from **Deckhouse** (active WIP dev build). Always run `studio_engine/ai_slide_director.py audit` and verify the exported `.pptx` opens cleanly in Microsoft PowerPoint or LibreOffice Impress before delivering.

When asked to build or remaster a PowerPoint presentation (`.pptx`), **do not** force every deck into a fixed slide quota (like always 15 slides), **do not** force unrelated decks into a handful of rigid cookie-cutter stencils, and **never** clash a deck's original visual DNA with alien colors or unrelated stock photos.

## 1. Run the AI Director Planner & Linter First

If [`studio_engine/ai_slide_director.py`](studio_engine/ai_slide_director.py) is present in the workspace:

```bash
# Plan an organic multi-stage layer-deconstruction storyboard (or pass --pptx <source.pptx> to inherit real DNA)
python studio_engine/ai_slide_director.py storyboard --title "<Deck Topic>" --category "<Pitch|Report|Design|...>" --industry "<Industry>"

# Audit any .pptx archive for DNA color coherence, Morph actor pairing & OOXML hygiene (0-100 score)
python studio_engine/ai_slide_director.py audit <path/to/output.pptx>
```

## 2. Core Principles: DNA Unity + Organic Layer Deconstruction

1. **Preserve Authentic Visual DNA Across Every Slide:**
   - Extract or lock **one coherent color & typography DNA** (`bg`, `panel`, `card`, `ink`, `muted`, `acc1`, `acc2`, primary typeface) from Slide 1 to the final slide.
   - If a deck is monochrome B&W, keep **100% of slides monochrome**. If a deck is Obsidian & Gold or Deep Navy & Cyan, keep every transition, setup frame, and takeaway frame inside that exact visual universe.
2. **Deconstruct Layers Organically (No Rigid Slide Quota, No Cookie-Cutter Stencil):**
   - Let slide count grow naturally from content density (`12`, `18`, `24`, `35`, `60+` slides):
     - **Layer Setup / Camera Framing:** Primary headline/visual anchor enters slightly zoomed while supporting cards/bullets rest cleanly off-canvas ready to Morph in.
     - **Progressive Layer Unfold:** Supporting waves glide onto screen across 1–2 stages via `<p159:morph option="byObject"/>` so no slide becomes a dense wall of text (`<= 55` words/box).
     - **Full Resolution & Focus Shift:** Complete native/rebuilt composition settles cleanly, followed by a DNA-matched focus/takeaway zoom when the beat has dense proof.
3. **Native PowerPoint Morph (`!!` Prefix Actor Matching):**
   - Attach `<p159:morph option="byObject"/>` (with `<p:fade/>` fallback) inside `<p:transition>`.
   - Assign matching `<p:cNvPr name="!!sXX-layer-YY"/>` names to every persistent layer across consecutive stages so PowerPoint smoothly interpolates position, scale, and framing without flickering.
4. **Zero Foreign Image Pollution:**
   - Use the deck's own native media (`ppt/media/`) with progressive crop/zoom framing across Morph stages, or construct crisp vector/geometric canvas layers colored strictly in the deck's own DNA hex palette. Never inject unrelated stock photos.

## 3. OOXML Hygiene Checklist (Prevents Corrupt `.pptx` Errors)

- Use `lxml.etree` when mutating existing `.pptx` slide XML so third-party namespace prefixes are preserved verbatim.
- Call `html.unescape()` on extracted `<a:t>` snippets before rendering or re-escaping XML.
- Declare `xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"` directly on `<p:sldIdLst>` and keep shape `cNvPr id` values unique inside `<p:spTree>`.
- Strip duplicate `notesSlide` relationships when cloning native slide `.rels`.
- Never write unmapped `.json` files inside `.pptx` ZIPs without `[Content_Types].xml`.
- Keep strict ECMA-376 `<p:sld>` child order: `<p:cSld>` → `<p:clrMapOvr>` → `<p:transition>` → `<p:timing>`.
