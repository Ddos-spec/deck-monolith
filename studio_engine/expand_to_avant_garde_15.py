"""
Avant-Garde 15-Slide Multi-System Architecture Engine (16 Distinct Design Families)
Replaces uniform MODNEXUS cloning with 16 radically distinct Avant-Garde editorial,
Swiss, Bauhaus, Brutalist, Luxury, Blueprint, Zen, and Modular Bento design systems.

Guarantees:
  - Preserves MODNEXUS (`modnexus-global-modding-union`) untouched as Specimen #1.
  - Recovers each deck's original PowerPoint-rendered slides (`orig_png_map`) by mapping
    non-`av_slide_*` positions in the current `<p:sldIdLst>` before rebuilding.
  - Extracts up to 4 native topic images from each deck's own `ppt/media/` (alpha-composited
    onto the assigned design system's surface background) before supplementing from the
    210-plate `visual_asset_bank`.
  - Renders 1:1 2x-supersampled (1920x1080 -> 960x540) preview PNGs matching the OOXML
    slides and interleaves them seamlessly with recovered original slides.
  - Attaches `<p159:morph option="byObject"/>`, `<p:timing>` entrance choreography, and
    consistent `!!scene-*` / `!!actor-*` Morph names across consecutive keyframes.
  - Writes `D:\\code\\ppt_studio\\design_families_map.json` so `compile_deck_gallery.py`
    tags every deck with its true architectural movement.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import math
import os
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

BASE_DIR = Path(r"D:\code\ppt_studio")
ASSET_BANK_DIR = BASE_DIR / "visual_asset_bank"
ASSET_MANIFEST = ASSET_BANK_DIR / "manifest.json"
CURATED_INDEX = BASE_DIR / "curated_index.json"
CURATED_OUT_DIR = BASE_DIR / "corpus_curated_v2"
SCRAPED_DIR = BASE_DIR / "corpus_scraped"
SCRAPED_META = SCRAPED_DIR / "scraped_meta.json"
FAMILY_MAP_PATH = BASE_DIR / "design_families_map.json"
PREVIEWS_DIR = Path(r"D:\code\deck_gallery\public\previews")

CANVAS_W_CM = 33.87
CANVAS_H_CM = 19.05
CANVAS_W_EMU = 12192000
CANVAS_H_EMU = 6858000

NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
NS_P159 = "http://schemas.microsoft.com/office/powerpoint/2015/09/main"
NS_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"

MORPH_TRANSITION_XML = (
    f'<p:transition xmlns:p="{NS_P}" xmlns:p14="{NS_P14}" xmlns:mc="{NS_MC}" '
    f'xmlns:p159="{NS_P159}" spd="med" p14:dur="850" advClick="1">'
    f'<mc:AlternateContent><mc:Choice Requires="p159"><p159:morph option="byObject"/></mc:Choice>'
    f'<mc:Fallback><p:fade/></mc:Fallback></mc:AlternateContent></p:transition>'
)

# 16 Distinct Avant-Garde Architectural Design Systems
DESIGN_FAMILIES: list[dict[str, Any]] = [
    {
        "id": "swiss_grid_white",
        "label": "Swiss Grid White",
        "is_dark": False,
        "bg": "F8F7F4", "panel": "ECE9E1", "card": "FFFFFF",
        "ink": "111827", "muted": "4B5563", "rule": "D1CDC4",
        "acc1": "E0311B", "acc2": "1D4ED8", "on_acc1": "FFFFFF", "on_acc2": "FFFFFF",
        "head_font": "display", "body_font": "sans", "serif_sub": "serif",
    },
    {
        "id": "kinfolk_warm_editorial",
        "label": "Warm Sand Editorial",
        "is_dark": False,
        "bg": "F4EFE6", "panel": "EAE2D4", "card": "FAF7F1",
        "ink": "1C1917", "muted": "57534E", "rule": "D6CEC0",
        "acc1": "9A3412", "acc2": "3F6212", "on_acc1": "FFFFFF", "on_acc2": "FFFFFF",
        "head_font": "serif", "body_font": "sans", "serif_sub": "serif",
    },
    {
        "id": "bauhaus_constructivist",
        "label": "Weimar Bauhaus",
        "is_dark": False,
        "bg": "F7F3E8", "panel": "EBE4D2", "card": "FFFFFF",
        "ink": "121212", "muted": "44403C", "rule": "121212",
        "acc1": "E03C1F", "acc2": "1D4ED8", "acc3": "EAB308", "on_acc1": "FFFFFF", "on_acc2": "FFFFFF",
        "head_font": "display", "body_font": "sans", "serif_sub": "sans",
    },
    {
        "id": "pentagram_split_poster",
        "label": "Pentagram Pigment Split",
        "is_dark": False,
        "bg": "FAF8F5", "panel": "EFECE6", "card": "FFFFFF",
        "ink": "141413", "muted": "52525B", "rule": "D4D0C8",
        "acc1": "991B1B", "acc2": "0F766E", "on_acc1": "FFFFFF", "on_acc2": "FFFFFF",
        "head_font": "display", "body_font": "sans", "serif_sub": "serif",
    },
    {
        "id": "ft_salmon_financial",
        "label": "FT Salmon Monograph",
        "is_dark": False,
        "bg": "F6DEC8", "panel": "EDD0B5", "card": "FDF5ED",
        "ink": "111827", "muted": "4B5563", "rule": "7F1D1D",
        "acc1": "7F1D1D", "acc2": "0F766E", "on_acc1": "FFFFFF", "on_acc2": "FFFFFF",
        "head_font": "serif", "body_font": "sans", "serif_sub": "serif",
    },
    {
        "id": "luxury_atelier_noir",
        "label": "Luxury Atelier Noir",
        "is_dark": True,
        "bg": "141312", "panel": "1F1D1B", "card": "191716",
        "ink": "F5F2EB", "muted": "A8A29E", "rule": "D4AF37",
        "acc1": "D4AF37", "acc2": "B45309", "on_acc1": "141312", "on_acc2": "FFFFFF",
        "head_font": "serif", "body_font": "sans", "serif_sub": "serif",
    },
    {
        "id": "brutalist_tabloid_press",
        "label": "Brutalist Broadsheet",
        "is_dark": False,
        "bg": "EAE6DF", "panel": "DDD7CC", "card": "F7F5F0",
        "ink": "0F0F0F", "muted": "3F3F46", "rule": "0F0F0F",
        "acc1": "DC2626", "acc2": "0F0F0F", "on_acc1": "FFFFFF", "on_acc2": "FFFFFF",
        "head_font": "display", "body_font": "sans", "serif_sub": "serif",
    },
    {
        "id": "apple_bento_modular",
        "label": "Modular Bento Grid",
        "is_dark": False,
        "bg": "F1F5F9", "panel": "E2E8F0", "card": "FFFFFF",
        "ink": "0F172A", "muted": "475569", "rule": "CBD5E1",
        "acc1": "2563EB", "acc2": "0F172A", "on_acc1": "FFFFFF", "on_acc2": "FFFFFF",
        "head_font": "display", "body_font": "sans", "serif_sub": "sans",
    },
    {
        "id": "architectural_blueprint",
        "label": "Architectural Blueprint",
        "is_dark": True,
        "bg": "0B2545", "panel": "13315C", "card": "0F2C52",
        "ink": "F0F9FF", "muted": "93C5FD", "rule": "38BDF8",
        "acc1": "38BDF8", "acc2": "F59E0B", "on_acc1": "0B2545", "on_acc2": "0B2545",
        "head_font": "display", "body_font": "mono", "serif_sub": "sans",
    },
    {
        "id": "botanical_sage_organic",
        "label": "Botanical Sage Folio",
        "is_dark": False,
        "bg": "EBF1EC", "panel": "DCE6DE", "card": "F9FBF9",
        "ink": "143326", "muted": "3B5C4E", "rule": "B8CABD",
        "acc1": "143326", "acc2": "C2410C", "on_acc1": "F9FBF9", "on_acc2": "FFFFFF",
        "head_font": "serif", "body_font": "sans", "serif_sub": "serif",
    },
    {
        "id": "neo_brutalist_acid",
        "label": "Neo-Brutalist Pop",
        "is_dark": False,
        "bg": "FEF3C7", "panel": "FDE68A", "card": "FFFFFF",
        "ink": "09090B", "muted": "27272A", "rule": "09090B",
        "acc1": "EF4444", "acc2": "2563EB", "on_acc1": "FFFFFF", "on_acc2": "FFFFFF",
        "head_font": "display", "body_font": "sans", "serif_sub": "sans",
    },
    {
        "id": "japanese_ma_zen",
        "label": "Kyoto Ma-Zen",
        "is_dark": False,
        "bg": "FAF8F2", "panel": "EFECE2", "card": "FFFFFF",
        "ink": "1C1917", "muted": "57534E", "rule": "D6D1C4",
        "acc1": "DC2626", "acc2": "292524", "on_acc1": "FFFFFF", "on_acc2": "FFFFFF",
        "head_font": "serif", "body_font": "sans", "serif_sub": "serif",
    },
    {
        "id": "cyber_pulse_quantum",
        "label": "Quantum Deep Field",
        "is_dark": True,
        "bg": "070B19", "panel": "101830", "card": "0D1428",
        "ink": "F8FAFC", "muted": "94A3B8", "rule": "1E293B",
        "acc1": "06B6D4", "acc2": "A855F7", "on_acc1": "070B19", "on_acc2": "FFFFFF",
        "head_font": "display", "body_font": "sans", "serif_sub": "mono",
    },
    {
        "id": "risograph_duotone_poster",
        "label": "Risograph Overprint",
        "is_dark": False,
        "bg": "F5EBE0", "panel": "EADBC8", "card": "FCF8F4",
        "ink": "1E1B4B", "muted": "4338CA", "rule": "D5C3B0",
        "acc1": "F43F5E", "acc2": "0D9488", "on_acc1": "FFFFFF", "on_acc2": "FFFFFF",
        "head_font": "display", "body_font": "sans", "serif_sub": "serif",
    },
    {
        "id": "vignelli_canon_band",
        "label": "Vignelli Canon Grid",
        "is_dark": False,
        "bg": "F9F8F6", "panel": "EDEBE6", "card": "FFFFFF",
        "ink": "111827", "muted": "4B5563", "rule": "D1CFC8",
        "acc1": "B91C1C", "acc2": "1E3A8A", "on_acc1": "FFFFFF", "on_acc2": "FFFFFF",
        "head_font": "display", "body_font": "sans", "serif_sub": "sans",
    },
    {
        "id": "gallery_diptych_spread",
        "label": "Museum Diptych Spread",
        "is_dark": False,
        "bg": "EDE9E0", "panel": "E2DDD1", "card": "FAF8F5",
        "ink": "18181B", "muted": "52525B", "rule": "C8C1B4",
        "acc1": "1E3A8A", "acc2": "B45309", "on_acc1": "FFFFFF", "on_acc2": "FFFFFF",
        "head_font": "serif", "body_font": "sans", "serif_sub": "serif",
    },
]

# Affinity biases by industry/category (rotates cleanly with deck hash so every vertical sees variety)
INDUSTRY_PREFERRED_FAMILIES: dict[str, list[int]] = {
    "Fintech": [4, 0, 14, 7, 5, 6],
    "Enterprise": [0, 4, 14, 7, 1, 15],
    "SaaS": [7, 0, 12, 10, 8, 14],
    "AI": [12, 8, 7, 10, 0, 2],
    "Fashion": [5, 1, 15, 11, 13, 3],
    "Beauty": [1, 5, 9, 15, 13, 11],
    "Architecture": [8, 0, 11, 15, 6, 1],
    "Real Estate": [1, 8, 0, 15, 5, 14],
    "Media": [6, 13, 3, 2, 10, 15],
    "Agency": [2, 10, 3, 13, 0, 6],
    "Climate": [9, 1, 11, 4, 15, 7],
    "Healthcare": [9, 0, 7, 1, 14, 8],
    "Education": [2, 14, 1, 4, 13, 9],
    "Hardware": [8, 2, 7, 12, 0, 10],
    "Aerospace": [12, 8, 0, 14, 5, 7],
    "Crypto": [12, 10, 6, 5, 8, 3],
    "Food & Beverage": [1, 9, 13, 3, 4, 10],
    "Travel": [1, 11, 15, 9, 3, 4],
    "Sports": [6, 10, 14, 3, 2, 12],
    "Gaming": [10, 12, 6, 13, 3, 2],
}

FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def load_ttf(role: str, size_px: int, text: str = "") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    has_cjk = any(ord(ch) > 0x2E80 for ch in text)
    eff_role = "cjk" if has_cjk else role
    key = (eff_role, size_px)
    if key in FONT_CACHE:
        return FONT_CACHE[key]
    candidates = {
        "cjk": [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\simhei.ttf"],
        "display": [r"C:\Windows\Fonts\bahnschrift.ttf", r"C:\Windows\Fonts\arialbd.ttf"],
        "serif": [r"C:\Windows\Fonts\georgia.ttf", r"C:\Windows\Fonts\times.ttf"],
        "mono": [r"C:\Windows\Fonts\consolab.ttf", r"C:\Windows\Fonts\consola.ttf"],
        "sans": [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"],
        "sans_bold": [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"],
    }.get(eff_role, [r"C:\Windows\Fonts\segoeui.ttf"])
    font = None
    for path in candidates:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, max(8, size_px))
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()
    FONT_CACHE[key] = font
    return font


def hex_rgba(h: str, alpha_0_100k: int = 100000) -> tuple[int, int, int, int]:
    h = h.lstrip("#").upper()
    if len(h) != 6:
        h = "111827"
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(round(alpha_0_100k * 255 / 100000)))


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#").upper()
    if len(h) != 6:
        h = "F6F3EC"
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-") or "deck"


def clean_title_for_slide(raw: str) -> str:
    s = re.sub(r"^(?:gh|ia|sc)[-_]+", "", (raw or "").strip(), flags=re.IGNORECASE)
    s = re.sub(r"[-_][0-9a-f]{4}$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\d{6,}[_-]*", "", s)
    s = re.sub(r"\.(pptx?|key|pdf)$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[_~]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" —-")
    return s or "Editorial Presentation"


def pick_design_family(slug: str, category: str, industry: str, deck_idx: int) -> dict[str, Any]:
    """Select an Avant-Garde family deterministically while maximizing variety across neighbors."""
    h = int(hashlib.md5(f"{slug}:{category}:{industry}".encode("utf-8", "ignore")).hexdigest(), 16)
    prefs = INDUSTRY_PREFERRED_FAMILIES.get(industry)
    if prefs and (deck_idx % 3 != 2):
        idx = prefs[(deck_idx + h) % len(prefs)]
    else:
        idx = (deck_idx * 5 + h) % len(DESIGN_FAMILIES)
    return dict(DESIGN_FAMILIES[idx], index=idx)


def safe_pic_box(max_w: float, max_h: float, aspect: float) -> tuple[float, float]:
    asp = max(0.6, min(2.2, aspect or 1.4))
    w = max_w
    h = w / asp
    if h > max_h:
        h = max_h
        w = h * asp
    return round(w, 3), round(h, 3)


def wrap_headline(title: str, max_chars: int = 16, max_lines: int = 3, upper: bool = False) -> str:
    words = [w for w in re.split(r"\s+", title.strip()) if w]
    if not words:
        return "EDITORIAL WORK" if upper else "Editorial Work"
    lines: list[str] = []
    cur = ""
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


def extract_native_deck_media(zin: zipfile.ZipFile, surface_bg_hex: str) -> list[dict[str, Any]]:
    """Extract up to 4 native non-screenshot images from a deck's ppt/media/ folder."""
    bg_rgb = hex_rgb(surface_bg_hex)
    candidates: list[tuple[float, dict[str, Any]]] = []
    names = [
        n for n in zin.namelist()
        if n.startswith("ppt/media/")
        and not n.startswith("ppt/media/av_art_")
        and n.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    names.sort(key=lambda n: zin.getinfo(n).file_size, reverse=True)

    for part in names[:14]:
        info = zin.getinfo(part)
        if info.file_size < 12_000 or info.file_size > 6_000_000:
            continue
        try:
            with Image.open(io.BytesIO(zin.read(part))) as im:
                w, h = im.size
                if w < 260 or h < 180:
                    continue
                ratio = w / max(1, h)
                if ratio < 0.55 or ratio > 2.35:
                    continue
                if im.mode in ("RGBA", "LA", "PA"):
                    canvas = Image.new("RGB", im.size, bg_rgb)
                    rgba = im.convert("RGBA")
                    canvas.paste(rgba, mask=rgba.split()[3])
                    rgb = canvas
                else:
                    rgb = im.convert("RGB")
                thumb = rgb.resize((64, 64), Image.Resampling.BILINEAR)
                px = list(thumb.getdata())
                near_white = sum(1 for r, g, b in px if r > 236 and g > 236 and b > 236) / len(px)
                st = ImageStat.Stat(thumb)
                mean_std = sum(st.stddev) / 3.0
                if near_white > 0.48 or mean_std < 24.0:
                    continue
                if w > 1280:
                    nh = max(1, int(round(h * (1280.0 / w))))
                    rgb = rgb.resize((1280, nh), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                rgb.save(buf, format="JPEG", quality=88, optimize=True)
                raw_jpg = buf.getvalue()
                candidates.append((
                    mean_std + min(w, 1200) * 0.03,
                    {
                        "raw_bytes": raw_jpg,
                        "width": rgb.width,
                        "height": rgb.height,
                        "aspect": round(rgb.width / max(1, rgb.height), 4),
                        "source": f"native:{Path(part).name}",
                    },
                ))
        except Exception:
            continue

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in candidates[:4]]


def extract_deck_context(zin: zipfile.ZipFile, fallback_title: str, category: str, industry: str) -> dict[str, Any]:
    names = zin.namelist()
    slide_files = sorted(
        [n for n in names if re.match(r"^ppt/slides/slide\d+\.xml$", n)],
        key=lambda s: int("".join(filter(str.isdigit, Path(s).stem)) or 0),
    )
    slide_snippets: list[str] = []
    slide1_has_pic = False

    for idx, sf in enumerate(slide_files):
        raw = zin.read(sf).decode("utf-8", "ignore")
        if idx == 0 and ("<p:pic" in raw or "<p:graphicFrame" in raw):
            slide1_has_pic = True
        texts = [
            re.sub(r"\s+", " ", html.unescape(t)).strip()
            for t in re.findall(r"<a:t>([^<]+)</a:t>", raw)
            if t.strip()
            and not any(tok in t.upper() for tok in ("AVANT //", "MORPH ·", "✦ MORPH", "SPEC //", "ACT //"))
            and not re.fullmatch(r"\d{1,3}", t.strip())
        ]
        joined = " — ".join(texts[:4])[:180]
        if joined:
            slide_snippets.append(joined)

    cx_emu, cy_emu = CANVAS_W_EMU, CANVAS_H_EMU
    if "ppt/presentation.xml" in names:
        pxml = zin.read("ppt/presentation.xml").decode("utf-8", "ignore")
        m = re.search(r'<p:sldSz\b[^>]*cx="(\d+)"[^>]*cy="(\d+)"', pxml)
        if m:
            cx_emu, cy_emu = int(m.group(1)), int(m.group(2))

    clean_title = clean_title_for_slide(fallback_title)
    if len(clean_title) < 4 and slide_snippets:
        clean_title = slide_snippets[0][:56]

    return {
        "slide_files": slide_files,
        "snippets": slide_snippets,
        "slide1_has_pic": slide1_has_pic,
        "cx_emu": cx_emu,
        "cy_emu": cy_emu,
        "title": clean_title,
        "category": category or "Strategy",
        "industry": industry or "Enterprise",
    }


def _add_plate_layer(
    layers: list[dict[str, Any]],
    name: str,
    asset: dict[str, Any],
    x: float, y: float, max_w: float, max_h: float,
    align_x: str = "ctr", align_y: str = "ctr",
    border: str | None = None,
    shadow: bool = False,
    rounded: bool = False,
) -> tuple[float, float, float, float]:
    pw, ph = safe_pic_box(max_w, max_h, asset["aspect"])
    if align_x == "l":
        px = x
    elif align_x == "r":
        px = x + (max_w - pw)
    else:
        px = x + (max_w - pw) * 0.5
    if align_y == "t":
        py = y
    elif align_y == "b":
        py = y + (max_h - ph)
    else:
        py = y + (max_h - ph) * 0.5
    layers.append({
        "kind": "pic", "name": name, "asset": asset,
        "x": px, "y": py, "w": pw, "h": ph,
        "rot": 0, "shadow": shadow, "border": border, "rounded": rounded,
    })
    return px, py, pw, ph


def make_keyframe_spec(
    fam: dict[str, Any],
    role: int,
    slot_idx: int,
    target_slide_num: int,
    total_slides: int,
    ctx: dict[str, Any],
    asset_primary: dict[str, Any],
    asset_secondary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate radically distinct slide geometry matching the assigned Design Family."""
    fid = fam["id"]
    bg = fam["bg"]
    panel = fam["panel"]
    card = fam["card"]
    ink = fam["ink"]
    muted = fam["muted"]
    rule = fam["rule"]
    acc1 = fam["acc1"]
    acc2 = fam["acc2"]
    on_acc1 = fam["on_acc1"]
    on_acc2 = fam["on_acc2"]
    hfont = fam["head_font"]
    bfont = fam["body_font"]
    sfont = fam["serif_sub"]

    title = ctx["title"]
    cat = ctx["category"]
    ind = ctx["industry"]
    snips = ctx["snippets"]
    raw_snip = snips[slot_idx % len(snips)] if snips else ""
    beat_head = clean_title_for_slide(raw_snip.split("—")[0])[:44] if raw_snip else ""
    if len(beat_head) < 4:
        beat_head = title[:42]
    lead_copy = raw_snip[:155] if len(raw_snip) > 32 else (
        f"{title} — structured {cat.lower()} perspective across {ind.lower()} initiatives, visual evidence, and sequenced delivery."
    )

    layers: list[dict[str, Any]] = []
    fid_num = fam["index"]
    slide_label = f"{cat.upper()} · {ind.upper()}  //  {target_slide_num:02d} OF {total_slides:02d}"

    # ------------------------------------------------------------------
    # FAMILY 0: SWISS GRID WHITE (#F8F7F4, exposed hairline grid, orthogonal red/blue block)
    # FAMILY 14: VIGNELLI CANON BAND (top solid pigment header + 3-col Swiss grid)
    # ------------------------------------------------------------------
    if fid in ("swiss_grid_white", "vignelli_canon_band"):
        is_vig = fid == "vignelli_canon_band"
        if is_vig:
            band_h = 5.4 if role == 0 else 3.8
            layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-band", "x": 0.0, "y": 0.0, "w": 33.87, "h": band_h, "fill": acc1})
            layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-rule", "x": 0.0, "y": band_h, "w": 33.87, "h": 0.14, "fill": acc2})
            layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"FOLIO {target_slide_num:02d}  /  {cat.upper()}  ·  {ind.upper()}", "x": 1.6, "y": 0.65, "w": 22.0, "h": 0.6, "font": "mono", "size": 10.5, "bold": True, "color": on_acc1})
            layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(title if role == 0 else beat_head, 32 if role > 0 else 24, 2), "x": 1.6, "y": 1.35, "w": 30.5, "h": band_h - 1.5, "font": "display", "size": 34.0 if role == 0 else 26.0, "bold": True, "color": on_acc1, "valign": "ctr"})
            # 3-column exposed grid below band
            grid_cols = (11.5,) if role in (0, 1) else (11.5, 22.5)
            for gx in grid_cols:
                layers.append({"kind": "shape", "preset": "rect", "name": f"#vg-gx-{gx}", "x": gx, "y": band_h + 0.14, "w": 0.04, "h": 19.05 - band_h - 0.8, "fill": rule})
            if role in (0, 1):
                _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 12.1, band_h + 0.85, 20.1, 19.05 - band_h - 1.6, border=ink)
                layers.append({"kind": "text", "name": "!!actor-sub", "text": f"{lead_copy}\n\n• Disciplined Swiss hierarchy\n• Asymmetric column proportion\n• Editable vector & motion cues", "x": 1.6, "y": band_h + 1.0, "w": 9.2, "h": 10.2, "font": "sans", "size": 14.5, "color": ink, "line_spacing": 1.38})
            else:
                cols = [("01 · CONTEXT", lead_copy[:85]), ("02 · STRUCTURE", f"Balanced {total_slides}-slide editorial pacing built for executive legibility."), ("03 · DELIVERY", f"{ind} edition with modular native charts & crisp contrast.")]
                for ci, (ch, cb) in enumerate(cols[:2]):
                    cx_p = 1.6 + ci * 10.7
                    layers.append({"kind": "text", "name": f"#vg-ch-{ci}", "text": ch, "x": cx_p, "y": band_h + 0.9, "w": 9.3, "h": 0.7, "font": "mono", "size": 10.5, "bold": True, "color": acc1})
                    layers.append({"kind": "text", "name": f"#vg-cb-{ci}", "text": cb, "x": cx_p, "y": band_h + 1.8, "w": 9.3, "h": 9.5, "font": "sans", "size": 14.0, "color": muted, "line_spacing": 1.35})
                _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 23.1, band_h + 0.9, 9.2, 11.4, border=ink)
        else:
            # SWISS GRID WHITE
            for gx in (1.4, 16.9, 32.47):
                layers.append({"kind": "shape", "preset": "rect", "name": f"#sw-vl-{gx}", "x": gx, "y": 1.0, "w": 0.04, "h": 17.05, "fill": rule})
            for gy in (1.0, 2.35, 17.65):
                layers.append({"kind": "shape", "preset": "rect", "name": f"#sw-hl-{gy}", "x": 1.4, "y": gy, "w": 31.1, "h": 0.04, "fill": rule})
            layers.append({"kind": "shape", "preset": "rect", "name": "!!actor-badge", "x": 1.4, "y": 1.0, "w": 4.2, "h": 1.35, "fill": acc1})
            layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"NO. {target_slide_num:02d}", "x": 1.4, "y": 1.0, "w": 4.2, "h": 1.35, "font": "mono", "size": 15.0, "bold": True, "color": on_acc1, "align": "ctr", "valign": "ctr"})
            layers.append({"kind": "text", "name": "#sw-hdr", "text": slide_label, "x": 6.1, "y": 1.0, "w": 26.0, "h": 1.35, "font": "mono", "size": 10.5, "bold": True, "color": muted, "valign": "ctr"})
            if role in (0, 2):
                layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(title if role == 0 else beat_head, 15, 3), "x": 1.9, "y": 3.1, "w": 14.3, "h": 7.6, "font": "display", "size": 42.0 if role == 0 else 33.0, "bold": True, "color": ink, "line_spacing": 0.96})
                layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-rule", "x": 1.9, "y": 11.2, "w": 6.5, "h": 0.14, "fill": acc2})
                layers.append({"kind": "text", "name": "!!actor-sub", "text": lead_copy, "x": 1.9, "y": 11.8, "w": 14.2, "h": 4.8, "font": "sans", "size": 14.5, "color": muted, "line_spacing": 1.35})
                _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 17.5, 2.95, 14.3, 14.1, border=ink)
            else:
                layers.append({"kind": "text", "name": "!!actor-ghost-num", "text": f"{target_slide_num:02d}", "x": 17.5, "y": 2.8, "w": 14.3, "h": 5.2, "font": "display", "size": 120.0, "bold": True, "color": panel, "align": "r"})
                _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 1.9, 2.95, 14.3, 10.6, border=rule)
                layers.append({"kind": "text", "name": "#sw-cap", "text": f"{cat} · {ind}  —  Modular 16:9 Architectural Frame", "x": 1.9, "y": 14.1, "w": 14.3, "h": 2.4, "font": "mono", "size": 11.0, "color": muted})
                layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(beat_head, 16, 3), "x": 17.6, "y": 4.2, "w": 14.2, "h": 5.5, "font": "display", "size": 32.0, "bold": True, "color": ink})
                layers.append({"kind": "text", "name": "!!actor-sub", "text": lead_copy, "x": 17.6, "y": 10.2, "w": 14.2, "h": 6.2, "font": "sans", "size": 14.5, "color": muted, "line_spacing": 1.36})

    # ------------------------------------------------------------------
    # FAMILY 1: KINFOLK WARM EDITORIAL | FAMILY 9: BOTANICAL SAGE | FAMILY 15: GALLERY DIPTYCH
    # ------------------------------------------------------------------
    elif fid in ("kinfolk_warm_editorial", "botanical_sage_organic", "gallery_diptych_spread"):
        roman = ["I", "II", "III", "IV"][role % 4]
        layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-rule", "x": 1.8, "y": 1.55, "w": 30.27, "h": 0.04, "fill": rule})
        layers.append({"kind": "shape", "preset": "rect", "name": "#ed-bot-rule", "x": 1.8, "y": 17.6, "w": 30.27, "h": 0.04, "fill": rule})
        layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"ACT {roman}  —  {cat.upper()}  ·  {ind.upper()}", "x": 1.8, "y": 0.85, "w": 22.0, "h": 0.55, "font": "mono", "size": 10.0, "bold": True, "color": acc1})
        layers.append({"kind": "text", "name": "#ed-pg", "text": f"{target_slide_num:02d} / {total_slides:02d}", "x": 27.5, "y": 0.85, "w": 4.5, "h": 0.55, "font": "mono", "size": 10.0, "color": muted, "align": "r"})

        if fid == "gallery_diptych_spread" and asset_secondary is not None:
            layers.append({"kind": "text", "name": "!!actor-title", "text": title if role == 0 else beat_head, "x": 1.8, "y": 2.0, "w": 30.2, "h": 2.0, "font": "serif", "size": 30.0, "color": ink})
            _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 1.8, 4.3, 14.5, 10.2, border=rule, shadow=True)
            _add_plate_layer(layers, "!!actor-sub-art", asset_secondary, 17.5, 4.3, 14.5, 10.2, border=rule, shadow=True)
            layers.append({"kind": "text", "name": "!!actor-sub", "text": lead_copy, "x": 1.8, "y": 15.1, "w": 30.2, "h": 2.1, "font": "serif", "size": 13.5, "color": muted, "line_spacing": 1.3})
        elif role % 2 == 0:
            layers.append({"kind": "shape", "preset": "rect", "name": "#ed-mat", "x": 17.4, "y": 2.2, "w": 14.6, "h": 14.6, "fill": card, "line": rule, "shadow": True})
            _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 18.0, 2.8, 13.4, 13.4, rounded=(fid == "botanical_sage_organic"))
            layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(title if role == 0 else beat_head, 18, 3), "x": 1.8, "y": 2.5, "w": 14.4, "h": 6.4, "font": hfont, "size": 36.0 if role == 0 else 30.0, "color": ink, "line_spacing": 1.08})
            layers.append({"kind": "shape", "preset": "rect", "name": "#ed-short", "x": 1.8, "y": 9.3, "w": 4.0, "h": 0.12, "fill": acc2})
            layers.append({"kind": "text", "name": "!!actor-sub", "text": lead_copy, "x": 1.8, "y": 10.0, "w": 14.4, "h": 5.5, "font": sfont, "size": 15.0, "color": muted, "line_spacing": 1.42})
        else:
            layers.append({"kind": "shape", "preset": "rect", "name": "#ed-mat", "x": 1.8, "y": 2.2, "w": 15.6, "h": 14.6, "fill": card, "line": rule, "shadow": True})
            _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 2.4, 2.8, 14.4, 13.4)
            layers.append({"kind": "text", "name": "!!actor-title", "text": beat_head, "x": 18.8, "y": 2.6, "w": 13.2, "h": 4.2, "font": hfont, "size": 28.0, "color": ink, "line_spacing": 1.12})
            layers.append({"kind": "shape", "preset": "roundRect", "name": "#ed-quote-box", "x": 18.8, "y": 7.5, "w": 13.2, "h": 5.2, "fill": panel, "line": rule})
            layers.append({"kind": "text", "name": "!!actor-sub", "text": f"“{lead_copy}”", "x": 19.5, "y": 8.0, "w": 11.8, "h": 4.2, "font": "serif", "size": 14.5, "color": ink, "valign": "ctr", "line_spacing": 1.35})
            layers.append({"kind": "text", "name": "#ed-meta", "text": f"Curated {cat} monograph for {ind}. Open layout margins with calm tonal contrast.", "x": 18.8, "y": 13.5, "w": 13.2, "h": 3.0, "font": "sans", "size": 12.5, "color": muted})

    # ------------------------------------------------------------------
    # FAMILY 2: BAUHAUS CONSTRUCTIVIST | FAMILY 13: RISOGRAPH DUOTONE POSTER
    # ------------------------------------------------------------------
    elif fid in ("bauhaus_constructivist", "risograph_duotone_poster"):
        is_bau = fid == "bauhaus_constructivist"
        acc3 = fam.get("acc3", acc2)
        if is_bau:
            layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-pillar", "x": 0.0, "y": 0.0, "w": 2.2, "h": 19.05, "fill": acc1})
            layers.append({"kind": "shape", "preset": "ellipse", "name": "!!actor-orb", "x": 20.5 if role % 2 == 0 else 13.0, "y": 1.2, "w": 11.5, "h": 11.5, "fill": acc3 if role % 2 == 0 else acc2})
            layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-rule", "x": 2.2, "y": 14.1, "w": 31.67, "h": 0.35, "fill": ink})
            _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 17.6, 2.2, 13.8, 10.8, border=ink)
            layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"BAUHAUS // {cat.upper()} · {target_slide_num:02d}", "x": 3.2, "y": 1.5, "w": 13.5, "h": 0.7, "font": "mono", "size": 11.0, "bold": True, "color": acc2})
            layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(title if role == 0 else beat_head, 13, 3, upper=True), "x": 3.2, "y": 2.6, "w": 13.5, "h": 6.5, "font": "display", "size": 42.0 if role == 0 else 33.0, "bold": True, "color": ink, "line_spacing": 0.94})
            layers.append({"kind": "text", "name": "!!actor-sub", "text": lead_copy, "x": 3.2, "y": 9.4, "w": 13.2, "h": 4.0, "font": "sans", "size": 14.0, "color": muted, "line_spacing": 1.3})
            for j in range(3):
                bx = 3.2 + j * 9.8
                layers.append({"kind": "shape", "preset": "rect", "name": f"!!actor-chip-{j}", "x": bx, "y": 15.1, "w": 2.2, "h": 2.2, "fill": [acc1, acc2, ink][j]})
                layers.append({"kind": "text", "name": f"#bh-t-{j}", "text": [ind[:14].upper(), f"{total_slides} SLIDES", "MORPH READY"][j], "x": bx + 2.6, "y": 15.1, "w": 6.6, "h": 2.2, "font": "mono", "size": 11.5, "bold": True, "color": ink, "valign": "ctr"})
        else:
            # RISOGRAPH OVERPRINT
            layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-band", "x": 1.5, "y": 1.2, "w": 17.5, "h": 16.6, "fill": acc1 if role % 2 == 0 else acc2})
            layers.append({"kind": "shape", "preset": "rect", "name": "!!actor-panel", "x": 15.2, "y": 2.4, "w": 17.0, "h": 14.2, "fill": card, "line": ink})
            layers.append({"kind": "text", "name": "!!actor-ghost-num", "text": f"{target_slide_num:02d}", "x": 2.1, "y": 0.8, "w": 12.0, "h": 5.5, "font": "display", "size": 110.0, "bold": True, "color": on_acc1})
            layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(title if role == 0 else beat_head, 14, 3, upper=True), "x": 2.2, "y": 7.0, "w": 12.3, "h": 6.2, "font": "display", "size": 36.0 if role == 0 else 29.0, "bold": True, "color": on_acc1, "line_spacing": 0.96})
            layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"{cat.upper()} / {ind.upper()}", "x": 2.2, "y": 14.4, "w": 12.3, "h": 1.2, "font": "mono", "size": 11.0, "bold": True, "color": on_acc1})
            _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 16.2, 3.2, 15.0, 9.4, border=ink)
            layers.append({"kind": "text", "name": "!!actor-sub", "text": lead_copy, "x": 16.2, "y": 13.1, "w": 15.0, "h": 2.9, "font": "sans", "size": 13.5, "color": ink, "line_spacing": 1.32})

    # ------------------------------------------------------------------
    # FAMILY 3: PENTAGRAM 50/50 SPLIT POSTER
    # ------------------------------------------------------------------
    elif fid == "pentagram_split_poster":
        pigments = ["991B1B", "0F766E", "1E3A8A", "3730A3", "14532D"]
        pig = pigments[(fid_num + role) % len(pigments)]
        left_pig = role % 2 == 0
        if left_pig:
            layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-band", "x": 0.0, "y": 0.0, "w": 16.6, "h": 19.05, "fill": pig})
            layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"0{role+1}  /  {cat.upper()} · {ind.upper()}", "x": 1.6, "y": 1.6, "w": 13.4, "h": 0.7, "font": "mono", "size": 10.5, "bold": True, "color": "F8FAFC"})
            layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(title if role == 0 else beat_head, 13, 3), "x": 1.6, "y": 3.1, "w": 13.4, "h": 7.4, "font": "display", "size": 44.0 if role == 0 else 34.0, "bold": True, "color": "FFFFFF", "line_spacing": 0.96})
            layers.append({"kind": "text", "name": "!!actor-sub", "text": lead_copy, "x": 1.6, "y": 12.2, "w": 13.4, "h": 4.8, "font": "sans", "size": 14.5, "color": "E2E8F0", "line_spacing": 1.36})
            _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 18.0, 2.0, 14.2, 11.4, border=ink)
            layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-rule", "x": 18.0, "y": 14.2, "w": 14.2, "h": 0.06, "fill": ink})
            layers.append({"kind": "text", "name": "#pg-foot", "text": f"PLATE {target_slide_num:02d}/{total_slides:02d}  —  50/50 Asymmetric Split Architecture", "x": 18.0, "y": 14.7, "w": 14.2, "h": 2.4, "font": "mono", "size": 10.5, "color": muted})
        else:
            layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-band", "x": 17.27, "y": 0.0, "w": 16.6, "h": 19.05, "fill": pig})
            _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 1.6, 2.0, 14.2, 11.4, border=ink)
            layers.append({"kind": "text", "name": "#pg-cap", "text": f"FIG. {target_slide_num:02d} — {cat} Specimen", "x": 1.6, "y": 14.2, "w": 14.2, "h": 2.5, "font": "mono", "size": 10.5, "color": muted})
            layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"{ind.upper()}  ·  SLIDE {target_slide_num:02d}", "x": 18.9, "y": 1.6, "w": 13.4, "h": 0.7, "font": "mono", "size": 10.5, "bold": True, "color": "F8FAFC"})
            layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(beat_head, 13, 3), "x": 18.9, "y": 3.1, "w": 13.4, "h": 7.0, "font": "display", "size": 36.0, "bold": True, "color": "FFFFFF", "line_spacing": 0.98})
            layers.append({"kind": "text", "name": "!!actor-sub", "text": lead_copy, "x": 18.9, "y": 11.4, "w": 13.4, "h": 5.5, "font": "sans", "size": 14.5, "color": "E2E8F0", "line_spacing": 1.36})

    # ------------------------------------------------------------------
    # FAMILY 4: FT SALMON FINANCIAL MONOGRAPH
    # ------------------------------------------------------------------
    elif fid == "ft_salmon_financial":
        layers.append({"kind": "shape", "preset": "rect", "name": "#ft-top1", "x": 1.6, "y": 0.9, "w": 30.67, "h": 0.14, "fill": acc1})
        layers.append({"kind": "shape", "preset": "rect", "name": "#ft-top2", "x": 1.6, "y": 1.15, "w": 30.67, "h": 0.04, "fill": acc1})
        layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"FINANCIAL MONOGRAPH  //  {ind.upper()}  ·  BRIEFING {target_slide_num:02d}", "x": 1.6, "y": 1.35, "w": 24.0, "h": 0.6, "font": "mono", "size": 10.0, "bold": True, "color": acc1})
        layers.append({"kind": "text", "name": "#ft-pg", "text": f"NO. {target_slide_num:02d}/{total_slides:02d}", "x": 27.0, "y": 1.35, "w": 5.2, "h": 0.6, "font": "mono", "size": 10.0, "color": muted, "align": "r"})
        layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(title if role == 0 else beat_head, 28, 2), "x": 1.6, "y": 2.15, "w": 30.67, "h": 3.0, "font": "serif", "size": 31.0 if role == 0 else 26.0, "bold": True, "color": ink})
        layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-rule", "x": 1.6, "y": 5.3, "w": 30.67, "h": 0.05, "fill": rule})
        _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 1.6, 5.9, 16.5, 10.8, border=acc1)
        metrics = [
            ("DECK DEPTH", f"{total_slides} Slides", acc1),
            ("VERTICAL", ind[:16], acc2),
            ("KEYFRAME", f"Act {role+1:02d} / Morph", ink),
        ]
        for mi, (mk, mv, mc) in enumerate(metrics):
            my = 5.9 + mi * 2.35
            layers.append({"kind": "shape", "preset": "rect", "name": f"!!actor-card-{mi}", "x": 19.2, "y": my, "w": 13.0, "h": 2.0, "fill": card, "line": rule})
            layers.append({"kind": "text", "name": f"#ft-mk-{mi}", "text": mk, "x": 19.65, "y": my + 0.25, "w": 12.1, "h": 0.5, "font": "mono", "size": 9.5, "bold": True, "color": muted})
            layers.append({"kind": "text", "name": f"#ft-mv-{mi}", "text": mv, "x": 19.65, "y": my + 0.85, "w": 12.1, "h": 0.9, "font": "serif", "size": 17.5, "bold": True, "color": mc})
        layers.append({"kind": "text", "name": "!!actor-sub", "text": lead_copy, "x": 19.2, "y": 13.15, "w": 13.0, "h": 3.8, "font": "sans", "size": 13.0, "color": ink, "line_spacing": 1.32})

    # ------------------------------------------------------------------
    # FAMILY 5: LUXURY ATELIER NOIR (#141312 + Champagne Gold Inset Perimeter Frame)
    # ------------------------------------------------------------------
    elif fid == "luxury_atelier_noir":
        layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-frame", "x": 1.1, "y": 1.0, "w": 31.67, "h": 17.05, "fill": "none", "line": acc1})
        layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"MAISON ARCHIVE  ·  CHAPTER 0{role+1}  ·  {ind.upper()}", "x": 2.2, "y": 1.65, "w": 29.4, "h": 0.6, "font": "mono", "size": 10.0, "bold": True, "color": acc1, "align": "ctr"})
        layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(title if role == 0 else beat_head, 28, 2), "x": 2.4, "y": 2.45, "w": 29.0, "h": 2.8, "font": "serif", "size": 32.0, "color": ink, "align": "ctr"})
        _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 4.4, 5.6, 25.0, 9.6 if role % 2 == 0 else 8.8, border=acc1, shadow=True)
        layers.append({"kind": "text", "name": "!!actor-sub", "text": lead_copy[:130], "x": 4.4, "y": 15.6, "w": 25.0, "h": 1.9, "font": "serif", "size": 13.5, "color": muted, "align": "ctr"})

    # ------------------------------------------------------------------
    # FAMILY 6: BRUTALIST TABLOID PRESS | FAMILY 10: NEO-BRUTALIST POP
    # ------------------------------------------------------------------
    elif fid in ("brutalist_tabloid_press", "neo_brutalist_acid"):
        if fid == "neo_brutalist_acid":
            # Solid black offset shadows behind straight cards
            layers.append({"kind": "shape", "preset": "rect", "name": "#nb-sh1", "x": 1.88, "y": 1.68, "w": 16.0, "h": 11.4, "fill": ink})
            layers.append({"kind": "shape", "preset": "rect", "name": "!!actor-panel", "x": 1.6, "y": 1.4, "w": 16.0, "h": 11.4, "fill": card, "line": ink})
            layers.append({"kind": "shape", "preset": "rect", "name": "#nb-sh2", "x": 18.88, "y": 1.68, "w": 13.6, "h": 11.4, "fill": ink})
            layers.append({"kind": "shape", "preset": "rect", "name": "#nb-p2", "x": 18.6, "y": 1.4, "w": 13.6, "h": 11.4, "fill": acc2 if role % 2 == 0 else acc1, "line": ink})
            _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 19.2, 2.0, 12.4, 10.2, border=ink)
            layers.append({"kind": "shape", "preset": "rect", "name": "!!actor-badge", "x": 2.2, "y": 2.0, "w": 5.4, "h": 0.9, "fill": acc1, "line": ink})
            layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"NO.{target_slide_num:02d} // {cat.upper()}", "x": 2.2, "y": 2.0, "w": 5.4, "h": 0.9, "font": "mono", "size": 11.0, "bold": True, "color": on_acc1, "align": "ctr", "valign": "ctr"})
            layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(title if role == 0 else beat_head, 15, 3, upper=True), "x": 2.2, "y": 3.3, "w": 14.8, "h": 8.8, "font": "display", "size": 36.0 if role == 0 else 29.0, "bold": True, "color": ink, "line_spacing": 0.96})
            layers.append({"kind": "shape", "preset": "rect", "name": "#nb-sh3", "x": 1.88, "y": 13.88, "w": 30.6, "h": 3.8, "fill": ink})
            layers.append({"kind": "shape", "preset": "rect", "name": "#nb-p3", "x": 1.6, "y": 13.6, "w": 30.6, "h": 3.8, "fill": card, "line": ink})
            layers.append({"kind": "text", "name": "!!actor-sub", "text": f"{ind.upper()}  —  {lead_copy}", "x": 2.2, "y": 14.1, "w": 29.4, "h": 2.8, "font": "sans", "size": 14.5, "bold": True, "color": ink, "valign": "ctr"})
        else:
            # BRUTALIST BROADSHEET NEWSPRINT
            layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-frame", "x": 1.2, "y": 1.0, "w": 31.47, "h": 17.05, "fill": card, "line": ink})
            layers.append({"kind": "shape", "preset": "rect", "name": "#br-h1", "x": 1.2, "y": 2.35, "w": 31.47, "h": 0.14, "fill": ink})
            layers.append({"kind": "shape", "preset": "rect", "name": "#br-h2", "x": 1.2, "y": 6.4, "w": 31.47, "h": 0.14, "fill": ink})
            layers.append({"kind": "shape", "preset": "rect", "name": "#br-v1", "x": 16.9, "y": 6.4, "w": 0.14, "h": 11.65, "fill": ink})
            layers.append({"kind": "shape", "preset": "rect", "name": "!!actor-badge", "x": 1.2, "y": 1.0, "w": 5.5, "h": 1.35, "fill": ink})
            layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"EDITION {target_slide_num:02d}/{total_slides:02d}", "x": 1.2, "y": 1.0, "w": 5.5, "h": 1.35, "font": "mono", "size": 11.5, "bold": True, "color": card, "align": "ctr", "valign": "ctr"})
            layers.append({"kind": "text", "name": "#br-hdr", "text": f"THE {ind.upper()} BRIEF  //  CATEGORY: {cat.upper()}", "x": 7.2, "y": 1.0, "w": 24.8, "h": 1.35, "font": "mono", "size": 11.5, "bold": True, "color": acc1, "valign": "ctr"})
            layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(title if role == 0 else beat_head, 28, 2, upper=True), "x": 1.7, "y": 2.65, "w": 30.4, "h": 3.55, "font": "display", "size": 34.0, "bold": True, "color": ink, "valign": "ctr"})
            layers.append({"kind": "text", "name": "!!actor-sub", "text": f"SUMMARY NOTE // {lead_copy}\n\n[ ARCHIVAL SPECIFICATION ] Structured multi-layer narrative designed for zero-ambiguity editorial scanning.", "x": 1.8, "y": 7.1, "w": 14.3, "h": 10.2, "font": "sans", "size": 14.5, "color": ink, "line_spacing": 1.38})
            _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 17.6, 7.0, 14.4, 10.4, border=ink)

    # ------------------------------------------------------------------
    # FAMILY 7: APPLE BENTO MODULAR GRID
    # ------------------------------------------------------------------
    elif fid == "apple_bento_modular":
        # 4 crisp rounded Bento cards on cool silver-slate canvas
        layers.append({"kind": "shape", "preset": "roundRect", "name": "!!actor-card-0", "x": 1.4, "y": 1.3, "w": 17.8, "h": 10.4, "fill": card, "line": rule, "shadow": True})
        layers.append({"kind": "shape", "preset": "roundRect", "name": "!!actor-card-1", "x": 19.8, "y": 1.3, "w": 12.67, "h": 10.4, "fill": acc2, "shadow": True})
        layers.append({"kind": "shape", "preset": "roundRect", "name": "!!actor-card-2", "x": 1.4, "y": 12.25, "w": 10.6, "h": 5.5, "fill": acc1, "shadow": True})
        layers.append({"kind": "shape", "preset": "roundRect", "name": "!!actor-card-3", "x": 12.55, "y": 12.25, "w": 19.92, "h": 5.5, "fill": card, "line": rule, "shadow": True})
        layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"{cat.upper()} · {ind.upper()}", "x": 2.2, "y": 2.0, "w": 16.0, "h": 0.65, "font": "mono", "size": 11.0, "bold": True, "color": acc1})
        layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(title if role == 0 else beat_head, 18, 3), "x": 2.2, "y": 2.95, "w": 16.2, "h": 5.4, "font": "display", "size": 34.0 if role == 0 else 28.0, "bold": True, "color": ink, "line_spacing": 1.02})
        layers.append({"kind": "text", "name": "#bn-foot", "text": f"Modular Bento Stage · Slide {target_slide_num:02d} of {total_slides:02d}", "x": 2.2, "y": 9.8, "w": 16.0, "h": 1.2, "font": "mono", "size": 10.5, "color": muted})
        _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 20.35, 1.85, 11.55, 9.3, rounded=True)
        layers.append({"kind": "text", "name": "!!actor-ghost-num", "text": f"{total_slides}", "x": 2.0, "y": 12.5, "w": 9.4, "h": 3.4, "font": "display", "size": 58.0, "bold": True, "color": on_acc1})
        layers.append({"kind": "text", "name": "#bn-lbl", "text": "TOTAL SLIDES\nIN THIS SYSTEM", "x": 2.0, "y": 15.85, "w": 9.4, "h": 1.5, "font": "mono", "size": 10.0, "bold": True, "color": on_acc1})
        layers.append({"kind": "text", "name": "!!actor-sub", "text": lead_copy, "x": 13.3, "y": 12.85, "w": 18.4, "h": 4.3, "font": "sans", "size": 14.5, "color": ink, "valign": "ctr", "line_spacing": 1.35})

    # ------------------------------------------------------------------
    # FAMILY 8: ARCHITECTURAL CAD BLUEPRINT | FAMILY 12: QUANTUM DEEP FIELD
    # ------------------------------------------------------------------
    elif fid in ("architectural_blueprint", "cyber_pulse_quantum"):
        # Blueprint / Sci-tech CAD grid with glowing telemetry rules & schematic framing
        for gx in range(2, 33, 4):
            layers.append({"kind": "shape", "preset": "rect", "name": f"#bp-gx-{gx}", "x": float(gx), "y": 1.0, "w": 0.02, "h": 17.0, "fill": rule})
        for gy in range(2, 18, 3):
            layers.append({"kind": "shape", "preset": "rect", "name": f"#bp-gy-{gy}", "x": 1.4, "y": float(gy), "w": 31.1, "h": 0.02, "fill": rule})
        layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-frame", "x": 1.4, "y": 1.0, "w": 31.07, "h": 17.05, "fill": "none", "line": acc1})
        layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"[ SPEC // {target_slide_num:02d}-{total_slides:02d} ]  {cat.upper()}  ·  {ind.upper()}", "x": 2.1, "y": 1.45, "w": 22.0, "h": 0.6, "font": "mono", "size": 10.5, "bold": True, "color": acc1})
        layers.append({"kind": "text", "name": "#bp-dim", "text": "16:9 // 33.87 x 19.05 CM", "x": 24.5, "y": 1.45, "w": 7.3, "h": 0.6, "font": "mono", "size": 10.0, "color": acc2, "align": "r"})
        layers.append({"kind": "shape", "preset": "rect", "name": "!!actor-panel", "x": 17.5, "y": 2.4, "w": 14.3, "h": 14.4, "fill": panel, "line": acc1})
        _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 18.0, 2.9, 13.3, 10.6, border=acc2)
        layers.append({"kind": "text", "name": "#bp-fig", "text": f"PLATE {target_slide_num:02d} // {ind.upper()} ARCHIVE SPECIMEN", "x": 18.0, "y": 14.1, "w": 13.3, "h": 2.0, "font": "mono", "size": 10.0, "color": acc1})
        layers.append({"kind": "text", "name": "!!actor-title", "text": wrap_headline(title if role == 0 else beat_head, 15, 3), "x": 2.1, "y": 2.8, "w": 14.6, "h": 6.4, "font": "display", "size": 36.0 if role == 0 else 29.0, "bold": True, "color": ink, "line_spacing": 1.0})
        layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-rule", "x": 2.1, "y": 9.6, "w": 14.4, "h": 0.08, "fill": acc2})
        layers.append({"kind": "text", "name": "!!actor-sub", "text": lead_copy, "x": 2.1, "y": 10.2, "w": 14.4, "h": 6.4, "font": bfont, "size": 13.5, "color": muted, "line_spacing": 1.38})

    # ------------------------------------------------------------------
    # FAMILY 11: KYOTO MA-ZEN (Rice-paper, generous open space, right vertical index & red Hanko chop)
    # ------------------------------------------------------------------
    else:
        layers.append({"kind": "shape", "preset": "rect", "name": "!!actor-badge", "x": 29.5, "y": 1.6, "w": 1.9, "h": 1.9, "fill": acc1})
        layers.append({"kind": "text", "name": "!!actor-kicker", "text": f"{target_slide_num:02d}", "x": 29.5, "y": 1.6, "w": 1.9, "h": 1.9, "font": "mono", "size": 18.0, "bold": True, "color": on_acc1, "align": "ctr", "valign": "ctr"})
        layers.append({"kind": "text", "name": "!!actor-vtxt", "vertical270": True, "text": f"{cat.upper()}  //  {ind.upper()}  ·  {total_slides:02d} SLIDES", "x": 29.9, "y": 4.2, "w": 1.1, "h": 13.0, "font": "mono", "size": 10.0, "bold": True, "color": muted, "align": "ctr", "valign": "ctr"})
        layers.append({"kind": "text", "name": "!!actor-title", "text": title if role == 0 else beat_head, "x": 2.2, "y": 1.65, "w": 25.4, "h": 3.2, "font": "serif", "size": 29.0, "color": ink, "line_spacing": 1.15})
        layers.append({"kind": "shape", "preset": "rect", "name": "!!scene-rule", "x": 2.2, "y": 5.05, "w": 7.5, "h": 0.08, "fill": acc1})
        _add_plate_layer(layers, "!!actor-cover-art", asset_primary, 2.2, 5.75, 16.5, 11.1, border=rule, shadow=True)
        layers.append({"kind": "text", "name": "!!actor-sub", "text": f"{lead_copy}\n\n— Restraint creates focal authority. Open margins let visual evidence breathe.", "x": 20.0, "y": 5.8, "w": 8.6, "h": 10.6, "font": "serif", "size": 14.5, "color": muted, "line_spacing": 1.48})

    return {"bg": bg, "accent": acc1, "family_id": fid, "family_label": fam["label"], "layers": layers}


def build_keyframe_ooxml(
    spec: dict[str, Any],
    cx_emu: int,
    cy_emu: int,
    pic_rids: dict[str, str],
) -> bytes:
    """Compile a declarative keyframe spec into strictly ordered PowerPoint OOXML."""
    sx = cx_emu / CANVAS_W_CM
    sy = cy_emu / CANVAS_H_CM
    smin = min(sx, sy)
    parts: list[str] = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<p:sld xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}" '
        f'xmlns:p14="{NS_P14}" xmlns:p159="{NS_P159}" xmlns:mc="{NS_MC}" mc:Ignorable="p14 p159">',
        f'<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{spec["bg"]}"/></a:solidFill>'
        f'<a:effectLst/></p:bgPr></p:bg><p:spTree>'
        f'<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        f'<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
        f'<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>',
    ]

    next_id = 100
    anim_ids: list[str] = []

    for lyr in spec["layers"]:
        next_id += 1
        sid = str(next_id)
        x = int(round(lyr["x"] * sx))
        y = int(round(lyr["y"] * sy))
        w = max(1, int(round(lyr["w"] * sx)))
        h = max(1, int(round(lyr["h"] * sy)))
        rot_deg = lyr.get("rot", 0)
        rot_attr = f' rot="{int(round(rot_deg * 60000))}"' if rot_deg else ""
        nm = escape(lyr["name"])
        if nm.startswith("!!actor-") and len(anim_ids) < 5:
            anim_ids.append(sid)

        if lyr["kind"] == "pic":
            rid = pic_rids[lyr["name"]]
            shdw_xml = (
                '<a:effectLst><a:outerShdw blurRad="152400" dist="50800" dir="2700000" algn="tl" rotWithShape="0">'
                '<a:srgbClr val="000000"><a:alpha val="32000"/></a:srgbClr></a:outerShdw></a:effectLst>'
                if lyr.get("shadow") else ""
            )
            ln_xml = (
                f'<a:ln w="12700"><a:solidFill><a:srgbClr val="{lyr["border"]}"/></a:solidFill></a:ln>'
                if lyr.get("border") else ""
            )
            prst = "roundRect" if lyr.get("rounded") else "rect"
            av_lst = '<a:gd name="adj" fmla="val 6500"/>' if prst == "roundRect" else ""
            parts.append(
                f'<p:pic><p:nvPicPr><p:cNvPr id="{sid}" name="{nm}"/><p:cNvPicPr>'
                f'<a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
                f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
                f'<p:spPr><a:xfrm{rot_attr}><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
                f'<a:prstGeom prst="{prst}"><a:avLst>{av_lst}</a:avLst></a:prstGeom>{ln_xml}{shdw_xml}</p:spPr></p:pic>'
            )
        elif lyr["kind"] == "shape":
            preset = lyr.get("preset", "rect")
            av = '<a:gd name="adj" fmla="val 4500"/>' if preset == "roundRect" else ""
            fill_xml = (
                f'<a:solidFill><a:srgbClr val="{lyr["fill"]}"/></a:solidFill>'
                if lyr.get("fill") and lyr["fill"] != "none" else "<a:noFill/>"
            )
            ln_xml = (
                f'<a:ln w="15240"><a:solidFill><a:srgbClr val="{lyr["line"]}"/></a:solidFill></a:ln>'
                if lyr.get("line") else "<a:ln><a:noFill/></a:ln>"
            )
            shdw_xml = (
                '<a:effectLst><a:outerShdw blurRad="127000" dist="50800" dir="2700000" algn="tl" rotWithShape="0">'
                '<a:srgbClr val="000000"><a:alpha val="22000"/></a:srgbClr></a:outerShdw></a:effectLst>'
                if lyr.get("shadow") else ""
            )
            parts.append(
                f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{nm}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
                f'<p:spPr><a:xfrm{rot_attr}><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
                f'<a:prstGeom prst="{preset}"><a:avLst>{av}</a:avLst></a:prstGeom>'
                f'{fill_xml}{ln_xml}{shdw_xml}</p:spPr>'
                f'<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>'
            )
        else:
            font_map = {"display": "Bahnschrift", "serif": "Georgia", "mono": "Consolas", "sans": "Segoe UI"}
            typeface = font_map.get(lyr.get("font", "sans"), "Segoe UI")
            sz_100 = int(round(lyr.get("size", 14) * 100 * (smin / 360000.0)))
            bold_attr = ' b="1"' if lyr.get("bold") else ""
            algn = lyr.get("align", "l")
            valgn = lyr.get("valign", "t")
            vert_attr = ' vert="vert270"' if lyr.get("vertical270") else ""
            ls = lyr.get("line_spacing", 1.15)
            lnspc_xml = f'<a:lnSpc><a:spcPct val="{int(round(ls * 100000))}"/></a:lnSpc>'

            paras = []
            for para_txt in str(lyr["text"]).splitlines() or [""]:
                paras.append(
                    f'<a:p><a:pPr algn="{algn}">{lnspc_xml}</a:pPr>'
                    f'<a:r><a:rPr lang="en-US" sz="{sz_100}"{bold_attr}>'
                    f'<a:solidFill><a:srgbClr val="{lyr["color"]}"/></a:solidFill>'
                    f'<a:latin typeface="{typeface}"/></a:rPr>'
                    f'<a:t>{escape(para_txt)}</a:t></a:r></a:p>'
                )
            parts.append(
                f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{nm}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
                f'<p:spPr><a:xfrm{rot_attr}><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
                f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>'
                f'<p:txBody><a:bodyPr wrap="square"{vert_attr} lIns="0" rIns="0" tIns="0" bIns="0" anchor="{valgn}"/>'
                f'<a:lstStyle/>{"".join(paras)}</p:txBody></p:sp>'
            )

    parts.append("</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>")
    parts.append(MORPH_TRANSITION_XML)

    if anim_ids:
        tparts = [
            f'<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
            f'<p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        ]
        nid = 3
        for idx, spid in enumerate(anim_ids):
            delay = idx * 140
            tparts.append(
                f'<p:par><p:cTn id="{nid}" fill="hold"><p:stCondLst><p:cond delay="{delay}"/></p:stCondLst>'
                f'<p:childTnLst><p:par><p:cTn id="{nid+1}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
                f'<p:childTnLst><p:par><p:cTn id="{nid+2}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold" nodeType="withEffect">'
                f'<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                f'<p:set><p:cBhvr><p:cTn id="{nid+3}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
                f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>'
                f'</p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>'
                f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{nid+4}" dur="420"/>'
                f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:animEffect>'
                f'</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>'
            )
            nid += 5
        tparts.append(
            '</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0">'
            '<p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
            '<p:nextCondLst><p:cond evt="onNext" delay="0">'
            '<p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>'
            '</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>'
        )
        parts.append("".join(tparts))

    parts.append("</p:sld>")
    out = "".join(parts).encode("utf-8")
    ET.fromstring(out)
    return out


def _paste_with_shadow(base: Image.Image, overlay: Image.Image, x0: int, y0: int, shadow: bool) -> None:
    if shadow:
        sh = Image.new("RGBA", (overlay.width + 44, overlay.height + 44), (0, 0, 0, 0))
        alpha = overlay.split()[3]
        sh_fill = Image.new("RGBA", overlay.size, (0, 0, 0, 75))
        sh.paste(sh_fill, (22, 22), alpha)
        sh = sh.filter(ImageFilter.GaussianBlur(12))
        base.paste(sh, (x0 - 16, y0 - 10), sh)
    base.paste(overlay, (x0, y0), overlay)


def _open_asset_bytes(asset: dict[str, Any]) -> Image.Image:
    if "raw_bytes" in asset:
        return Image.open(io.BytesIO(asset["raw_bytes"])).convert("RGBA")
    return Image.open(asset["path"]).convert("RGBA")


def render_keyframe_png(spec: dict[str, Any], out_png: Path) -> None:
    """Render 2x-supersampled (1920x1080 -> 960x540) 1:1 preview matching OOXML keyframe."""
    W, H = 1920, 1080
    px_per_cm = W / CANVAS_W_CM
    base = Image.new("RGBA", (W, H), hex_rgba(spec["bg"]))

    for lyr in spec["layers"]:
        x = int(round(lyr["x"] * px_per_cm))
        y = int(round(lyr["y"] * px_per_cm))
        w = max(2, int(round(lyr["w"] * px_per_cm)))
        h = max(2, int(round(lyr["h"] * px_per_cm)))

        if lyr["kind"] == "pic":
            try:
                pic = _open_asset_bytes(lyr["asset"]).resize((w, h), Image.Resampling.LANCZOS)
                if lyr.get("rounded"):
                    mask = Image.new("L", (w, h), 0)
                    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=24, fill=255)
                    pic.putalpha(mask)
                if lyr.get("border"):
                    dr = ImageDraw.Draw(pic)
                    if lyr.get("rounded"):
                        dr.rounded_rectangle([0, 0, w - 1, h - 1], radius=24, outline=hex_rgba(lyr["border"]), width=4)
                    else:
                        dr.rectangle([0, 0, w - 1, h - 1], outline=hex_rgba(lyr["border"]), width=4)
                _paste_with_shadow(base, pic, x, y, bool(lyr.get("shadow")))
            except Exception:
                pass
        elif lyr["kind"] == "shape":
            sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            dr = ImageDraw.Draw(sh, "RGBA")
            preset = lyr.get("preset", "rect")
            fill_c = hex_rgba(lyr["fill"]) if lyr.get("fill") and lyr["fill"] != "none" else None
            line_c = hex_rgba(lyr["line"]) if lyr.get("line") else None
            bw = 4 if lyr.get("line") else 0
            if preset == "roundRect":
                dr.rounded_rectangle([0, 0, w - 1, h - 1], radius=24, fill=fill_c, outline=line_c, width=bw)
            elif preset == "ellipse":
                dr.ellipse([0, 0, w - 1, h - 1], fill=fill_c, outline=line_c, width=bw)
            else:
                dr.rectangle([0, 0, w - 1, h - 1], fill=fill_c, outline=line_c, width=bw)
            _paste_with_shadow(base, sh, x, y, bool(lyr.get("shadow")))
        else:
            if lyr.get("vertical270"):
                txt_im = Image.new("RGBA", (h, w), (0, 0, 0, 0))
                dr = ImageDraw.Draw(txt_im, "RGBA")
                font = load_ttf("mono", int(round(lyr["size"] * (px_per_cm / 28.3465) * 1.1)))
                tb = dr.textbbox((0, 0), str(lyr["text"]), font=font)
                tw, th = tb[2] - tb[0], tb[3] - tb[1]
                dr.text(((h - tw) / 2, (w - th) / 2 - 2), str(lyr["text"]), font=font, fill=hex_rgba(lyr["color"]))
                rot_txt = txt_im.rotate(90, resample=Image.Resampling.BICUBIC, expand=True)
                base.paste(rot_txt, (x, y), rot_txt)
            else:
                txt_im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                dr = ImageDraw.Draw(txt_im, "RGBA")
                f_role = "sans_bold" if lyr.get("font") == "sans" and lyr.get("bold") else lyr.get("font", "sans")
                px_sz = int(round(lyr.get("size", 14) * (px_per_cm / 28.3465) * 1.12))
                txt_val = str(lyr["text"])
                font = load_ttf(f_role, px_sz, txt_val)
                ls = lyr.get("line_spacing", 1.15)
                algn = lyr.get("align", "l")
                valgn = lyr.get("valign", "t")
                col = hex_rgba(lyr["color"])

                wrapped_lines: list[str] = []
                for pline in txt_val.splitlines() or [""]:
                    words = pline.split(" ")
                    cur = ""
                    for word in words:
                        test = f"{cur} {word}".strip()
                        if dr.textlength(test, font=font) <= w - 8 or not cur:
                            cur = test
                        else:
                            wrapped_lines.append(cur)
                            cur = word
                    if cur or not wrapped_lines:
                        wrapped_lines.append(cur)

                line_h = int(px_sz * ls)
                total_h = len(wrapped_lines) * line_h
                y_start = 0 if valgn == "t" else (max(0, (h - total_h) // 2) if valgn == "ctr" else max(0, h - total_h))
                for li, ln_txt in enumerate(wrapped_lines):
                    ly = y_start + li * line_h
                    if ly > h - 4:
                        break
                    tw = dr.textlength(ln_txt, font=font)
                    lx = 0 if algn == "l" else (max(0, (w - tw) / 2) if algn == "ctr" else max(0, w - tw))
                    dr.text((lx, ly), ln_txt, font=font, fill=col)
                base.paste(txt_im, (x, y), txt_im)

    final_img = base.convert("RGB").resize((960, 540), Image.Resampling.LANCZOS)
    q = final_img.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
    buf = io.BytesIO()
    q.save(buf, format="PNG", optimize=True)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    out_png.write_bytes(buf.getvalue())


def render_ooxml_slide_png(
    zin: zipfile.ZipFile,
    slide_part: str,
    cx_emu: int,
    cy_emu: int,
    accent: str,
    bg_default: str = "F8F7F4",
) -> bytes:
    """Fast pure-Pillow OOXML slide rasterizer (960x540) fallback when a COM PNG is absent."""
    W, H = 960, 540
    names_set = set(zin.namelist())
    raw_xml = zin.read(slide_part)
    root = ET.fromstring(raw_xml)

    rels_part = f"ppt/slides/_rels/{Path(slide_part).name}.rels"
    rel_map: dict[str, str] = {}
    if rels_part in names_set:
        try:
            rroot = ET.fromstring(zin.read(rels_part))
            for rel in rroot:
                rid = rel.attrib.get("Id", "")
                tgt = rel.attrib.get("Target", "")
                if rid and tgt:
                    norm_t = tgt.lstrip("/")
                    if norm_t.startswith("../"):
                        norm_t = "ppt/" + norm_t[3:]
                    elif not norm_t.startswith("ppt/"):
                        norm_t = "ppt/slides/" + norm_t
                    rel_map[rid] = norm_t
        except Exception:
            pass

    bg_hex = bg_default
    bg_el = root.find(f".//{{{NS_P}}}bg//{{{NS_A}}}srgbClr")
    if bg_el is not None and bg_el.attrib.get("val"):
        bg_hex = bg_el.attrib["val"]
    img = Image.new("RGBA", (W, H), hex_rgba(bg_hex))
    draw = ImageDraw.Draw(img, "RGBA")

    sx = W / max(1, cx_emu)
    sy = H / max(1, cy_emu)
    smin = min(sx, sy)

    bg_rgb = hex_rgba(bg_hex)[:3]
    is_dark_bg = (0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2]) < 120
    default_txt_hex = "F4F0E6" if is_dark_bg else "14171F"

    sp_tree = root.find(f".//{{{NS_P}}}spTree")
    if sp_tree is not None:
        for child in list(sp_tree):
            tag = child.tag.split("}")[-1]
            xfrm = child.find(f".//{{{NS_A}}}xfrm")
            if xfrm is None:
                continue
            off = xfrm.find(f"{{{NS_A}}}off")
            ext = xfrm.find(f"{{{NS_A}}}ext")
            if off is None or ext is None:
                continue
            x0 = int(round(int(off.attrib.get("x", 0)) * sx))
            y0 = int(round(int(off.attrib.get("y", 0)) * sy))
            bw = max(4, int(round(int(ext.attrib.get("cx", 0)) * sx)))
            bh = max(4, int(round(int(ext.attrib.get("cy", 0)) * sy)))

            if tag == "pic":
                blip = child.find(f".//{{{NS_A}}}blip")
                if blip is not None:
                    emb = blip.attrib.get(f"{{{NS_R}}}embed") or ""
                    media_part = rel_map.get(emb, "")
                    if media_part in names_set:
                        try:
                            with Image.open(io.BytesIO(zin.read(media_part))) as pim:
                                p_rgba = pim.convert("RGBA").resize((bw, bh), Image.Resampling.LANCZOS)
                            img.paste(p_rgba, (x0, y0), p_rgba)
                        except Exception:
                            pass
            elif tag == "sp":
                spPr = child.find(f"{{{NS_P}}}spPr")
                if spPr is not None and spPr.find(f"{{{NS_A}}}noFill") is None:
                    srgb = spPr.find(f".//{{{NS_A}}}solidFill/{{{NS_A}}}srgbClr")
                    if srgb is not None and srgb.attrib.get("val"):
                        av_el = srgb.find(f"{{{NS_A}}}alpha")
                        av = int(av_el.attrib.get("val", 100000)) if av_el is not None else 100000
                        draw.rectangle([x0, y0, x0 + bw, y0 + bh], fill=hex_rgba(srgb.attrib["val"], av))

                txBody = child.find(f"{{{NS_P}}}txBody")
                if txBody is not None:
                    cur_y = y0 + 4
                    for p_el in txBody.findall(f"{{{NS_A}}}p"):
                        runs = []
                        first_sz = 1600
                        first_clr = default_txt_hex
                        first_bold = False
                        for r_el in p_el.findall(f"{{{NS_A}}}r"):
                            t_el = r_el.find(f"{{{NS_A}}}t")
                            if t_el is not None and t_el.text:
                                runs.append(t_el.text)
                                rPr = r_el.find(f"{{{NS_A}}}rPr")
                                if rPr is not None and len(runs) == 1:
                                    if rPr.attrib.get("sz"):
                                        try:
                                            first_sz = int(rPr.attrib["sz"])
                                        except ValueError:
                                            pass
                                    first_bold = rPr.attrib.get("b") == "1"
                                    c_el = rPr.find(f".//{{{NS_A}}}srgbClr")
                                    if c_el is not None and c_el.attrib.get("val"):
                                        first_clr = c_el.attrib["val"]
                        ptxt = "".join(runs).strip()
                        if not ptxt or "AVANT //" in ptxt or "MORPH" in ptxt:
                            continue
                        px_sz = max(10, min(52, int(round((first_sz / 100.0) * (smin * 360000.0 / 28.3465) * 1.1))))
                        font = load_ttf("sans_bold" if first_bold else "sans", px_sz)
                        cur = ""
                        for word in ptxt.split():
                            test = f"{cur} {word}".strip()
                            if draw.textlength(test, font=font) <= max(40, bw - 8) or not cur:
                                cur = test
                            else:
                                if cur_y < y0 + bh - 4:
                                    draw.text((x0 + 4, cur_y), cur, font=font, fill=hex_rgba(first_clr))
                                    cur_y += int(px_sz * 1.18)
                                cur = word
                        if cur and cur_y < y0 + bh - 4:
                            draw.text((x0 + 4, cur_y), cur, font=font, fill=hex_rgba(first_clr))
                            cur_y += int(px_sz * 1.25)

    draw.rectangle([0, 0, W, 3], fill=hex_rgba(accent))
    q = img.convert("RGB").quantize(colors=256, method=Image.Quantize.FASTOCTREE)
    buf = io.BytesIO()
    q.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def attach_morph_transition(slide_bytes: bytes) -> bytes:
    txt = slide_bytes.decode("utf-8", "ignore")
    if "<p159:morph" in txt:
        return slide_bytes
    m_root = re.match(r"^(<\?xml[^>]*\?>\s*)?<p:sld\b([^>]*)>", txt)
    if m_root:
        attrs = m_root.group(2)
        adds = []
        if "xmlns:p159=" not in attrs:
            adds.append(f'xmlns:p159="{NS_P159}"')
        if "xmlns:p14=" not in attrs:
            adds.append(f'xmlns:p14="{NS_P14}"')
        if "xmlns:mc=" not in attrs:
            adds.append(f'xmlns:mc="{NS_MC}"')
        if adds:
            new_open = (m_root.group(1) or "") + f'<p:sld{attrs} {" ".join(adds)}>'
            txt = new_open + txt[m_root.end():]

    if re.search(r"<p:transition\b", txt):
        txt = re.sub(r"<p:transition\b[^>]*>.*?</p:transition>|<p:transition\b[^>]*/\s*>", MORPH_TRANSITION_XML, txt, count=1, flags=re.S)
    else:
        for anchor in ("<p:timing", "<p:extLst", "</p:sld>"):
            idx = txt.rfind(anchor)
            if idx != -1:
                txt = txt[:idx] + MORPH_TRANSITION_XML + txt[idx:]
                break
    out = txt.encode("utf-8")
    ET.fromstring(out)
    return out


def expand_single_pptx(
    src_path: Path,
    dst_path: Path,
    slug: str,
    deck_idx: int,
    assets: list[dict[str, Any]],
    meta_info: dict[str, Any],
    sync_previews: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    with zipfile.ZipFile(src_path, "r") as zin:
        names = zin.namelist()
        if any(n.startswith("ppt/slides/av_slide_") for n in names) and not force:
            return {"slug": slug, "status": "already-expanded"}

        pres_xml = zin.read("ppt/presentation.xml").decode("utf-8", "ignore")
        pres_rels = zin.read("ppt/_rels/presentation.xml.rels").decode("utf-8", "ignore")
        ct_xml = zin.read("[Content_Types].xml").decode("utf-8", "ignore")

        ctx = extract_deck_context(
            zin,
            meta_info.get("title") or src_path.stem,
            meta_info.get("category") or "Strategy",
            meta_info.get("industry") or "Enterprise",
        )
        fam = pick_design_family(slug, ctx["category"], ctx["industry"], deck_idx)
        native_media = extract_native_deck_media(zin, fam["card"])

        sld_ids_raw = re.findall(r"<p:sldId\b[^>]*/?\s*>", pres_xml)
        sld_ids = []
        for tag in sld_ids_raw:
            mid = re.search(r'\bid="(\d+)"', tag)
            mrid = re.search(r'\br:id="([^"]+)"', tag)
            if mid and mrid:
                sld_ids.append((mid.group(1), mrid.group(1)))

        rel_root = ET.fromstring(pres_rels.encode("utf-8"))
        rid_to_target = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rel_root if rel.attrib.get("Id")}

        # Recover true original slide PNGs BEFORE stripping old av_slide_* slots!
        orig_png_map: dict[int, bytes] = {}
        preview_dir = PREVIEWS_DIR / slug
        orig_counter = 0
        orig_sld_ids: list[tuple[str, str]] = []
        for old_pos_1b, (sid, rid) in enumerate(sld_ids, start=1):
            t_str = rid_to_target.get(rid, "")
            if "av_slide_" not in t_str:
                orig_counter += 1
                orig_sld_ids.append((sid, rid))
                if sync_previews and preview_dir.exists():
                    pf = preview_dir / f"slide_{old_pos_1b:02d}.png"
                    if pf.exists() and pf.stat().st_size > 1500:
                        orig_png_map[orig_counter] = pf.read_bytes()

        k = len(orig_sld_ids)
        if k == 0:
            return {"slug": slug, "status": "empty-skip", "family": fam["label"]}

        sample_slide_target = rid_to_target.get(orig_sld_ids[0][1], "slides/slide1.xml")
        uses_abs_ppt = sample_slide_target.startswith("/ppt/")

        layouts = sorted([n for n in names if re.match(r"^ppt/slideLayouts/slideLayout\d+\.xml$", n)])
        layout_part = layouts[-1] if layouts else "ppt/slideLayouts/slideLayout1.xml"
        s1_target_rel = sample_slide_target.lstrip("/")
        if not s1_target_rel.startswith("ppt/"):
            s1_target_rel = "ppt/" + s1_target_rel
        s1_rels_path = f"ppt/slides/_rels/{Path(s1_target_rel).name}.rels"
        layout_target_rel = "../slideLayouts/" + Path(layout_part).name
        if s1_rels_path in names:
            s1_r_xml = zin.read(s1_rels_path).decode("utf-8", "ignore")
            m_lay = re.search(r'Type="[^"]*slideLayout"[^>]*Target="([^"]+)"', s1_r_xml) or re.search(r'Target="([^"]*slideLayout[^"]*)"', s1_r_xml)
            if m_lay:
                layout_target_rel = m_lay.group(1)

        total_assets = len(assets)
        needed_av = max(4, 15 - k) if k < 15 else 4
        final_total = k + needed_av

        av_slots: list[int] = []
        if not ctx["slide1_has_pic"] or k < 12:
            av_slots.append(0)
        rem_slots_needed = needed_av - len(av_slots)
        if rem_slots_needed > 0:
            span = final_total - 1
            for i in range(1, rem_slots_needed + 1):
                pos = min(final_total - 1, max(1, int(round(i * span / (rem_slots_needed + 1)))))
                while pos in av_slots and pos + 1 < final_total:
                    pos += 1
                while pos in av_slots and pos - 1 >= 0:
                    pos -= 1
                av_slots.append(pos)
        av_slots = sorted(av_slots[:needed_av])

        timeline: list[tuple[str, Any]] = []
        orig_cursor = 0
        av_cursor = 0
        for pos in range(final_total):
            if pos in av_slots and av_cursor < needed_av:
                role = 0 if pos == 0 else [1, 2, 3, 1, 2, 3, 0, 1, 2, 3][(av_cursor - 1) % 10]
                timeline.append(("av", (av_cursor, role, pos + 1)))
                av_cursor += 1
            elif orig_cursor < k:
                timeline.append(("orig", (orig_cursor + 1, orig_sld_ids[orig_cursor])))
                orig_cursor += 1
        while orig_cursor < k:
            timeline.append(("orig", (orig_cursor + 1, orig_sld_ids[orig_cursor])))
            orig_cursor += 1

        max_sld_num = max([int(s[0]) for s in sld_ids] + [255])
        existing_rids = set(rid_to_target.keys())

        new_slides_bytes: dict[str, bytes] = {}
        new_slide_rels_bytes: dict[str, bytes] = {}
        new_media_bytes: dict[str, bytes] = {}
        new_pres_rels_xml: list[str] = []
        new_ct_overrides: list[str] = []
        final_sld_id_xml: list[str] = []
        av_specs_for_png: list[tuple[int, dict[str, Any]]] = []

        asset_base = (deck_idx * 17) % total_assets
        used_orig_paths_to_morph: set[str] = set()
        orig_slide_parts_by_idx: dict[int, str] = {}

        for final_pos, (kind, payload) in enumerate(timeline, start=1):
            if kind == "orig":
                orig_idx_1b, (sid, rid) = payload
                final_sld_id_xml.append(f'<p:sldId id="{sid}" r:id="{rid}"/>')
                t = rid_to_target.get(rid, "").lstrip("/")
                if t and not t.startswith("ppt/"):
                    t = "ppt/" + t
                if t:
                    used_orig_paths_to_morph.add(t)
                    orig_slide_parts_by_idx[orig_idx_1b] = t
            else:
                av_idx, role, slide_num = payload
                # Prioritize deck's own native media before visual_asset_bank
                if av_idx < len(native_media):
                    a1 = native_media[av_idx]
                else:
                    a1 = assets[(asset_base + av_idx * 19) % total_assets]
                a2 = (
                    assets[(asset_base + av_idx * 19 + 7) % total_assets]
                    if fam["id"] == "gallery_diptych_spread"
                    else None
                )
                spec = make_keyframe_spec(fam, role, av_idx, slide_num, len(timeline), ctx, a1, a2)

                media_1 = f"av_art_{av_idx+1:02d}a.jpg"
                a1_bytes = a1["raw_bytes"] if "raw_bytes" in a1 else Path(a1["path"]).read_bytes()
                new_media_bytes[f"ppt/media/{media_1}"] = a1_bytes
                pic_rids = {"!!actor-cover-art": "rId2"}
                rels_extra = [f'<Relationship Id="rId2" Type="{NS_R}/image" Target="../media/{media_1}"/>']

                if a2 is not None:
                    media_2 = f"av_art_{av_idx+1:02d}b.jpg"
                    a2_bytes = a2["raw_bytes"] if "raw_bytes" in a2 else Path(a2["path"]).read_bytes()
                    new_media_bytes[f"ppt/media/{media_2}"] = a2_bytes
                    pic_rids["!!actor-sub-art"] = "rId3"
                    rels_extra.append(f'<Relationship Id="rId3" Type="{NS_R}/image" Target="../media/{media_2}"/>')

                slide_fname = f"av_slide_{av_idx+1:02d}.xml"
                slide_part = f"ppt/slides/{slide_fname}"
                rels_part = f"ppt/slides/_rels/{slide_fname}.rels"
                new_slides_bytes[slide_part] = build_keyframe_ooxml(spec, ctx["cx_emu"], ctx["cy_emu"], pic_rids)
                new_slide_rels_bytes[rels_part] = (
                    '<?xml version="1.0" encoding="utf-8"?>'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    f'<Relationship Id="rId1" Type="{NS_R}/slideLayout" Target="{layout_target_rel}"/>'
                    + "".join(rels_extra)
                    + "</Relationships>"
                ).encode("utf-8")

                max_sld_num += 1
                new_rid = f"rIdAv{av_idx+1:02d}"
                while new_rid in existing_rids:
                    new_rid += "x"
                existing_rids.add(new_rid)
                target_val = f"/ppt/slides/{slide_fname}" if uses_abs_ppt else f"slides/{slide_fname}"
                new_pres_rels_xml.append(f'<Relationship Id="{new_rid}" Type="{NS_R}/slide" Target="{target_val}"/>')
                new_ct_overrides.append(
                    f'<Override PartName="/ppt/slides/{slide_fname}" '
                    f'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
                )
                final_sld_id_xml.append(f'<p:sldId id="{max_sld_num}" r:id="{new_rid}"/>')
                av_specs_for_png.append((final_pos, spec))

        new_pres_xml = re.sub(
            r"<p:sldIdLst\b[^>]*>.*?</p:sldIdLst>",
            f'<p:sldIdLst xmlns:r="{NS_R}">{"".join(final_sld_id_xml)}</p:sldIdLst>',
            pres_xml,
            count=1,
            flags=re.S,
        )
        ET.fromstring(new_pres_xml.encode("utf-8"))

        if sync_previews:
            for final_pos, (kind, payload) in enumerate(timeline, start=1):
                if final_pos > 16 or kind != "orig":
                    continue
                orig_idx = payload[0]
                if orig_idx not in orig_png_map:
                    sp = orig_slide_parts_by_idx.get(orig_idx, "")
                    if sp and sp in names:
                        try:
                            orig_png_map[orig_idx] = render_ooxml_slide_png(
                                zin, sp, ctx["cx_emu"], ctx["cy_emu"], fam["acc1"], bg_default=fam["bg"]
                            )
                        except Exception:
                            pass

        cleaned_pres_rels = re.sub(r'<Relationship\b[^>]*Target="[^"]*av_slide_[^"]*"[^>]*/>\s*', "", pres_rels)
        cleaned_pres_rels = cleaned_pres_rels.replace("</Relationships>", f"{''.join(new_pres_rels_xml)}</Relationships>")
        ET.fromstring(cleaned_pres_rels.encode("utf-8"))

        cleaned_ct = re.sub(r'<Override\b[^>]*PartName="/ppt/slides/av_slide_[^"]*"[^>]*/>\s*', "", ct_xml)
        if 'Extension="jpg"' not in cleaned_ct:
            cleaned_ct = cleaned_ct.replace("</Types>", '<Default Extension="jpg" ContentType="image/jpeg"/></Types>')
        cleaned_ct = cleaned_ct.replace("</Types>", f"{''.join(new_ct_overrides)}</Types>")
        ET.fromstring(cleaned_ct.encode("utf-8"))

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = dst_path.with_suffix(".exp.tmp.pptx")
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
            skip_prefixes = ("ppt/slides/av_slide_", "ppt/slides/_rels/av_slide_", "ppt/media/av_art_", "ppt/av_expanded_v1.json")
            for info in zin.infolist():
                if any(info.filename.startswith(sp) for sp in skip_prefixes):
                    continue
                raw = zin.read(info.filename)
                if info.filename == "ppt/presentation.xml":
                    raw = new_pres_xml.encode("utf-8")
                elif info.filename == "ppt/_rels/presentation.xml.rels":
                    raw = cleaned_pres_rels.encode("utf-8")
                elif info.filename == "[Content_Types].xml":
                    raw = cleaned_ct.encode("utf-8")
                elif info.filename in used_orig_paths_to_morph and "animations" not in slug:
                    try:
                        raw = attach_morph_transition(raw)
                    except Exception:
                        pass
                zi = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(zi, raw)

            for part_name, pbytes in {**new_slides_bytes, **new_slide_rels_bytes, **new_media_bytes}.items():
                zout.writestr(part_name, pbytes)

        if not zipfile.is_zipfile(tmp_path):
            tmp_path.unlink(missing_ok=True)
            raise RuntimeError(f"Output invalid zip for {slug}")
        shutil.move(str(tmp_path), str(dst_path))

    if sync_previews:
        av_png_lookup = dict(av_specs_for_png)
        preview_dir.mkdir(parents=True, exist_ok=True)
        for old_png in preview_dir.glob("slide_*.png"):
            old_png.unlink(missing_ok=True)
        for final_pos, (kind, payload) in enumerate(timeline, start=1):
            if final_pos > 16:
                break
            out_png = preview_dir / f"slide_{final_pos:02d}.png"
            if kind == "orig":
                orig_idx = payload[0]
                if orig_idx in orig_png_map:
                    out_png.write_bytes(orig_png_map[orig_idx])
            else:
                spec = av_png_lookup.get(final_pos)
                if spec:
                    render_keyframe_png(spec, out_png)

    return {
        "slug": slug,
        "status": "expanded",
        "orig": k,
        "final": len(timeline),
        "av_added": needed_av,
        "family": fam["label"],
        "family_id": fam["id"],
    }


def _curated_worker(task: tuple[dict[str, Any], int, list[dict[str, Any]], bool]) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
    item, idx, assets, force = task
    slug = item["slug"]
    src = Path(item["path"])
    dst = CURATED_OUT_DIR / f"{slug}.pptx"
    try:
        res = expand_single_pptx(
            src, dst, slug, deck_idx=idx, assets=assets, meta_info=item, sync_previews=True, force=force
        )
        return item, res, None
    except Exception as exc:
        return item, None, str(exc)


def run_curated(assets: list[dict[str, Any]], force: bool, family_map: dict[str, dict[str, str]]) -> None:
    CURATED_OUT_DIR.mkdir(parents=True, exist_ok=True)
    curated = json.loads(CURATED_INDEX.read_text(encoding="utf-8"))
    curated.sort(key=lambda x: (0 if x.get("slug") == "modnexus-global-modding-union" else 1))

    family_map["modnexus-global-modding-union"] = {"id": "modnexus_flagship", "label": "MODNEXUS Flagship"}
    tasks = []
    for idx, item in enumerate(curated):
        slug = item["slug"]
        if slug == "modnexus-global-modding-union":
            continue
        if not Path(item["path"]).exists():
            print(f"  [SKIP MISSING] {slug}: {item['path']}")
            continue
        tasks.append((item, idx, assets, force))

    print(f"[CURATED] Rebuilding {len(tasks)} curated decks across 16 design systems (MODNEXUS #1 untouched)...", flush=True)
    done_cnt = 0
    with ProcessPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(_curated_worker, t) for t in tasks]
        for fut in as_completed(futs):
            item, res, err = fut.result()
            slug = item["slug"]
            if err:
                print(f"  [ERR CURATED] {slug}: {err}", flush=True)
                continue
            item["path"] = str(CURATED_OUT_DIR / f"{slug}.pptx")
            if res and res.get("final"):
                item["slides"] = res["final"]
            if res and res.get("family"):
                family_map[slug] = {"id": res["family_id"], "label": res["family"]}
            done_cnt += 1

    CURATED_INDEX.write_text(json.dumps(curated, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[CURATED COMPLETE] Processed {done_cnt} curated decks -> {CURATED_INDEX}", flush=True)


def _scraped_worker(task: tuple[str, int, list[dict[str, Any]], dict[str, Any], bool]) -> tuple[str, str, dict[str, Any] | None, str | None]:
    p_str, deck_idx, assets, meta_info, force = task
    p = Path(p_str)
    slug = slugify(p.stem)
    try:
        res = expand_single_pptx(
            p, p, slug, deck_idx=deck_idx, assets=assets, meta_info=meta_info, sync_previews=True, force=force
        )
        return p.name, slug, res, None
    except Exception as exc:
        return p.name, slug, None, str(exc)


def run_scraped(assets: list[dict[str, Any]], force: bool, limit: int, family_map: dict[str, dict[str, str]]) -> None:
    meta_map = json.loads(SCRAPED_META.read_text(encoding="utf-8")) if SCRAPED_META.exists() else {}
    files = sorted(SCRAPED_DIR.glob("*.pptx"))
    if limit > 0:
        files = files[:limit]
    total = len(files)
    done_cnt = 0
    skip_cnt = 0
    err_cnt = 0

    tasks = []
    for idx, p in enumerate(files):
        meta = meta_map.get(p.name, {}) if isinstance(meta_map, dict) else {}
        meta_info = {
            "title": meta.get("inferred_title") or meta.get("title") or p.stem,
            "category": meta.get("inferred_category") or meta.get("category") or "Strategy",
            "industry": meta.get("industry") or "Enterprise",
        }
        tasks.append((str(p), idx + 100, assets, meta_info, force))

    print(f"[SCRAPED] Expanding {total} decks across 16 Avant-Garde systems with 8 workers...", flush=True)
    with ProcessPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(_scraped_worker, t) for t in tasks]
        for processed, fut in enumerate(as_completed(futs), start=1):
            fname, slug, res, err = fut.result()
            if err:
                err_cnt += 1
                print(f"  [ERR] {fname}: {err}", flush=True)
            elif res and res["status"] == "expanded":
                done_cnt += 1
                if res.get("family"):
                    family_map[slug] = {"id": res["family_id"], "label": res["family"]}
            else:
                skip_cnt += 1
            if processed % 150 == 0 or processed == total:
                print(f"[SCRAPED {processed}/{total}] expanded={done_cnt}, skipped={skip_cnt}, errors={err_cnt}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["curated", "scraped", "all"], default="all")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    assets = json.loads(ASSET_MANIFEST.read_text(encoding="utf-8"))
    if len(assets) < 50:
        raise RuntimeError(f"Asset bank too small ({len(assets)})")

    family_map: dict[str, dict[str, str]] = (
        json.loads(FAMILY_MAP_PATH.read_text(encoding="utf-8")) if FAMILY_MAP_PATH.exists() else {}
    )

    if args.mode in ("curated", "all"):
        run_curated(assets, force=args.force, family_map=family_map)
    if args.mode in ("scraped", "all"):
        run_scraped(assets, force=args.force, limit=args.limit, family_map=family_map)

    FAMILY_MAP_PATH.write_text(json.dumps(family_map, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[DONE] Saved design family registry ({len(family_map)} entries) -> {FAMILY_MAP_PATH}", flush=True)


if __name__ == "__main__":
    main()
