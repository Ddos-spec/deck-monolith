# deck-monolith

> **Status: Early Development / Experimental WIP (`Masih Tahap Dev`)**
>
> **English:** This project is in active early development and still has rough edges and visual defects ("cacat"). Automated 15-slide expansion across 1,000+ messy scraped `.pptx` files can produce awkward text wraps or mismatched imagery, the fast Pillow OOXML preview renderer approximates complex SmartArt/charts compared to native PowerPoint COM export, and the topic-to-image pairing heuristic needs further tuning. Do not expect production perfection out of the box—inspect, report defects, or fork and extend the engine.
>
> **Bahasa Indonesia:** Repo ini masih dalam tahap pengembangan awal (*WIP / Dev Build*) dan masih banyak kekurangannya. Ekspansi otomatis ke 15+ slide pada seribu lebih file `.pptx` hasil scraping masih kadang menghasilkan wrapping teks kurang pas atau gambar kurang nyambung, renderer preview Pillow bersifat aproksimasi dibanding export PowerPoint COM asli, dan UI masih terus berevolusi.

A brutalist presentation archive (Astro 5 + Tailwind CSS v4) paired with a Python OOXML engine (`studio_engine/`) containing **1,060 cataloged decks** (`51` flagship/curated `.pptx` + previews tracked directly in Git) across **10 categories**, **29 industries**, and **16 distinct visual design systems**.

---

## How Any AI Agent Can Use This Repo to Build Much Better `.pptx` Files

Most LLM-generated PowerPoint files fail for four predictable reasons: centered bullet walls, distorted `16:9` aspect ratios, static cut-to-cut transitions, and invalid OpenXML parts that crash Microsoft PowerPoint. Everything in [`studio_engine/`](studio_engine/) and [`SKILL.md`](SKILL.md) exists to eliminate those failures.

### Quickest Option: Drop [`SKILL.md`](SKILL.md) Into Your AI Agent

Copy [`SKILL.md`](SKILL.md) into your AI assistant's skills directory (Claude Code `~/.claude/skills/`, Codex `~/.codex/skills/`, Antigravity/Gemini `~/.gemini/antigravity-cli/skills/`, or Cursor rules). It gives the agent the exact OOXML Morph XML, `33.87 x 19.05 cm` geometry math, contrast tokens across 16 design movements, and PowerPoint validation traps.

---

### 1. Native PowerPoint Morph Protocol (`!!actor-*` + `<p159:morph>`)

Do not settle for static slide cuts. Microsoft PowerPoint automatically interpolates position, scale, rotation, and color between consecutive slides **if**:

1. Every slide includes the `<mc:AlternateContent>` `<p159:morph option="byObject"/>` transition block (falling back to `<p:fade/>` on older viewers).
2. Persistent shapes/pictures across adjacent slides share the **exact same `name` attribute starting with `!!`** (`!!actor-cover-art`, `!!actor-title`, `!!scene-rule`, `!!actor-card-0`) inside `<p:cNvPr id="..." name="!!actor-cover-art"/>`.

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

Keep `<p:timing>` entrance animations (`presetClass="entr"`, staggered `140ms` delays) strictly on foreground `!!actor-*` elements (`max 5` per slide) so background panels never flicker during Morph transitions.

---

### 2. `16:9` Safe Coordinate & Anti-Collision Math

Work exclusively on a **`33.87 x 19.05 cm` (`12192000 x 6858000 EMU`)** widescreen canvas (`1 cm = 360000 EMU`). Never stretch images to arbitrary boxes—clamp aspect ratios and compute overflow before writing XML (`studio_engine/expand_to_avant_garde_15.py`):

```python
def safe_pic_box(max_w: float, max_h: float, aspect: float) -> tuple[float, float]:
    """Fit image inside max_w x max_h without distorting its natural aspect ratio."""
    asp = max(0.6, min(2.2, aspect or 1.4))
    w = max_w
    h = w / asp
    if h > max_h:
        h = max_h
        w = h * asp
    return round(w, 3), round(h, 3)

def wrap_headline(title: str, max_chars: int = 16, max_lines: int = 3, upper: bool = False) -> str:
    """Prevent headlines from spilling vertically into body blocks."""
    words = [w for w in title.strip().split() if w]
    lines, cur = [], ""
    for w in words:
        if len(w) > max_chars + 3 and not cur:
            lines.append(w[:max_chars])
        elif not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= max_chars:
            cur = f"{cur} {w}"
        else:
            lines.append(cur)
            cur = w
        if len(lines) >= max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    out = "\n".join(lines[:max_lines]).strip(" —-")
    return out.upper() if upper else out
```

**Three rendering safeguards learned while expanding 1,093 decks:**
- **HTML Entity Unescaping:** Regex-extracting `<a:t>` leaves `&amp;` or `&quot;` literal; always run `html.unescape()` before writing slide text or PNG renders.
- **CJK Font Routing:** Windows Latin fonts (`Georgia`, `Bahnschrift`, `Consolas`) draw square tofu (`□□□`) on CJK strings. Route non-Latin text (`ord(ch) > 0x2E80`) to `msyh.ttc` when rasterizing previews.
- **RGBA Surface Compositing:** Transparent `.png` assets look broken on dark canvases or get black halos when saved to JPEG. Always composite `RGBA` assets over the active deck's exact card/surface hex before embedding.

---

### 3. Real PowerPoint COM / OpenXML Pitfalls to Avoid

When mutating `.pptx` ZIP archives directly (`zipfile`), Microsoft PowerPoint COM `.Open()` will fail with `E_FAIL (-2147467259)` even when Python's `xml.etree.ElementTree` parses cleanly if any of these happen:

1. **Unregistered ZIP Extensions / `.json` Parts:** Dropping an extra metadata file like `ppt/meta.json` inside a `.pptx` without a valid `[Content_Types].xml` mapping breaks COM loading immediately.
2. **Missing `xmlns:r` on `<p:sldIdLst>`:** Some scraped `.pptx` decks declare `xmlns:r` on individual `<p:sldId>` children instead of `<p:presentation>`. Explicitly emit `<p:sldIdLst xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">` when rewriting slide lists.
3. **Relative vs. Absolute Slide Targets:** Check whether existing relationships in `ppt/_rels/presentation.xml.rels` use `slides/slide1.xml` or `/ppt/slides/slide1.xml` and match the deck's existing convention.
4. **Element Ordering in `<p:spPr>` and `<p:sld>`:** Keep strict ECMA-376 child sequence (`<p:cSld>` -> `<p:clrMapOvr>` -> `<p:transition>` -> `<p:timing>`).

---

### 4. The 16 Avant-Garde Design Systems (`DESIGN_FAMILIES`)

Do not default every presentation to dark navy or generic gradient SaaS templates. Pick one system from [`studio_engine/expand_to_avant_garde_15.py`](studio_engine/expand_to_avant_garde_15.py) matching the topic:

| ID | Movement | Background | Surface / Card | Primary Ink | Accent 1 | Accent 2 | Typography Role |
|---|---|---|---|---|---|---|---|
| `swiss_grid_white` | Swiss Grid White | `#F8F7F4` | `#FFFFFF` | `#111827` | `#E0311B` | `#1D4ED8` | Grotesk + Sans |
| `kinfolk_warm_editorial` | Warm Sand Editorial | `#F4EFE6` | `#FAF7F1` | `#1C1917` | `#9A3412` | `#3F6212` | Serif + Sans |
| `bauhaus_constructivist` | Weimar Bauhaus | `#F7F3E8` | `#FFFFFF` | `#121212` | `#E03C1F` | `#1D4ED8` | Grotesk Display |
| `pentagram_split_poster` | Pentagram Pigment Split | `#FAF8F5` | `#FFFFFF` | `#141413` | `#991B1B` | `#0F766E` | Grotesk + Serif |
| `ft_salmon_financial` | FT Salmon Monograph | `#F6DEC8` | `#FDF5ED` | `#111827` | `#7F1D1D` | `#0F766E` | Serif + Sans |
| `luxury_atelier_noir` | Luxury Atelier Noir | `#141312` | `#191716` | `#F5F2EB` | `#D4AF37` | `#B45309` | Editorial Serif |
| `brutalist_tabloid_press` | Brutalist Broadsheet | `#EAE6DF` | `#F7F5F0` | `#0F0F0F` | `#DC2626` | `#0F0F0F` | Condensed Display |
| `apple_bento_modular` | Modular Bento Grid | `#F1F5F9` | `#FFFFFF` | `#0F172A` | `#2563EB` | `#0F172A` | Grotesk Display |
| `architectural_blueprint` | Architectural Blueprint | `#0B2545` | `#0F2C52` | `#F0F9FF` | `#38BDF8` | `#F59E0B` | Display + Mono |
| `botanical_sage_organic` | Botanical Sage Folio | `#EBF1EC` | `#F9FBF9` | `#143326` | `#143326` | `#C2410C` | Serif + Sans |
| `neo_brutalist_acid` | Neo-Brutalist Pop | `#FEF3C7` | `#FFFFFF` | `#09090B` | `#EF4444` | `#2563EB` | Hard-Shadow Display |
| `japanese_ma_zen` | Kyoto Ma-Zen | `#FAF8F2` | `#FFFFFF` | `#1C1917` | `#DC2626` | `#292524` | Serif + Vertical Mono |
| `cyber_pulse_quantum` | Quantum Deep Field | `#070B19` | `#0D1428` | `#F8FAFC` | `#06B6D4` | `#A855F7` | Grotesk + Mono |
| `risograph_duotone_poster` | Risograph Overprint | `#F5EBE0` | `#FCF8F4` | `#1E1B4B` | `#F43F5E` | `#0D9488` | Display + Serif |
| `vignelli_canon_band` | Vignelli Canon Grid | `#F9F8F6` | `#FFFFFF` | `#111827` | `#B91C1C` | `#1E3A8A` | Grotesk Grid |
| `gallery_diptych_spread` | Museum Diptych Spread | `#EDE9E0` | `#FAF8F5` | `#18181B` | `#1E3A8A` | `#B45309` | Serif Monograph |

*(Specimen #1, [`MODNEXUS`](public/pptx/modnexus-global-modding-union.pptx), stays untouched as the original diagonal-curtain reference deck.)*

---

### 5. Querying the Catalog for Few-Shot Examples (Zero MCP)

Every deck in [`src/data/decks.json`](src/data/decks.json) (and live at `GET /api/decks.json`) exposes structured design tokens an AI agent can sample as few-shot guidance before generating slides:

```json
{
  "title": "FY2024 Strategic Budget Review & Financial Planning",
  "category": "Report",
  "industry": "Enterprise",
  "designFamily": "Vignelli Canon Grid",
  "slidesCount": 15,
  "avgShapesPerSlide": 21.9,
  "morphSlides": 15,
  "pairedMorphSlides": 4,
  "fonts": ["Bahnschrift", "Georgia", "Consolas"],
  "colors": ["#B91C1C", "#1E3A8A", "#F9F8F6", "#111827"],
  "pptxUrl": "/pptx/corpus-fy24-budget-review.pptx"
}
```

Use [`buildAiPromptFromDeck`](src/lib/deckCatalog.ts) or click **`AI Prompt`** on any card in the web UI to copy the ready-made generation prompt for that presentation.

---

## Repository Structure

```text
.
├── README.md
├── SKILL.md                  # Drop-in agent skill for generating Morph OOXML .pptx decks
├── src/
│   ├── data/decks.json       # Full 1,060-deck structured catalog & OOXML telemetry
│   ├── lib/deckCatalog.ts    # Categories, industries, and buildAiPromptFromDeck()
│   ├── pages/
│   │   ├── index.astro       # Brutalist exhibition grid + live hero motion stage
│   │   ├── api/decks.json.ts # Machine-readable HTTP JSON endpoint (/api/decks.json)
│   │   └── deck/[slug].astro # Per-deck static pages (1,060 routes)
│   └── scripts/gallery.ts    # Virtualized cards, hover scrubbing, modal FX, keyboard nav
├── studio_engine/            # OOXML generation, asset filtering & compilation scripts
│   ├── expand_to_avant_garde_15.py   # 16 design systems + <p159:morph> injection
│   ├── build_visual_asset_bank.py    # 210 dhash-deduplicated plates (rejects white UI screenshots)
│   ├── compile_deck_gallery.py       # Catalog compiler + /llms.txt emitter
│   ├── analyze_corpus.py             # OOXML shape/font/color/Morph analyzer
│   └── build_dedup_registry.py       # 4-layer .pptx deduplication registry
└── public/
    ├── llms.txt              # LLM discovery index
    ├── pptx/                 # 51 flagship/curated .pptx files (bulk scraped corpus excluded via .gitignore)
    └── previews/             # 16:9 PNG slide strips for tracked decks
```

## Local Development

```bash
npm install
npm run dev       # Local dev server at http://localhost:4321
npm run build     # Build all 1,061 static pages + /api/decks.json
npm run preview   # Serve dist/ production bundle
```

Note on `.gitignore`: the `3.5 GB` bulk scraped binary folders (`public/pptx/{gh,ia,sc}-*` and `public/previews/{gh,ia,sc}-*`) are excluded from Git to keep clones under ~145 MB while keeping [`src/data/decks.json`](src/data/decks.json), all `51` flagship `.pptx` specs, and the complete [`studio_engine/`](studio_engine/) source intact.
