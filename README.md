# DECK.MONOLITH

An architectural Brutalist counterpart to `deck.gallery`—combining an **Awwwards-grade Raw Concrete Web Archive** built with Astro 5 + Tailwind CSS v4 and a **16-System OOXML Presentation Generation & Expansion Engine** (`studio_engine/`).

---

## Core Architecture

1. **Web Platform (`src/`)**
   - **Exposed Brutalist Design System ([global.css](src/styles/global.css))**: Built on a *Raw Architectural Limestone* (`#F2EFE9`) palette with a 48px exposed concrete grid, `2px` load-bearing `#111111` structural rules, tactile hard offset shadows (`4px 4px 0px`), and a 1-click toggle to **Obsidian Monolith** (`theme-obsidian`).
   - **Asymmetric Exhibition Hero & Live FX Stage ([index.astro](src/pages/index.astro), [DeckViewerModal.astro](src/components/DeckViewerModal.astro))**:
     - Interactive dual-buffer **Live Motion Stage** right in the hero and modal supporting **4 live transition engines** (`Morph Flow`, `Kinetic 3D`, `Spatial Tilt`, `Brutalist Wipe`).
     - **Seamless Deck-to-Deck Switching** (`[` / `]` or `←` / `→` Prev/Next PPT) without backing out of the viewer.
     - **1-Click Category Ribbon**, **Hover Filmstrip Scrubbing** on grid cards, and virtualized 60FPS batch rendering (`IntersectionObserver`) over the full **1,060-deck catalog**.
   - **First-Class AI Utility**:
     - Every grid card and modal includes 1-click **`⧉ AI Prompt`** extraction (`buildAiPromptFromDeck` in [deckCatalog.ts](src/lib/deckCatalog.ts)).
     - Plain HTTP JSON & context indexes at **`GET /api/decks.json`** and **`GET /llms.txt`** (zero MCP setup required).

2. **16-System Avant-Garde OOXML Engine (`studio_engine/`)**
   - **`expand_to_avant_garde_15.py`**: Expands `.pptx` decks to **15+ native OOXML slides** with `<p159:morph option="byObject"/>` and `!!actor-*` transitions across **16 distinct Avant-Garde design movements** (plus flagship `MODNEXUS` `#1` preserved intact):
     - *Swiss Grid White*, *Warm Sand Editorial*, *Weimar Bauhaus*, *Pentagram Pigment Split*, *FT Salmon Monograph*, *Luxury Atelier Noir*, *Brutalist Broadsheet*, *Modular Bento Grid*, *Architectural Blueprint*, *Botanical Sage Folio*, *Neo-Brutalist Pop*, *Kyoto Ma-Zen*, *Quantum Deep Field*, *Risograph Overprint*, *Vignelli Canon Grid*, and *Museum Diptych Spread*.
   - **`build_visual_asset_bank.py`**: Builds `210` perceptual-hash-deduplicated visual plates (`114` non-screenshot real artwork/photography assets + `96` fine-art procedural plates across `24` styles & `20` palettes).
   - **`compile_deck_gallery.py` & `analyze_corpus.py`**: Validates OOXML structure, enforces 4-layer deduplication, and compiles `src/data/decks.json` + `/llms.txt`.

---

## Local Development

```bash
npm install
npm run dev       # Local dev server at http://localhost:4321
npm run build     # Build all 1,061 static pages & /api/decks.json
npm run preview   # Serve dist/ production bundle
```

### Rebuilding the Presentation Catalog (`studio_engine/`)

```bash
python studio_engine/build_visual_asset_bank.py
python studio_engine/expand_to_avant_garde_15.py --mode all --force
python studio_engine/compile_deck_gallery.py
```

---

## Repository Scope Note

To keep repository size fast while preserving all 1,060 cataloged decks and API endpoints (`src/data/decks.json`, `/api/decks.json`), all **51 curated/flagship `.pptx` files and PNG slide previews** plus core engine scripts are tracked directly in Git, while the bulk 3.5 GB scraped binary folders (`public/pptx/{gh,ia,sc}-*` and `public/previews/{gh,ia,sc}-*`) are excluded via `.gitignore`.
