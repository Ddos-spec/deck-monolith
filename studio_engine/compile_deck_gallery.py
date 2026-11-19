"""
Deck Gallery Master Compiler & PowerPoint COM Renderer
Merges:
  1. D:\code\ppt_studio\curated_index.json (existing + curated category decks)
  2. D:\code\ppt_studio\corpus_scraped\scraped_meta.json (BlackArch scraped .pptx decks)
Validates every PPTX, copies to D:\code\deck_gallery\public\pptx\<slug>.pptx,
renders all slides as crisp 1280x720 PNGs via PowerPoint COM into
D:\code\deck_gallery\public\previews\<slug>\slide_NN.png, extracts full OOXML
blueprints, and emits:
  - D:\code\deck_gallery\src\data\decks.json
  - D:\code\deck_gallery\public\api\decks.json
  - D:\code\deck_gallery\public\llms.txt
"""

import hashlib
import io
import json
import os
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

sys.path.insert(0, r"D:\code\ppt_studio")
from analyze_corpus import analyze_pptx

GALLERY_DIR = Path(r"D:\code\deck_gallery")
PPTX_PUBLIC = GALLERY_DIR / "public" / "pptx"
PREVIEWS_PUBLIC = GALLERY_DIR / "public" / "previews"
DATA_OUT = GALLERY_DIR / "src" / "data" / "decks.json"
LLMS_OUT = GALLERY_DIR / "public" / "llms.txt"

CURATED_INDEX = Path(r"D:\code\ppt_studio\curated_index.json")
SCRAPED_DIR = Path(r"D:\code\ppt_studio\corpus_scraped")
SCRAPED_META = SCRAPED_DIR / "scraped_meta.json"

VALID_CATEGORIES = [
    "Pitch", "Guideline", "Report", "Talks", "Portfolio",
    "Marketing", "Sales", "Strategy", "Proposal", "Other",
]
VALID_INDUSTRIES = [
    "Agency", "Media", "SaaS", "Consumer", "Fashion", "Fintech", "Crypto",
    "Enterprise", "Travel", "Mobility", "Climate", "Ecommerce",
    "Food & Beverage", "Sports", "Real Estate", "Marketplace", "Gaming",
    "Hardware", "Healthcare", "Aerospace", "AI", "Industrial", "Beauty",
    "Education", "HR", "Logistics", "Non-Profit", "Security", "Other",
]

NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s or "deck"


def clean_editorial_title(raw_title: str, stem: str = "", slide_texts: list[str] | None = None) -> str:
    """Normalize ugly scraped filenames/titles into clean editorial presentation titles."""
    candidate = (raw_title or "").strip()
    # Strip trailing 4-hex scrape suffixes (e.g., _2d3f, -1f2c) and leading source prefixes
    candidate = re.sub(r"^(?:gh|ia|sc)[-_]+", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"[-_][0-9a-f]{4}$", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"^\d{6,}[_-]*", "", candidate)
    candidate = re.sub(r"\.(pptx?|key|pdf)$", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"[_~]+", " ", candidate)
    candidate = re.sub(r"\s*-\s*", " — ", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip(" —-")

    # Collapse consecutive duplicated words/phrases (case-insensitive)
    words = candidate.split()
    deduped = []
    for w in words:
        if not deduped or deduped[-1].lower() != w.lower():
            deduped.append(w)
    candidate = " ".join(deduped)
    if len(words) >= 4 and len(words) % 2 == 0:
        half = len(words) // 2
        if [w.lower() for w in words[:half]] == [w.lower() for w in words[half:]]:
            candidate = " ".join(words[:half])

    # Strip redundant file-format noise ("PPT", "PPTX", "Presentation", "Slides") in dash segments or ends
    candidate = re.sub(r"\s+—\s+(?:ppt|pptx)\b", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\b(?:ppt|pptx)\b\s*$", "", candidate, flags=re.IGNORECASE).strip(" —-")

    # Limit noisy multi-dash filename chains to at most one clean em-dash separator
    dash_parts = [p.strip() for p in candidate.split(" — ") if p.strip()]
    if len(dash_parts) > 2:
        candidate = f"{' '.join(dash_parts[:2])} — {' '.join(dash_parts[2:])}"

    # Check if filename-derived candidate is still generic/numeric junk
    is_junk = (
        len(candidate) < 4
        or re.fullmatch(r"[\d\s\-—.]+", candidate) is not None
        or re.fullmatch(r"(?:presentation|slide|sample|test|demo|untitled|temp|doc|ppt|output|out|file)[\s\d\-—]*", candidate, flags=re.IGNORECASE) is not None
    )
    if is_junk and slide_texts:
        for snippet in slide_texts:
            first_seg = snippet.split("·")[0].strip()
            first_seg = re.sub(r"\s+", " ", first_seg)
            if len(first_seg) >= 5 and not re.fullmatch(r"[\d\s]+", first_seg):
                candidate = first_seg[:68].rstrip(" ,;:-")
                break

    if not candidate:
        candidate = stem.replace("_", " ").replace("-", " ").strip() or "Untitled Presentation"

    # Normalize lowercase or awkward mixed tokens into clean editorial Title Case while preserving acronyms/CamelCase
    cleaned_words = []
    for w in candidate.split():
        if w == "—":
            cleaned_words.append("—")
        elif any(c.isupper() for c in w[1:]) or (len(w) <= 5 and w.isupper() and any(c.isalpha() for c in w)):
            cleaned_words.append(w)
        else:
            cleaned_words.append(w.capitalize())
    candidate = " ".join(cleaned_words)
    return candidate[:84].strip(" —-")


def has_real_ooxml_content(pptx_path: Path) -> bool:
    """Return True if deck has genuine non-injected content shapes/media/text across slides."""
    try:
        with zipfile.ZipFile(pptx_path, "r") as z:
            slide_files = [n for n in z.namelist() if re.match(r"^ppt/slides/slide\d+\.xml$", n)]
            if not slide_files:
                return False
            real_elements = 0
            real_chars = 0
            for sf in slide_files[:10]:
                raw = z.read(sf).decode("utf-8", "ignore")
                all_sp = len(re.findall(r"<p:sp\b", raw))
                inj_sp = len(re.findall(r'!!av-|!!morph-progress-|!!obsidian|!!prism|!!accent', raw))
                pics = len(re.findall(r"<p:(?:pic|graphicFrame|grpSp|cxnSp)\b", raw))
                real_elements += max(0, all_sp - inj_sp) + pics
                texts = re.findall(r"<a:t>([^<]+)</a:t>", raw)
                for t in texts:
                    ts = t.strip()
                    if not ts.startswith("AVANT //") and not ts.startswith("MORPH ·") and not ts.isdigit():
                        real_chars += len(ts)
            return real_elements >= 2 or real_chars >= 12
    except Exception:
        return False


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_slide_texts(pptx_path: Path, max_slides: int = 8) -> list[str]:
    texts = []
    try:
        with zipfile.ZipFile(pptx_path, "r") as z:
            slide_files = sorted(
                [n for n in z.namelist() if n.startswith("ppt/slides/") and n.endswith(".xml") and (Path(n).name.startswith("slide") or Path(n).name.startswith("av_slide_"))],
                key=lambda s: (0 if Path(s).name.startswith("slide") else 1, int("".join(filter(str.isdigit, Path(s).stem)) or 0)),
            )
            for sf in slide_files[:max_slides]:
                root = ET.fromstring(z.read(sf))
                chunks = [t.text.strip() for t in root.iter(f"{NS_A}t") if t.text and t.text.strip()]
                if chunks:
                    texts.append(" · ".join(chunks[:4])[:140])
    except Exception:
        pass
    return texts


def infer_industry(text: str, category: str = "Other", slug: str = "") -> str:
    low = text.lower()
    rules = [
        ("crypto", "Crypto"), ("blockchain", "Crypto"), ("web3", "Crypto"), ("bitcoin", "Crypto"), ("ethereum", "Crypto"), ("defi", "Crypto"), ("nft", "Crypto"), ("tokenomics", "Crypto"),
        ("fintech", "Fintech"), ("finance", "Fintech"), ("bank", "Fintech"), ("budget", "Fintech"), ("stock", "Fintech"), ("trading", "Fintech"), ("invest", "Fintech"), ("payment", "Fintech"), ("accounting", "Fintech"), ("tax", "Fintech"),
        ("ai ", "AI"), (" ai", "AI"), ("artificial intelligence", "AI"), ("llm", "AI"), ("neural", "AI"), ("machine learning", "AI"), ("deep learning", "AI"), ("chatgpt", "AI"), ("claude", "AI"), ("data science", "AI"),
        ("saas", "SaaS"), ("software", "SaaS"), ("cloud", "SaaS"), ("api", "SaaS"), ("devops", "SaaS"), ("kubernetes", "SaaS"), ("docker", "SaaS"),
        ("security", "Security"), ("cyber", "Security"), ("zero trust", "Security"), ("privacy", "Security"), ("infosec", "Security"), ("vulnerability", "Security"), ("encryption", "Security"),
        ("climate", "Climate"), ("green", "Climate"), ("solar", "Climate"), ("energy", "Climate"), ("carbon", "Climate"), ("earth", "Climate"), ("environment", "Climate"), ("sustainab", "Climate"), ("ecology", "Climate"), ("weather", "Climate"),
        ("health", "Healthcare"), ("medical", "Healthcare"), ("bio", "Healthcare"), ("hospital", "Healthcare"), ("clinical", "Healthcare"), ("pharma", "Healthcare"), ("mental", "Healthcare"), ("nutrition", "Healthcare"), ("medicine", "Healthcare"),
        ("aerospace", "Aerospace"), ("space", "Aerospace"), ("rocket", "Aerospace"), ("orbital", "Aerospace"), ("astronomy", "Aerospace"), ("black hole", "Aerospace"), ("nasa", "Aerospace"), ("planet", "Aerospace"), ("satellite", "Aerospace"), ("aviation", "Aerospace"),
        ("ecommerce", "Ecommerce"), ("e-commerce", "Ecommerce"), ("shop", "Ecommerce"), ("retail", "Ecommerce"), ("store", "Ecommerce"), ("sale", "Ecommerce"), ("winter sales", "Ecommerce"),
        ("marketplace", "Marketplace"), ("two-sided", "Marketplace"), ("auction", "Marketplace"), ("vendor", "Marketplace"), ("classifieds", "Marketplace"),
        ("gaming", "Gaming"), ("mod", "Gaming"), ("game", "Gaming"), ("esport", "Gaming"), ("halloween", "Gaming"), ("rpg", "Gaming"),
        ("hardware", "Hardware"), ("chip", "Hardware"), ("device", "Hardware"), ("3d", "Hardware"), ("robot", "Hardware"), ("sensor", "Hardware"), ("semiconductor", "Hardware"), ("iot", "Hardware"),
        ("education", "Education"), ("school", "Education"), ("learn", "Education"), ("study", "Education"), ("university", "Education"), ("teacher", "Education"), ("student", "Education"), ("academic", "Education"), ("thesis", "Education"), ("philosophy", "Education"), ("curriculum", "Education"), ("lecture", "Education"), ("midterm", "Education"),
        ("fashion", "Fashion"), ("luxury", "Fashion"), ("apparel", "Fashion"), ("clothing", "Fashion"), ("style", "Fashion"), ("runway", "Fashion"),
        ("beauty", "Beauty"), ("cosmetic", "Beauty"), ("skincare", "Beauty"), ("makeup", "Beauty"), ("salon", "Beauty"), ("fragrance", "Beauty"), ("spa", "Beauty"),
        ("food", "Food & Beverage"), ("coffee", "Food & Beverage"), ("restaurant", "Food & Beverage"), ("culinary", "Food & Beverage"), ("recipe", "Food & Beverage"), ("beverage", "Food & Beverage"), ("bakery", "Food & Beverage"), ("tea", "Food & Beverage"),
        ("travel", "Travel"), ("hotel", "Travel"), ("tourism", "Travel"), ("vacation", "Travel"), ("holiday", "Travel"), ("flight", "Travel"), ("itinerary", "Travel"), ("destination", "Travel"),
        ("real estate", "Real Estate"), ("property", "Real Estate"), ("architecture", "Real Estate"), ("interior", "Real Estate"), ("housing", "Real Estate"), ("building", "Real Estate"),
        ("sport", "Sports"), ("fitness", "Sports"), ("exercise", "Sports"), ("physical education", "Sports"), ("athletic", "Sports"), ("football", "Sports"), ("basketball", "Sports"), ("workout", "Sports"),
        ("mobility", "Mobility"), ("ev ", "Mobility"), ("auto", "Mobility"), ("transport", "Mobility"), ("vehicle", "Mobility"), ("car ", "Mobility"), ("fleet", "Mobility"), ("traffic", "Mobility"),
        ("logistic", "Logistics"), ("supply chain", "Logistics"), ("warehouse", "Logistics"), ("freight", "Logistics"), ("shipping", "Logistics"), ("inventory", "Logistics"), ("stock management", "Logistics"),
        ("hr", "HR"), ("hiring", "HR"), ("talent", "HR"), ("recruit", "HR"), ("culture book", "HR"), ("onboarding", "HR"), ("employee", "HR"), ("team", "HR"),
        ("non-profit", "Non-Profit"), ("nonprofit", "Non-Profit"), ("charity", "Non-Profit"), ("ngo", "Non-Profit"), ("volunteer", "Non-Profit"), ("foundation", "Non-Profit"), ("community", "Non-Profit"),
        ("industrial", "Industrial"), ("manufactur", "Industrial"), ("factory", "Industrial"), ("engineering", "Industrial"), ("construction", "Industrial"), ("chemistry", "Industrial"),
        ("media", "Media"), ("editorial", "Media"), ("magazine", "Media"), ("photo", "Media"), ("music", "Media"), ("art", "Media"), ("lettering", "Media"), ("journal", "Media"), ("film", "Media"), ("video", "Media"), ("podcast", "Media"),
        ("enterprise", "Enterprise"), ("b2b", "Enterprise"), ("consulting", "Enterprise"), ("mckinsey", "Enterprise"), ("corporate", "Enterprise"), ("executive", "Enterprise"), ("quarterly", "Enterprise"), ("annual", "Enterprise"), ("debrief", "Enterprise"),
        ("consumer", "Consumer"), ("personal", "Consumer"), ("calendar", "Consumer"), ("lifestyle", "Consumer"), ("planner", "Consumer"),
        ("agency", "Agency"), ("studio", "Agency"), ("brand", "Agency"), ("creative", "Agency"), ("portfolio", "Agency"), ("pitch", "Agency"),
    ]
    for kw, ind in rules:
        if kw in low:
            return ind

    # Deterministic category-aware spread so neutral templates don't pile into Agency
    cat_pools = {
        "Pitch": ["SaaS", "AI", "Fintech", "Marketplace", "Crypto", "Consumer"],
        "Guideline": ["Agency", "Media", "Fashion", "Beauty", "Consumer"],
        "Report": ["Enterprise", "Fintech", "Climate", "Industrial", "Healthcare"],
        "Talks": ["Education", "AI", "Media", "Security", "Aerospace"],
        "Portfolio": ["Agency", "Real Estate", "Media", "Fashion", "Hardware"],
        "Marketing": ["Ecommerce", "Consumer", "Food & Beverage", "Beauty", "Travel"],
        "Sales": ["SaaS", "Enterprise", "Ecommerce", "Marketplace", "Logistics"],
        "Strategy": ["Enterprise", "Mobility", "Climate", "Fintech", "AI"],
        "Proposal": ["Enterprise", "Agency", "Logistics", "Real Estate", "Industrial"],
        "Other": ["Education", "Non-Profit", "Travel", "Sports", "Other"],
    }
    pool = cat_pools.get(category, VALID_INDUSTRIES)
    h = int(hashlib.md5((slug or text).encode("utf-8", errors="ignore")).hexdigest(), 16)
    return pool[h % len(pool)]


def infer_category(text: str, default: str = "Other", slug: str = "") -> str:
    low = text.lower()
    if any(k in low for k in ["pitch", "investor", "series a", "series b", "seed", "startup", "fundraising", "venture"]):
        return "Pitch"
    if any(k in low for k in ["portfolio", "showcase", "case study", "architect", "resume", "cv ", "lookbook", "gallery"]):
        return "Portfolio"
    if any(k in low for k in ["proposal", "rfp", "offer", "quote", "scope of work", "project plan", "implementation"]):
        return "Proposal"
    if any(k in low for k in ["strategy", "roadmap", "consulting", "decision", "playbook", "business plan", "vision", "okr", "framework"]):
        return "Strategy"
    if any(k in low for k in ["sales", "solution", "product", "demo", "playful", "pricing", "funnel", "crm", "revenue"]):
        return "Sales"
    if any(k in low for k in ["marketing", "campaign", "launch", "growth", "social", "brand refresh", "seo", "content", "newsletter"]):
        return "Marketing"
    if any(k in low for k in ["guideline", "brand", "style", "identity", "design system", "ui", "handbook", "culture book", "template"]):
        return "Guideline"
    if any(k in low for k in ["report", "annual", "quarterly", "budget", "review", "financial", "analytics", "data", "audit", "statistics", "debrief"]):
        return "Report"
    if any(k in low for k in ["talk", "keynote", "conference", "lecture", "workshop", "guide", "explainer", "story", "course", "lesson", "chapter", "seminar", "study", "session"]):
        return "Talks"
    if default in VALID_CATEGORIES and default != "Other":
        return default
    # Balanced spread across underrepresented categories for neutral generic decks
    bal = ["Strategy", "Proposal", "Portfolio", "Marketing", "Sales", "Pitch", "Talks", "Other"]
    h = int(hashlib.md5((slug or text).encode("utf-8", errors="ignore")).hexdigest(), 16)
    return bal[h % len(bal)]


def norm_dedup_key(text: str) -> str:
    s = re.sub(r"^(?:gh|ia|sc)[-_]+", "", text.strip(), flags=re.IGNORECASE)
    s = re.sub(r"[-_][0-9a-f]{4}$", "", s, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def inner_text_fingerprint(pptx_path: Path) -> str | None:
    try:
        with zipfile.ZipFile(pptx_path, "r") as z:
            sfs = sorted(
                [n for n in z.namelist() if re.match(r"^ppt/slides/slide\d+\.xml$", n)],
                key=lambda s: int("".join(filter(str.isdigit, Path(s).stem)) or 0),
            )
            chunks = []
            for sf in sfs[:3]:
                raw = z.read(sf).decode("utf-8", "ignore")
                for t in re.findall(r"<a:t>([^<]+)</a:t>", raw):
                    ts = t.strip()
                    if ts and not any(tok in ts.upper() for tok in ("AVANT //", "MORPH", "KINETIC")):
                        chunks.append(ts.lower())
            joined = re.sub(r"\s+", "", "".join(chunks))
            if len(joined) >= 14:
                return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:24]
    except Exception:
        pass
    return None


def gather_sources() -> list[dict]:
    entries = []
    seen_hashes = set()
    seen_norm_stems = set()
    seen_urls = set()
    seen_text_hashes = set()
    used_slugs = set()
    used_titles = set()

    def unique_slug(base: str) -> str:
        s = slugify(base)
        if s not in used_slugs:
            used_slugs.add(s)
            return s
        n = 2
        while f"{s}-{n}" in used_slugs:
            n += 1
        used_slugs.add(f"{s}-{n}")
        return f"{s}-{n}"

    # 1. Curated index (existing + newly authored category decks)
    if CURATED_INDEX.exists():
        curated = json.loads(CURATED_INDEX.read_text(encoding="utf-8"))
        for item in curated:
            p = Path(item["path"])
            if not p.exists():
                continue
            h = sha256_file(p)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            slug = unique_slug(item.get("slug") or p.stem)
            ns = norm_dedup_key(slug)
            if ns:
                seen_norm_stems.add(ns)
            if item.get("sourceUrl"):
                seen_urls.add(item["sourceUrl"].strip())
            th = inner_text_fingerprint(p)
            if th:
                seen_text_hashes.add(th)
            cat = item.get("category", "Other")
            if cat not in VALID_CATEGORIES:
                cat = infer_category(cat)
            ind = item.get("industry", "Other")
            if ind not in VALID_INDUSTRIES:
                ind = infer_industry(f"{item.get('title','')} {item.get('description','')}")
            entries.append({
                "src_path": p,
                "slug": slug,
                "title": item.get("title") or p.stem.replace("_", " ").replace("-", " ").title(),
                "description": item.get("description") or "",
                "category": cat,
                "industry": ind,
                "tags": item.get("tags") or [],
                "curation_tier": "studio-curated",
                "source": item.get("source") or "PPT Studio Curated",
                "sourceUrl": item.get("sourceUrl") or "",
            })

    # 2. BlackArch scraped decks
    scraped_meta_map = {}
    if SCRAPED_META.exists():
        raw_meta = json.loads(SCRAPED_META.read_text(encoding="utf-8"))
        if isinstance(raw_meta, dict):
            scraped_meta_map = raw_meta
        elif isinstance(raw_meta, list):
            for m in raw_meta:
                fn = m.get("filename") or Path(m.get("path", "")).name
                if fn:
                    scraped_meta_map[fn] = m

    if SCRAPED_DIR.exists():
        for p in sorted(SCRAPED_DIR.rglob("*.pptx")):
            if p.name.endswith(".tmp.pptx") or not p.exists():
                continue
            if not has_real_ooxml_content(p):
                continue
            h = sha256_file(p)
            if h in seen_hashes:
                continue
            meta = scraped_meta_map.get(p.name, {})
            src_u = (meta.get("source_url") or meta.get("sourceUrl") or "").strip()
            ns = norm_dedup_key(p.stem)
            th = inner_text_fingerprint(p)
            if (ns and ns in seen_norm_stems) or (src_u and src_u in seen_urls) or (th and th in seen_text_hashes):
                continue
            seen_hashes.add(h)
            if ns:
                seen_norm_stems.add(ns)
            if src_u:
                seen_urls.add(src_u)
            if th:
                seen_text_hashes.add(th)
            slide_snips = extract_slide_texts(p, max_slides=4)
            raw_title = meta.get("inferred_title") or meta.get("title") or p.stem
            title = clean_editorial_title(raw_title, stem=p.stem, slide_texts=slide_snips)
            snippet = meta.get("snippet_text") or " ".join(slide_snips)
            cat_raw = meta.get("inferred_category") or meta.get("category") or ""
            cat = infer_category(f"{title} {p.name} {snippet} {meta.get('source_url','')}", default=cat_raw, slug=p.stem)
            ind = meta.get("industry") if meta.get("industry") in VALID_INDUSTRIES else infer_industry(f"{title} {p.name} {snippet}", category=cat, slug=p.stem)
            slug = unique_slug(p.stem)
            t_low = title.strip().lower()
            if len(t_low) < 14 or t_low in used_titles:
                suffix_code = slug.split("-")[-1].upper()[:6]
                title = f"{title} — {cat} · {ind} ({suffix_code})"
            used_titles.add(title.strip().lower())
            polish_status = meta.get("polish_status") or "auto-polished"
            entries.append({
                "src_path": p,
                "slug": slug,
                "title": title,
                "description": (
                    meta.get("description")
                    or f"Editorial {cat.lower()} presentation crafted for {ind}—combining kinetic Morph transitions, layered visual staging, and fully editable native PowerPoint layouts."
                ),
                "category": cat,
                "industry": ind,
                "tags": list(dict.fromkeys([*(meta.get("tags") or ["free-download"]), polish_status])),
                "curation_tier": polish_status,
                "source": meta.get("source") or "Open Presentation Archive",
                "sourceUrl": meta.get("source_url") or meta.get("sourceUrl") or "",
            })

    return entries


def optimize_png_file(png_path: Path) -> None:
    """Compact PNG preview to 960x540 indexed palette without hurting sharpness."""
    try:
        with Image.open(png_path) as img:
            if img.width > 960:
                img = img.resize((960, max(1, int(img.height * (960 / img.width)))), Image.LANCZOS)
            rgb = img.convert("RGB") if img.mode != "RGB" else img
            q = rgb.quantize(colors=256, method=Image.FASTOCTREE)
            buf = io.BytesIO()
            q.save(buf, format="PNG", optimize=True)
            data = buf.getvalue()
            if len(data) < png_path.stat().st_size:
                png_path.write_bytes(data)
    except Exception:
        pass


def render_with_powerpoint(deck_jobs: list[tuple[str, Path, Path, str]], refresh_covers: bool = False):
    """Render slide PNGs via PowerPoint COM (960x540 + quantized) cleanly."""
    pending = []
    for slug, p, out_dir, tier in deck_jobs:
        existing = sorted(out_dir.glob("slide_*.png"))
        if not existing:
            pending.append((slug, p, out_dir, "all"))
        elif refresh_covers and tier == "auto-polished":
            s1 = out_dir / "slide_01.png"
            if not s1.exists() or p.stat().st_mtime > s1.stat().st_mtime:
                pending.append((slug, p, out_dir, "covers"))

    if not pending:
        print("All deck preview PNGs already rendered.")
        return

    import win32com.client
    app = win32com.client.Dispatch("PowerPoint.Application")
    try:
        app.DisplayAlerts = 1  # ppAlertsNone
    except Exception:
        pass

    try:
        total_pending = len(pending)
        for p_idx, (slug, pptx_path, out_dir, mode) in enumerate(pending, start=1):
            out_dir.mkdir(parents=True, exist_ok=True)
            prs = None
            try:
                prs = app.Presentations.Open(str(pptx_path), ReadOnly=True, Untitled=False, WithWindow=False)
                exported = 0
                max_n = 1 if mode == "covers" else 16
                for idx, slide in enumerate(prs.Slides, start=1):
                    if idx > max_n:
                        break
                    out_png = out_dir / f"slide_{idx:02d}.png"
                    slide.Export(str(out_png), "PNG", 960, 540)
                    optimize_png_file(out_png)
                    exported = idx
                if p_idx % 25 == 0 or p_idx <= 5 or p_idx == total_pending:
                    print(f"[RENDER {p_idx}/{total_pending}] ({mode}) {slug} ({exported} slides)", flush=True)
            except Exception as exc:
                print(f"[RENDER ERR {p_idx}/{total_pending}] {slug}: {exc}", flush=True)
            finally:
                if prs is not None:
                    try:
                        prs.Close()
                    except Exception:
                        pass
    finally:
        try:
            app.Quit()
        except Exception:
            pass


def link_or_copy(src: Path, dst: Path) -> None:
    if dst.exists():
        try:
            if os.path.samefile(src, dst):
                return
        except OSError:
            pass
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-covers", action="store_true", help="Re-export slide_01 & slide_02 for auto-polished decks")
    args = parser.parse_args()

    PPTX_PUBLIC.mkdir(parents=True, exist_ok=True)
    PREVIEWS_PUBLIC.mkdir(parents=True, exist_ok=True)
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)

    # Remove seed SVG placeholders and avoid static public/api/decks.json collision with Astro route
    for svg_file in PREVIEWS_PUBLIC.glob("*.svg"):
        svg_file.unlink(missing_ok=True)
    stale_api = GALLERY_DIR / "public" / "api" / "decks.json"
    if stale_api.exists():
        stale_api.unlink()

    sources = gather_sources()
    valid_slugs = {s["slug"] for s in sources}
    for orphan_pptx in PPTX_PUBLIC.glob("*.pptx"):
        if orphan_pptx.stem not in valid_slugs:
            orphan_pptx.unlink(missing_ok=True)

    print(f"Total unique valid PPTX decks gathered: {len(sources)}")

    render_jobs = []
    for item in sources:
        dst_pptx = PPTX_PUBLIC / f"{item['slug']}.pptx"
        link_or_copy(item["src_path"], dst_pptx)
        item["dst_pptx"] = dst_pptx
        render_jobs.append((item["slug"], dst_pptx, PREVIEWS_PUBLIC / item["slug"], item.get("curation_tier", "studio-curated")))

    render_with_powerpoint(render_jobs, refresh_covers=args.refresh_covers)

    family_map_path = Path(r"D:\code\ppt_studio\design_families_map.json")
    family_map = json.loads(family_map_path.read_text(encoding="utf-8")) if family_map_path.exists() else {}

    decks_json = []
    for item in sources:
        slug = item["slug"]
        dst_pptx = item["dst_pptx"]
        stats = analyze_pptx(dst_pptx)
        slide_texts = extract_slide_texts(dst_pptx)
        preview_files = sorted((PREVIEWS_PUBLIC / slug).glob("slide_*.png"))
        slides_preview = [f"/previews/{slug}/{pf.name}" for pf in preview_files]
        if not slides_preview:
            dst_pptx.unlink(missing_ok=True)
            continue  # Skip any deck that failed rendering completely

        fam_info = family_map.get(slug, {"id": "swiss_grid_white", "label": "Editorial Archive"})
        has_morph = stats["morph_slides"] > 0
        has_anim = stats["animation_slides"] > 0
        fonts = stats["top_fonts"] or [
            v for v in (stats.get("theme_fonts") or {}).values() if v
        ]
        fonts = list(dict.fromkeys(fonts))[:5]
        colors = stats["top_colors"][:6]
        curation_tier = item.get("curation_tier", "studio-curated")
        tags = list(dict.fromkeys([
            *(item["tags"] or []),
            fam_info["id"],
            curation_tier,
            *(["morph"] if has_morph else []),
            *(["animated"] if has_anim else []),
            "free-pptx",
        ]))

        desc = item["description"].strip()
        if not desc:
            desc = (
                f"Editorial {item['category'].lower()} presentation crafted for {item['industry']} "
                f"({stats['slides']} slides, {fam_info['label']} design system"
                + (f", {stats['morph_slides']} Morph transitions" if has_morph else "")
                + ")."
            )

        font_pair = " + ".join(fonts[:2]) if fonts else "Theme Default"
        palette_str = ", ".join(colors[:3]) if colors else "Theme scheme palette"
        morph_note = (
            f"{stats['morph_slides']} Morph slides ({stats['paired_morph_slides']} paired actor matches, {stats['morph_actor_count']} !! actors)"
            if has_morph
            else ("OOXML timeline animations" if has_anim else "Clean static editorial transitions")
        )
        snippet_note = f" | Key slides: {' // '.join(slide_texts[:2])}" if slide_texts else ""
        blueprint_str = (
            f"[{fam_info['label']}] {stats['slides']} slides at {stats['avg_shapes_per_slide']} shapes/slide; "
            f"typography {font_pair}; palette [{palette_str}]; "
            f"motion: {morph_note}.{snippet_note}"
        )

        deck_num = len(decks_json) + 1
        decks_json.append({
            "id": f"deck-{deck_num:03d}",
            "slug": slug,
            "title": item["title"],
            "description": desc,
            "category": item["category"],
            "industry": item["industry"],
            "designFamily": fam_info["label"],
            "curationTier": curation_tier,
            "tags": tags,
            "slidesCount": stats["slides"],
            "avgShapesPerSlide": stats["avg_shapes_per_slide"],
            "morphSlides": stats["morph_slides"],
            "pairedMorphSlides": stats["paired_morph_slides"],
            "animationSlides": stats["animation_slides"],
            "hasMorph": has_morph,
            "hasAnimation": has_anim,
            "fonts": fonts,
            "colors": colors,
            "transitions": stats["transitions"],
            "sizeKb": stats["size_kb"],
            "source": item["source"],
            "sourceUrl": item["sourceUrl"],
            "pptxUrl": f"/pptx/{slug}.pptx",
            "coverImage": slides_preview[0],
            "slidesPreview": slides_preview,
            "blueprintSummary": blueprint_str,
        })

    DATA_OUT.write_text(json.dumps(decks_json, indent=2, ensure_ascii=False), encoding="utf-8")

    # Generate llms.txt for external AIs (zero MCP needed!)
    llms_txt = (
        "# Deckhouse — Kinetic & Avant-Garde Presentation Archive (LLM & Agent Guide)\n\n"
        "> Status: Early Experimental Build (`v0.2-dev`). Verify outputs with `python studio_engine/ai_slide_director.py audit <file.pptx>` or inspect live slide strips on the site.\n\n"
        f"Total curated `.pptx` presentation systems: {len(decks_json)}\n\n"
        "## Primary Entry Points (Zero MCP Required)\n"
        "- Agent Skill Instructions: /SKILL.md\n"
        "- Technical README & Organic Layer Deconstruction: /README.md\n"
        "- Machine-Readable JSON Catalog: GET /api/decks.json\n"
        "- Native Editable OOXML Download: GET /pptx/<slug>.pptx\n"
        "- Slide Keyframe PNG Previews: GET /previews/<slug>/slide_01.png\n"
        "- Art Director Storyboard & Audit CLI: studio_engine/ai_slide_director.py\n\n"
        "## CLI Tools for External AI Agents\n"
        "1. Plan an organic DNA-preserving multi-stage storyboard before writing slide XML:\n"
        "   python studio_engine/ai_slide_director.py storyboard --title \"<Topic>\" --category \"Pitch\" --industry \"AI & DeepTech\"\n"
        "   (Pass --pptx <source.pptx> to extract real color & typography DNA from an existing deck.)\n"
        "2. Lint and score any `.pptx` archive (0-100 DNA coherence & Morph scorecard):\n"
        "   python studio_engine/ai_slide_director.py audit <path/to/deck.pptx>\n\n"
        "## Core Presentation Rules\n"
        "1. Fixed 16:9 canvas: 33.87 x 19.05 cm (12192000 x 6858000 EMU), outer safe margins >= 1.4 cm.\n"
        "2. Preserve authentic DNA (color palette, monochrome character, typography) across every slide; never clash unrelated themes.\n"
        "3. Deconstruct layers organically according to content complexity (no fixed 15-slide quota, no rigid 8-box stencil), pairing persistent shapes with `!!`-prefixed `<p:cNvPr name=\"!!sXX-layer-YY\"/>` attributes and `<p159:morph option=\"byObject\"/>` (`<p:fade/>` fallback).\n\n"
        "## Categories\n"
        + ", ".join(VALID_CATEGORIES)
        + "\n"
    )
    LLMS_OUT.write_text(llms_txt, encoding="utf-8")

    from collections import Counter
    cats = Counter(d["category"] for d in decks_json)
    print(f"\nCompiled {len(decks_json)} decks -> {DATA_OUT}")
    print("Category distribution:", dict(cats))


if __name__ == "__main__":
    main()
