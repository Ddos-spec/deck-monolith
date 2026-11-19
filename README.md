# Deckhouse — Kinetic & Avant-Garde Presentation Archive

> **Early Experimental Build (`WIP / v0.3-dev`)**
>
> **English:** This toolkit and archive are under active development. Automated organic layer deconstruction across 1,000+ heterogeneous scraped `.pptx` sources can still encounter edge-case text wraps or Pillow raster approximations compared to native PowerPoint export. Always inspect outputs and run `python studio_engine/ai_slide_director.py audit <file.pptx>` before production delivery.
>
> **Bahasa Indonesia:** Proyek ini masih dalam tahap pengembangan awal (*WIP / Dev Build*) dan terus disempurnakan. Dekonstruksi layer otomatis pada seribu lebih `.pptx` hasil scraping masih kadang memiliki perbedaan minor antara rasterisasi preview Pillow dibanding export PowerPoint COM asli. Gunakan validator bawaan (`ai_slide_director.py audit`) sebelum dipakai di produksi.

An editorial-brutalist presentation showcase (**Astro 5 + Tailwind CSS v4**) paired with a Python OOXML choreography engine ([`studio_engine/`](studio_engine/)) indexing **1,060 cataloged decks** (`51` flagship/curated `.pptx` + slide strips tracked cleanly in Git) across **10 categories** and **29 industries**.

---

## Core Philosophy: DNA-Preserving Organic Layer Deconstruction

Instead of forcing every presentation into a fixed slide quota (e.g. stamping every deck to 15 slides) or cookie-cutter stencil templates that clash with the original creator's colors, [`studio_engine/expand_to_avant_garde_15.py`](studio_engine/expand_to_avant_garde_15.py) and [`studio_engine/ai_slide_director.py`](studio_engine/ai_slide_director.py) follow three principles:

1. **100% Authentic Visual DNA Lock (`extract_original_dna`)**
   - Reads the original deck's `<p:bg>`, `<a:srgbClr>`, `<a:schemeClr>` (`theme1.xml`), monochrome character, and native typefaces before generating or staging a single slide.
   - Pure monochrome B&W decks stay strictly monochrome; Obsidian & Gold decks stay Obsidian & Gold; Deep Navy or Warm Pastel decks stay faithful to their original visual universe from first slide to last—zero "2-designer color clash".
2. **Organic Layer Deconstruction & Multi-Stage Camera Framing (Zero Stencil Quota)**
   - Rich native slides are deconstructed directly at the `<p:spTree>` XML level (preserving original shapes, groups, illustrations, and `.rels` relationships) into **2–4 progressive Morph stages** (*Camera Anchor Framing* → *Wave Unfold* → *Full Native Composition* → *Focus Synthesis*), staging secondary elements off-canvas so PowerPoint `<p159:morph option="byObject"/>` glides every layer smoothly onto screen.
   - Bare, unstyled text slides are rebuilt via continuous content-driven generative proportioning locked 100% to the deck's original DNA palette + native media / DNA vector geometry (never pulling unrelated random stock photos).
   - Total slide counts grow organically from real deck density (`11` to `100+` slides).
3. **Executable AI Art-Director & Linter (`ai_slide_director.py`)**

```bash
# 1) Generate an organic DNA-preserving multi-stage storyboard JSON
python studio_engine/ai_slide_director.py storyboard \
  --title "Autonomous Drone Freight Network" \
  --category "Pitch" \
  --industry "Logistics"

# Or extract authentic color/font DNA straight from an existing .pptx before planning:
python studio_engine/ai_slide_director.py storyboard \
  --title "Art of Design Remaster" \
  --pptx public/pptx/corpus-art-of-design-pillars.pptx

# 2) Audit any .pptx for DNA palette coherence, Morph actor pairing & OOXML hygiene (0-100 score)
python studio_engine/ai_slide_director.py audit public/pptx/corpus-art-of-design-pillars.pptx
```

Drop [`SKILL.md`](SKILL.md) into your AI coding assistant (`~/.claude/skills/`, `~/.codex/skills/`, `~/.gemini/antigravity-cli/skills/`, or Cursor rules) to activate this workflow automatically.

---

### Native PowerPoint Morph Protocol (`!!sXX-layer-YY` + `<p159:morph>`)

Microsoft PowerPoint natively interpolates position, scale, rotation, and fill between adjacent slides **only if**:

1. Every target slide carries `<mc:AlternateContent>` `<p159:morph option="byObject"/>` (with `<p:fade/>` fallback).
2. Persistent shapes across Slide $N$ and Slide $N+1$ share identical `<p:cNvPr id="..." name="!!..."/>` identifiers (e.g. `!!s01-layer-00`, `!!s01-layer-01`, `!!s01-bg-01`) regardless of how many layers exist on that slide.

```xml
<p:transition xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
              xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main"
              xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
              xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main"
              spd="med" p14:dur="850" advClick="1">
  <mc:AlternateContent>
    <mc:Choice Requires="p159">
      <p159:morph option="byObject"/>
    </mc:Choice>
    <mc:Fallback>
      <p:fade/>
    </mc:Fallback>
  </mc:AlternateContent>
</p:transition>
```

---

### Real PowerPoint COM / OpenXML Pitfalls Prevented by `studio_engine/`

1. **Prefix Preservation via `lxml.etree`:** Mutating arbitrary third-party `.pptx` XML with `xml.etree.ElementTree` rewrites namespace prefixes (`ns0:`, `ns1:`). All native XML deconstruction uses `lxml.etree` so prefixes remain verbatim.
2. **Unregistered ZIP Parts:** Writing `.json` files inside a `.pptx` ZIP without `[Content_Types].xml` breaks PowerPoint COM (`E_FAIL`).
3. **Explicit `xmlns:r` on `<p:sldIdLst>` & Strict ECMA-376 `<p:sld>` Ordering:** Always maintain `<p:cSld>` → `<p:clrMapOvr>` → `<p:transition>` → `<p:timing>`, and strip duplicate `notesSlide` relationships when cloning native slide `.rels`.
4. **CJK Routing & Entity Hygiene:** Call `html.unescape()` on extracted `<a:t>` runs and route non-Latin CJK text (`ord(ch) > 0x2E80`) to `msyh.ttc` when rasterizing PNG previews.

*(Specimen #1, [`MODNEXUS`](public/pptx/modnexus-global-modding-union.pptx), stays preserved in its original diagonal-curtain composition.)*

---

## Repository Structure

```text
.
├── README.md
├── SKILL.md                  # Drop-in agent skill for DNA-preserving Morph OOXML decks
├── src/
│   ├── data/decks.json       # Full 1,060-deck structured catalog & OOXML telemetry
│   ├── lib/deckCatalog.ts    # Categories, industries, and buildAiPromptFromDeck()
│   ├── pages/
│   │   ├── index.astro       # Deckhouse exhibition showcase & live motion stage
│   │   ├── api/decks.json.ts # Machine-readable JSON catalog (/api/decks.json)
│   │   └── deck/[slug].astro # Per-deck static pages (1,060 routes)
│   └── scripts/gallery.ts    # Virtualized cards, hover filmstrip scrubber, modal FX, `[` / `]` nav
├── studio_engine/
│   ├── ai_slide_director.py          # Organic DNA storyboard planner & 0-100 PPTX quality linter
│   ├── expand_to_avant_garde_15.py   # DNA extractor + lxml organic layer deconstructor + 2x Pillow rasterizer
│   ├── compile_deck_gallery.py       # Catalog compiler + /llms.txt generator
│   ├── analyze_corpus.py             # OOXML shape/font/color/Morph analyzer
│   └── build_dedup_registry.py       # 4-layer .pptx deduplication registry
└── public/
    ├── llms.txt              # LLM discovery index
    ├── pptx/                 # 51 flagship/curated .pptx files (bulk scraped corpus excluded in .gitignore)
    └── previews/             # 16:9 PNG slide strips for tracked decks
```

## Local Development

```bash
npm install
npm run dev       # Local dev server at http://localhost:4321
npm run build     # Build static routes + /api/decks.json
npm run preview   # Serve dist/ production bundle
```
