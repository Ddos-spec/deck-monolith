"""
DNA-Preserving Organic Layer Deconstruction & Morph Choreography Engine
----------------------------------------------------------------------
Architecture:
  - Preserves MODNEXUS (`modnexus-global-modding-union`) untouched as Specimen #1.
  - Extracts true visual DNA directly from each deck's original slides (`slide1..K.xml`,
    `slideMaster1.xml`, `theme1.xml`): background color, foreground ink, real accent
    colors, monochrome lock (never injects chromatic colors onto B&W decks), and typeface
    roles (`Serif`, `Mono`, `Display`, `Sans`, `CJK`).
  - Eliminates both the "2-designer Frankenstein" split (`orig` vs random colored `av`)
    AND rigid template stencils (`8 layouts` / `fixed 15 slides`):
      * Deconstructs native rich slides into 2-4 progressive XML stages (`Framing ->
        Wave Unfold -> Full Native Composition -> DNA Focus Synthesis`) with matched
        `!!sXX-layer-YY` Morph IDs across consecutive frames so shapes glide organically
        into screen rather than popping or breaking design continuity.
      * Rebuilds bare/unstyled text-only slides via continuous proportion-driven generative
        stages locked 100% to the deck's original DNA palette + native media / DNA vector
        architecture (zero unrelated foreign stock photography).
      * Produces organic total slide counts reflecting real deck density (11..100+ slides).
  - Upgraded lxml XML manipulation preserves every OOXML namespace prefix verbatim and
    validates all XML parts before writing atomic ZIP archives.
  - Upgraded 2x-supersampled Pillow OOXML renderer handles `<p:grpSp>` transforms,
    `<a:schemeClr>` tint/lumMod, `<a:gradFill>`, ellipses/roundRects/lines/polygons,
    rotated boxes, and CJK fallback (`msyh.ttc`).
"""

from __future__ import annotations

import argparse
import colorsys
import copy
import hashlib
import html
import io
import json
import math
import os
import re
import shutil
import zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from lxml import etree as LET
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

BASE_DIR = Path(r"D:\code\ppt_studio")
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
EMU_PER_CM = 360000

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

# Retained palette reference systems for fallback taxonomy / ai_slide_director imports
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
        "acc1": "E03C1F", "acc2": "1D4ED8", "on_acc1": "FFFFFF", "on_acc2": "FFFFFF",
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
PARSER = LET.XMLParser(remove_blank_text=False, recover=True)


# ---------------------------------------------------------------------------
# Color, Contrast & Font Helpers
# ---------------------------------------------------------------------------

def hex_rgb(h: str) -> tuple[int, int, int]:
    h = (h or "FFFFFF").lstrip("#").upper()
    if len(h) != 6 or not re.fullmatch(r"[0-9A-F]{6}", h):
        h = "F6F3EC"
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_hex(r: int, g: int, b: int) -> str:
    return f"{max(0, min(255, int(round(r)))):02X}{max(0, min(255, int(round(g)))):02X}{max(0, min(255, int(round(b)))):02X}"


def hex_rgba(h: str, alpha_100k: int = 100000) -> tuple[int, int, int, int]:
    r, g, b = hex_rgb(h)
    a = max(0, min(255, int(round(alpha_100k * 255 / 100000.0))))
    return (r, g, b, a)


def color_lum(h: str) -> float:
    r, g, b = hex_rgb(h)
    return 0.299 * r + 0.587 * g + 0.114 * b


def rel_lum(h: str) -> float:
    def ch(v: int) -> float:
        s = v / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = hex_rgb(h)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast_ratio(h1: str, h2: str) -> float:
    l1, l2 = rel_lum(h1), rel_lum(h2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def color_sat(h: str) -> int:
    r, g, b = hex_rgb(h)
    return max(r, g, b) - min(r, g, b)


def color_dist(h1: str, h2: str) -> float:
    r1, g1, b1 = hex_rgb(h1)
    r2, g2, b2 = hex_rgb(h2)
    return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)


def blend_hex(h1: str, h2: str, t: float) -> str:
    r1, g1, b1 = hex_rgb(h1)
    r2, g2, b2 = hex_rgb(h2)
    return rgb_hex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)


def apply_color_mods(hex_val: str, color_el: LET._Element) -> str:
    r, g, b = hex_rgb(hex_val)
    lum_mod = color_el.find(f"{{{NS_A}}}lumMod")
    lum_off = color_el.find(f"{{{NS_A}}}lumOff")
    tint_el = color_el.find(f"{{{NS_A}}}tint")
    shade_el = color_el.find(f"{{{NS_A}}}shade")

    if tint_el is not None and tint_el.attrib.get("val"):
        t = int(tint_el.attrib["val"]) / 100000.0
        r = r * t + 255 * (1.0 - t)
        g = g * t + 255 * (1.0 - t)
        b = b * t + 255 * (1.0 - t)
    if shade_el is not None and shade_el.attrib.get("val"):
        s = int(shade_el.attrib["val"]) / 100000.0
        r *= s
        g *= s
        b *= s
    if lum_mod is not None or lum_off is not None:
        h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        if lum_mod is not None and lum_mod.attrib.get("val"):
            l *= int(lum_mod.attrib["val"]) / 100000.0
        if lum_off is not None and lum_off.attrib.get("val"):
            l += int(lum_off.attrib["val"]) / 100000.0
        l = max(0.0, min(1.0, l))
        nr, ng, nb = colorsys.hls_to_rgb(h, l, s)
        r, g, b = nr * 255.0, ng * 255.0, nb * 255.0
    return rgb_hex(r, g, b)


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


def slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-") or "deck"


def clean_title_for_slide(raw: str) -> str:
    s = re.sub(r"^(?:gh|ia|sc)[-_]+", "", (raw or "").strip(), flags=re.IGNORECASE)
    s = re.sub(r"[-_][0-9a-f]{4}$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\d{6,}[_-]*", "", s)
    s = re.sub(r"\.(pptx?|key|pdf)$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[_~]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" —-:,")
    return s or "Editorial Presentation"


def pick_design_family(slug: str, category: str, industry: str, deck_idx: int) -> dict[str, Any]:
    """Select reference family deterministically (kept for sibling tool compatibility)."""
    h = int(hashlib.md5(f"{slug}:{category}:{industry}".encode("utf-8", "ignore")).hexdigest(), 16)
    prefs = INDUSTRY_PREFERRED_FAMILIES.get(industry)
    if prefs and (deck_idx % 3 != 2):
        idx = prefs[(deck_idx + h) % len(prefs)]
    else:
        idx = (deck_idx * 5 + h) % len(DESIGN_FAMILIES)
    return dict(DESIGN_FAMILIES[idx], index=idx)


def safe_pic_box(max_w: float, max_h: float, aspect: float) -> tuple[float, float]:
    asp = max(0.58, min(2.25, aspect or 1.4))
    w = max_w
    h = w / asp
    if h > max_h:
        h = max_h
        w = h * asp
    return round(w, 3), round(h, 3)


def wrap_headline(title: str, max_chars: int = 18, max_lines: int = 3, upper: bool = False) -> str:
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
    out = "\n".join(lines[:max_lines]).strip(" —-:,")
    return out.upper() if upper else out


# ---------------------------------------------------------------------------
# Theme & Color Resolution + Original DNA Extractor
# ---------------------------------------------------------------------------

def parse_theme_info(zin: zipfile.ZipFile) -> tuple[dict[str, str], str, str]:
    scheme_map: dict[str, str] = {
        "dk1": "000000", "lt1": "FFFFFF", "dk2": "1F2937", "lt2": "F3F4F6",
        "accent1": "2563EB", "accent2": "0F766E", "accent3": "D97706",
        "accent4": "7C3AED", "accent5": "DC2626", "accent6": "059669",
    }
    major_font, minor_font = "Calibri", "Calibri"
    theme_files = sorted(n for n in zin.namelist() if re.match(r"^ppt/theme/theme\d+\.xml$", n))
    if theme_files:
        try:
            root = LET.fromstring(zin.read(theme_files[0]), PARSER)
            clr_scheme = root.find(f".//{{{NS_A}}}clrScheme")
            if clr_scheme is not None:
                for child in clr_scheme:
                    key = child.tag.split("}")[-1]
                    srgb = child.find(f"{{{NS_A}}}srgbClr")
                    sys_c = child.find(f"{{{NS_A}}}sysClr")
                    if srgb is not None and srgb.attrib.get("val"):
                        scheme_map[key] = srgb.attrib["val"].upper()
                    elif sys_c is not None and (sys_c.attrib.get("lastClr") or sys_c.attrib.get("val")):
                        val = (sys_c.attrib.get("lastClr") or sys_c.attrib.get("val") or "000000").upper()
                        if re.fullmatch(r"[0-9A-F]{6}", val):
                            scheme_map[key] = val
            maj = root.find(f".//{{{NS_A}}}majorFont/{{{NS_A}}}latin")
            minf = root.find(f".//{{{NS_A}}}minorFont/{{{NS_A}}}latin")
            if maj is not None and maj.attrib.get("typeface") and not maj.attrib["typeface"].startswith("+"):
                major_font = maj.attrib["typeface"]
            if minf is not None and minf.attrib.get("typeface") and not minf.attrib["typeface"].startswith("+"):
                minor_font = minf.attrib["typeface"]
        except Exception:
            pass
    scheme_map["tx1"] = scheme_map.get("dk1", "000000")
    scheme_map["bg1"] = scheme_map.get("lt1", "FFFFFF")
    scheme_map["tx2"] = scheme_map.get("dk2", "1F2937")
    scheme_map["bg2"] = scheme_map.get("lt2", "F3F4F6")
    return scheme_map, major_font, minor_font


def resolve_fill_hex(container_el: LET._Element | None, scheme_map: dict[str, str]) -> tuple[str | None, int]:
    """Resolve solidFill or gradFill hex and alpha (0..100000) from an OOXML fill owner."""
    if container_el is None:
        return None, 100000
    sf = container_el.find(f"{{{NS_A}}}solidFill")
    target = sf
    if target is None:
        gf = container_el.find(f"{{{NS_A}}}gradFill")
        if gf is not None:
            gs = gf.find(f".//{{{NS_A}}}gs")
            if gs is not None:
                target = gs
    if target is None:
        return None, 100000

    alpha = 100000
    srgb = target.find(f"{{{NS_A}}}srgbClr")
    if srgb is not None and srgb.attrib.get("val"):
        val = apply_color_mods(srgb.attrib["val"].upper(), srgb)
        al = srgb.find(f"{{{NS_A}}}alpha")
        if al is not None and al.attrib.get("val"):
            alpha = int(al.attrib["val"])
        return val, alpha

    sch = target.find(f"{{{NS_A}}}schemeClr")
    if sch is not None and sch.attrib.get("val"):
        key = sch.attrib["val"]
        base_hex = scheme_map.get(key)
        if base_hex:
            val = apply_color_mods(base_hex, sch)
            al = sch.find(f"{{{NS_A}}}alpha")
            if al is not None and al.attrib.get("val"):
                alpha = int(al.attrib["val"])
            return val, alpha
    return None, 100000


def _classify_font_role(typeface: str) -> str:
    low = typeface.lower()
    if any(k in low for k in ("courier", "consolas", "mono", "jetbrains", "fira code", "menlo")):
        return "mono"
    if any(k in low for k in ("georgia", "times", "serif", "playfair", "garamond", "palatino", "baskerville", "bodoni")):
        return "serif"
    if any(k in low for k in ("bahnschrift", "arial black", "impact", "bebas", "oswald", "montserrat", "futur", "aptos display", "syne", "space grotesk")):
        return "display"
    return "sans"


def extract_original_dna(
    zin: zipfile.ZipFile,
    slug: str,
    orig_slide_parts: list[str],
    cx_emu: int,
    cy_emu: int,
    fallback_fam: dict[str, Any],
) -> dict[str, Any]:
    """Read actual palette, monochrome character, surface temperature, and fonts from original XML."""
    scheme_map, major_font, minor_font = parse_theme_info(zin)
    names_set = set(zin.namelist())

    bg_counter: Counter[str] = Counter()
    all_color_counter: Counter[str] = Counter()
    text_color_counter: Counter[str] = Counter()
    font_counter: Counter[str] = Counter()

    scan_parts = list(orig_slide_parts[:10])
    masters = [n for n in names_set if re.match(r"^ppt/slideMasters/slideMaster\d+\.xml$", n)]
    if masters:
        scan_parts.append(sorted(masters)[0])

    for sp in scan_parts:
        is_slide = sp.startswith("ppt/slides/")
        try:
            root = LET.fromstring(zin.read(sp), PARSER)
        except Exception:
            continue

        bg_el = root.find(f".//{{{NS_P}}}bg/{{{NS_P}}}bgPr")
        if bg_el is not None:
            bh, balpha = resolve_fill_hex(bg_el, scheme_map)
            if bh and balpha > 40000:
                bg_counter[bh] += (3 if is_slide else 1)

        if not is_slide:
            continue

        sp_tree = root.find(f".//{{{NS_P}}}spTree")
        if sp_tree is not None:
            for ch in sp_tree:
                tag = ch.tag.split("}")[-1]
                if tag == "sp":
                    spPr = ch.find(f"{{{NS_P}}}spPr")
                    ext = spPr.find(f".//{{{NS_A}}}xfrm/{{{NS_A}}}ext") if spPr is not None else None
                    sh, salpha = resolve_fill_hex(spPr, scheme_map)
                    if sh and salpha > 35000:
                        if ext is not None and int(ext.attrib.get("cx", 0)) >= cx_emu * 0.78 and int(ext.attrib.get("cy", 0)) >= cy_emu * 0.78:
                            bg_counter[sh] += 4
                        else:
                            all_color_counter[sh] += 2

        for rPr in root.iter(f"{{{NS_A}}}rPr"):
            th, _ = resolve_fill_hex(rPr, scheme_map)
            if th:
                text_color_counter[th] += 1
                all_color_counter[th] += 1
            for ftag in (f"{{{NS_A}}}latin", f"{{{NS_A}}}ea"):
                fel = rPr.find(ftag)
                if fel is not None:
                    tf = fel.attrib.get("typeface", "")
                    if tf and not tf.startswith("+") and "wingding" not in tf.lower() and "symbol" not in tf.lower():
                        font_counter[tf] += 1

        for ln in root.iter(f"{{{NS_A}}}ln"):
            lh, lalpha = resolve_fill_hex(ln, scheme_map)
            if lh and lalpha > 45000:
                all_color_counter[lh] += 1

    # Determine authentic background color
    bg = bg_counter.most_common(1)[0][0] if bg_counter else scheme_map.get("bg1", "FFFFFF")
    if bg == "FFFFFF" and "style-dark-" in slug:
        # Check if original deck used near-black text instead of explicit dark bg
        dark_fills = [c for c, _ in all_color_counter.most_common(6) if color_lum(c) < 42]
        bg = dark_fills[0] if dark_fills else "111318"
    elif "style-bw-" in slug and color_sat(bg) > 15:
        bg = "FFFFFF"

    is_dark = color_lum(bg) < 115

    # Check monochrome lock across real non-background colors
    non_bg_weights = [(c, cnt) for c, cnt in all_color_counter.items() if color_dist(c, bg) > 18]
    total_w = sum(cnt for _, cnt in non_bg_weights) or 1
    neutral_w = sum(cnt for c, cnt in non_bg_weights if color_sat(c) < 22)
    chromatic = [(c, cnt) for c, cnt in non_bg_weights if color_sat(c) >= 22 and color_dist(c, bg) > 36]
    chromatic.sort(key=lambda x: x[1], reverse=True)

    is_bw_slug = slug.startswith("style-bw-")
    has_intentional_bw_spot = is_bw_slug and len(chromatic) > 0 and chromatic[0][1] >= 4
    is_monochrome = (is_bw_slug and not has_intentional_bw_spot) or (not chromatic and total_w >= 1) or (neutral_w / total_w >= 0.90)

    if is_monochrome:
        if is_dark:
            ink, muted = "F4F4F5", "A1A1AA"
            panel = blend_hex(bg, "FFFFFF", 0.08)
            card = blend_hex(bg, "FFFFFF", 0.05)
            rule = blend_hex(bg, "FFFFFF", 0.22)
            acc1, acc2 = "F4F4F5", "A1A1AA"
            on_acc1, on_acc2 = "111111", "111111"
        else:
            ink, muted = "141414", "52525B"
            panel = blend_hex(bg, ink, 0.06)
            card = "FFFFFF" if bg != "FFFFFF" else "F6F6F6"
            rule = blend_hex(bg, ink, 0.24)
            acc1, acc2 = "1A1A1A", "71717A"
            on_acc1, on_acc2 = "FFFFFF", "FFFFFF"
    else:
        # Pick highest-contrast original ink
        candidate_inks = [
            c for c, _ in text_color_counter.most_common(8)
            if contrast_ratio(c, bg) >= 4.8 and color_sat(c) < 48
        ]
        if candidate_inks:
            ink = candidate_inks[0]
        else:
            ink = "F5F3EE" if is_dark else "14171F"
        if contrast_ratio(ink, bg) < 5.5:
            ink = "F8FAFC" if is_dark else "111827"

        muted = blend_hex(ink, bg, 0.38)
        if is_dark:
            panel = blend_hex(bg, "FFFFFF", 0.075)
            card = blend_hex(bg, "FFFFFF", 0.045)
            rule = blend_hex(bg, "FFFFFF", 0.20)
        else:
            panel = blend_hex(bg, ink, 0.065)
            card = "FFFFFF" if color_lum(bg) < 245 else "F7F5F0"
            rule = blend_hex(bg, ink, 0.18)

        # Pick 1..2 authentic chromatic accents from XML; only consult theme1.xml if slides had 0 explicit accents
        picked_accents: list[str] = []
        for c, _ in chromatic:
            if all(color_dist(c, prev) > 52 for prev in picked_accents) and contrast_ratio(c, bg) >= 1.6:
                picked_accents.append(c)
            if len(picked_accents) >= 2:
                break
        if len(picked_accents) == 0:
            for key in ("accent1", "accent2", "accent3"):
                sc = scheme_map.get(key)
                if sc and color_sat(sc) >= 22 and color_dist(sc, bg) > 40 and all(color_dist(sc, p) > 52 for p in picked_accents):
                    if not has_intentional_bw_spot:
                        picked_accents.append(sc)
                if len(picked_accents) >= 2:
                    break

        if not picked_accents:
            acc1 = ink
            acc2 = blend_hex(ink, bg, 0.45)
        elif len(picked_accents) == 1:
            acc1 = picked_accents[0]
            acc2 = ink if has_intentional_bw_spot else blend_hex(acc1, ink, 0.45)
        else:
            acc1, acc2 = picked_accents[0], picked_accents[1]

        on_acc1 = "111111" if contrast_ratio("111111", acc1) > contrast_ratio("FFFFFF", acc1) else "FFFFFF"
        on_acc2 = "111111" if contrast_ratio("111111", acc2) > contrast_ratio("FFFFFF", acc2) else "FFFFFF"

    # Typography DNA
    top_font = font_counter.most_common(1)[0][0] if font_counter else (major_font or minor_font or "Segoe UI")
    second_font = font_counter.most_common(2)[1][0] if len(font_counter) > 1 else (minor_font or top_font)
    hfont_role = _classify_font_role(top_font)
    bfont_role = _classify_font_role(second_font)
    if bfont_role == "display":
        bfont_role = "sans"

    # Accurate movement/DNA label matching nearest perceptual mood
    if is_monochrome:
        dna_id = "dna_monochrome_dark" if is_dark else "dna_monochrome_light"
        dna_label = "Obsidian Monochrome" if is_dark else "Monochrome Editorial"
    elif has_intentional_bw_spot:
        dna_id = "dna_bw_spot"
        dna_label = "Brutalist Spot Ink"
    else:
        best_fam = min(
            DESIGN_FAMILIES,
            key=lambda f: color_dist(bg, f["bg"]) * 1.4 + color_dist(acc1, f["acc1"]) * 0.7,
        )
        dna_id = f"dna_{best_fam['id']}"
        dna_label = best_fam["label"]

    return {
        "id": dna_id,
        "label": dna_label,
        "is_dark": is_dark,
        "is_monochrome": is_monochrome,
        "bg": bg,
        "panel": panel,
        "card": card,
        "ink": ink,
        "muted": muted,
        "rule": rule,
        "acc1": acc1,
        "acc2": acc2,
        "on_acc1": on_acc1,
        "on_acc2": on_acc2,
        "head_font": hfont_role,
        "body_font": bfont_role,
        "serif_sub": "serif" if hfont_role == "serif" else bfont_role,
        "raw_head_font": top_font,
        "raw_body_font": second_font,
        "scheme_map": scheme_map,
    }


def extract_native_deck_media(zin: zipfile.ZipFile, surface_bg_hex: str) -> list[dict[str, Any]]:
    """Extract native non-screenshot images from deck's ppt/media/, alpha-composited to DNA surface."""
    bg_rgb = hex_rgb(surface_bg_hex)
    candidates: list[tuple[float, dict[str, Any]]] = []
    names = [
        n for n in zin.namelist()
        if n.startswith("ppt/media/")
        and not n.startswith("ppt/media/av_art_")
        and n.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    names.sort(key=lambda n: zin.getinfo(n).file_size, reverse=True)

    for part in names[:16]:
        info = zin.getinfo(part)
        if info.file_size < 10_000 or info.file_size > 6_000_000:
            continue
        try:
            with Image.open(io.BytesIO(zin.read(part))) as im:
                w, h = im.size
                if w < 220 or h < 160:
                    continue
                ratio = w / max(1, h)
                if ratio < 0.50 or ratio > 2.40:
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
                near_white = sum(1 for r, g, b in px if r > 238 and g > 238 and b > 238) / len(px)
                st = ImageStat.Stat(thumb)
                mean_std = sum(st.stddev) / 3.0
                if near_white > 0.58 or mean_std < 18.0:
                    continue
                if w > 1280:
                    nh = max(1, int(round(h * (1280.0 / w))))
                    rgb = rgb.resize((1280, nh), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                rgb.save(buf, format="JPEG", quality=88, optimize=True)
                candidates.append((
                    mean_std + min(w, 1200) * 0.03,
                    {
                        "raw_bytes": buf.getvalue(),
                        "rgb_img": rgb,
                        "width": rgb.width,
                        "height": rgb.height,
                        "aspect": round(rgb.width / max(1, rgb.height), 4),
                        "source": f"native:{Path(part).name}",
                    },
                ))
        except Exception:
            continue

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in candidates[:8]]


def crop_native_media_variant(asset: dict[str, Any], variant: int) -> dict[str, Any]:
    """Create zoomed/cropped framing variants of an authentic native image for Morph motion."""
    rgb: Image.Image = asset.get("rgb_img")
    if rgb is None:
        rgb = Image.open(io.BytesIO(asset["raw_bytes"])).convert("RGB")
    if variant % 3 == 0:
        return asset
    w, h = rgb.size
    if variant % 3 == 1:
        # Left/upper focal detail crop (~74%)
        cw, ch = int(w * 0.76), int(h * 0.76)
        x0, y0 = int(w * 0.08), int(h * 0.10)
    else:
        # Wide cinematic panorama strip crop
        cw, ch = int(w * 0.88), int(h * 0.68)
        x0, y0 = int(w * 0.06), int(h * 0.16)
    sub = rgb.crop((x0, y0, min(w, x0 + cw), min(h, y0 + ch)))
    buf = io.BytesIO()
    sub.save(buf, format="JPEG", quality=88, optimize=True)
    return {
        "raw_bytes": buf.getvalue(),
        "width": sub.width,
        "height": sub.height,
        "aspect": round(sub.width / max(1, sub.height), 4),
        "source": f"{asset['source']}#v{variant}",
    }


def make_dna_procedural_plate(dna: dict[str, Any], seed_idx: int) -> dict[str, Any]:
    """Generate a bespoke architectural vector canvas matching 100% of deck's original DNA palette."""
    W, H = 1024, 680
    im = Image.new("RGBA", (W, H), hex_rgba(dna["panel"]))
    dr = ImageDraw.Draw(im, "RGBA")

    acc1_rgba = hex_rgba(dna["acc1"])
    acc2_rgba = hex_rgba(dna["acc2"])
    rule_rgba = hex_rgba(dna["rule"])
    card_rgba = hex_rgba(dna["card"])
    ink_soft = hex_rgba(dna["ink"], 22000)

    mode = seed_idx % 4
    # Subtle structural coordinate grid in DNA rule color
    step = 64
    for gx in range(step, W, step):
        dr.line([(gx, 0), (gx, H)], fill=(*rule_rgba[:3], 65), width=1)
    for gy in range(step, H, step):
        dr.line([(0, gy), (W, gy)], fill=(*rule_rgba[:3], 65), width=1)

    if mode == 0:
        # Concentric architectural radar / orbital geometry in DNA accents
        cx, cy = int(W * 0.54), int(H * 0.50)
        for rad, col_t in ((260, (*acc2_rgba[:3], 70)), (195, (*rule_rgba[:3], 170)), (120, acc1_rgba)):
            dr.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=col_t, width=3)
        dr.ellipse([cx - 56, cy - 56, cx + 56, cy + 56], fill=acc1_rgba)
        dr.rectangle([64, H - 148, 380, H - 64], fill=card_rgba, outline=(*acc1_rgba[:3], 200), width=3)
    elif mode == 1:
        # Constructivist stepped cantilever blocks using panel, card, acc1, acc2
        dr.rectangle([72, 80, 560, 590], fill=card_rgba, outline=rule_rgba, width=2)
        dr.rectangle([420, 150, 930, 510], fill=(*acc1_rgba[:3], 225))
        dr.rectangle([280, 290, 690, 590], fill=(*acc2_rgba[:3], 185), outline=card_rgba, width=3)
        dr.line([(72, 220), (952, 220)], fill=ink_soft, width=2)
    elif mode == 2:
        # Precision kinetic waveform bars strictly inside deck palette
        bar_w = 18
        gap = 12
        start_x = 88
        for bi in range(28):
            ang = bi * 0.34 + seed_idx * 0.7
            amp = int(75 + 165 * (0.5 + 0.5 * math.sin(ang)))
            bx = start_x + bi * (bar_w + gap)
            if bx + bar_w > W - 64:
                break
            col = acc1_rgba if bi % 5 == 0 else (acc2_rgba if bi % 7 == 0 else (*hex_rgb(dna["ink"]), 210))
            dr.rectangle([bx, H // 2 - amp, bx + bar_w, H // 2 + amp], fill=col)
    else:
        # Diptych typographic scale frame with overlapping rings
        dr.rectangle([60, 60, W - 60, H - 60], outline=rule_rgba, width=3)
        dr.rectangle([100, 100, 500, H - 100], fill=card_rgba, outline=acc1_rgba, width=2)
        dr.ellipse([480, 130, 900, 550], fill=(*acc2_rgba[:3], 210), outline=card_rgba, width=4)
        dr.line([(60, H // 2), (W - 60, H // 2)], fill=acc1_rgba, width=2)

    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="JPEG", quality=90, optimize=True)
    return {
        "raw_bytes": buf.getvalue(),
        "width": W,
        "height": H,
        "aspect": round(W / H, 4),
        "source": f"dna_vector_{mode}",
    }


# ---------------------------------------------------------------------------
# Slide Content & Native Layer Inspection (lxml Prefix-Safe)
# ---------------------------------------------------------------------------

def _extract_node_box(el: LET._Element) -> tuple[int, int, int, int] | None:
    xf = el.find(f".//{{{NS_A}}}xfrm")
    if xf is None:
        return None
    off = xf.find(f"{{{NS_A}}}off")
    ext = xf.find(f"{{{NS_A}}}ext")
    if off is None or ext is None:
        return None
    return (
        int(float(off.attrib.get("x", 0))),
        int(float(off.attrib.get("y", 0))),
        int(float(ext.attrib.get("cx", 0))),
        int(float(ext.attrib.get("cy", 0))),
    )


def _shift_node_xfrm(el: LET._Element, dx: int, dy: int, scale: float = 1.0) -> None:
    tag = el.tag.split("}")[-1]
    xf = el.find(f"{{{NS_P}}}spPr/{{{NS_A}}}xfrm") if tag != "grpSp" else el.find(f"{{{NS_P}}}grpSpPr/{{{NS_A}}}xfrm")
    if xf is None:
        xf = el.find(f"{{{NS_A}}}xfrm")
    if xf is None:
        return
    off = xf.find(f"{{{NS_A}}}off")
    ext = xf.find(f"{{{NS_A}}}ext")
    if off is None or ext is None:
        return
    x = int(float(off.attrib.get("x", 0)))
    y = int(float(off.attrib.get("y", 0)))
    cx = int(float(ext.attrib.get("cx", 0)))
    cy = int(float(ext.attrib.get("cy", 0)))
    if scale != 1.0 and cx > 0 and cy > 0:
        ncx = max(36000, int(round(cx * scale)))
        ncy = max(36000, int(round(cy * scale)))
        x -= (ncx - cx) // 2
        y -= (ncy - cy) // 2
        ext.attrib["cx"] = str(ncx)
        ext.attrib["cy"] = str(ncy)
    off.attrib["x"] = str(x + dx)
    off.attrib["y"] = str(y + dy)


def _node_text_info(el: LET._Element) -> tuple[str, int, list[str]]:
    paras: list[str] = []
    max_sz = 1400
    for p in el.iter(f"{{{NS_A}}}p"):
        parts = []
        for t in p.iter(f"{{{NS_A}}}t"):
            if t.text:
                parts.append(html.unescape(t.text))
        line = re.sub(r"\s+", " ", "".join(parts)).strip()
        if line:
            paras.append(line)
    for rPr in el.iter(f"{{{NS_A}}}rPr"):
        sz = rPr.attrib.get("sz")
        if sz and sz.isdigit():
            max_sz = max(max_sz, int(sz))
    full = " ".join(paras)
    return full, max_sz, paras


def _set_cNvPr_name(el: LET._Element, actor_name: str) -> None:
    cnv = el.find(f".//{{{NS_P}}}cNvPr")
    if cnv is not None:
        cnv.attrib["name"] = actor_name


def _ensure_unique_shape_ids(root: LET._Element) -> None:
    seen: set[str] = set()
    next_id = 2
    for cnv in root.iter(f"{{{NS_P}}}cNvPr"):
        cid = cnv.attrib.get("id", "")
        while not cid.isdigit() or cid in seen or int(cid) < 1:
            cid = str(next_id)
            next_id += 1
        seen.add(cid)
        cnv.attrib["id"] = cid
        if int(cid) >= next_id:
            next_id = int(cid) + 1


def _inject_bg_if_missing(root: LET._Element, bg_hex: str) -> None:
    csld = root.find(f"{{{NS_P}}}cSld")
    if csld is None:
        return
    if csld.find(f"{{{NS_P}}}bg") is not None:
        return
    bg_el = LET.Element(f"{{{NS_P}}}bg")
    bg_pr = LET.SubElement(bg_el, f"{{{NS_P}}}bgPr")
    sfill = LET.SubElement(bg_pr, f"{{{NS_A}}}solidFill")
    srgb = LET.SubElement(sfill, f"{{{NS_A}}}srgbClr")
    srgb.attrib["val"] = bg_hex
    LET.SubElement(bg_pr, f"{{{NS_A}}}effectLst")
    csld.insert(0, bg_el)


def attach_morph_transition_lxml(root: LET._Element) -> bytes:
    """Attach <p159:morph option='byObject'/> and clean ECMA-376 <p:sld> child order."""
    # Ensure namespaces declared on root if missing via string roundtrip safely
    for old_t in root.findall(f"{{{NS_P}}}transition"):
        root.remove(old_t)
    morph_el = LET.fromstring(MORPH_TRANSITION_XML.encode("utf-8"), PARSER)

    # Insert right before <p:timing> or <p:extLst>, else append at end of <p:sld>
    insert_idx = len(root)
    for idx, ch in enumerate(list(root)):
        local = ch.tag.split("}")[-1]
        if local in ("timing", "extLst"):
            insert_idx = idx
            break
    root.insert(insert_idx, morph_el)
    out = LET.tostring(root, encoding="utf-8", xml_declaration=True)
    LET.fromstring(out, PARSER)
    return out


# ---------------------------------------------------------------------------
# Generative DNA Composer (Non-Stencil Continuous Proportion Layout)
# ---------------------------------------------------------------------------

def build_generative_dna_ooxml(spec: dict[str, Any], cx_emu: int, cy_emu: int, pic_rids: dict[str, str]) -> bytes:
    sx = cx_emu / CANVAS_W_EMU
    sy = cy_emu / CANVAS_H_EMU
    smin = min(sx, sy)

    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<p:sld xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}" '
        f'xmlns:p14="{NS_P14}" xmlns:mc="{NS_MC}" xmlns:p159="{NS_P159}">'
        '<p:cSld>'
        f'<p:bg><p:bgPr><a:solidFill><a:srgbClr val="{spec["bg"]}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
        '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
    ]

    sid_counter = 2
    anim_ids: list[int] = []
    for lyr in spec["layers"]:
        sid = sid_counter
        sid_counter += 1
        x = int(round(lyr["x"] * EMU_PER_CM * sx))
        y = int(round(lyr["y"] * EMU_PER_CM * sy))
        w = max(36000, int(round(lyr["w"] * EMU_PER_CM * sx)))
        h = max(12000, int(round(lyr["h"] * EMU_PER_CM * sy)))
        nm = escape(lyr["name"])
        rot_attr = f' rot="{int(round(lyr.get("rot", 0) * 60000))}"' if lyr.get("rot") else ""

        if lyr.get("animate"):
            anim_ids.append(sid)

        if lyr["kind"] == "pic":
            rid = pic_rids.get(lyr["name"], "rId2")
            shdw_xml = (
                '<a:effectLst><a:outerShdw blurRad="139700" dist="63500" dir="2700000" algn="tl" rotWithShape="0">'
                '<a:srgbClr val="000000"><a:alpha val="24000"/></a:srgbClr></a:outerShdw></a:effectLst>'
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
                f'<a:ln w="{lyr.get("lw", 15240)}"><a:solidFill><a:srgbClr val="{lyr["line"]}"/></a:solidFill></a:ln>'
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
            raw_tf = lyr.get("raw_font")
            font_map = {"display": "Bahnschrift", "serif": "Georgia", "mono": "Consolas", "sans": "Segoe UI"}
            typeface = escape(raw_tf) if raw_tf else font_map.get(lyr.get("font", "sans"), "Segoe UI")
            sz_100 = int(round(lyr.get("size", 14) * 100 * (smin / 360000.0)))
            bold_attr = ' b="1"' if lyr.get("bold") else ""
            algn = lyr.get("align", "l")
            valgn = lyr.get("valign", "t")
            ls = lyr.get("line_spacing", 1.15)
            lnspc_xml = f'<a:lnSpc><a:spcPct val="{int(round(ls * 100000))}"/></a:lnSpc>'

            paras = []
            for para_txt in str(lyr["text"]).splitlines() or [""]:
                paras.append(
                    f'<a:p><a:pPr algn="{algn}">{lnspc_xml}</a:pPr>'
                    f'<a:r><a:rPr lang="en-US" sz="{sz_100}"{bold_attr}>'
                    f'<a:solidFill><a:srgbClr val="{lyr["color"]}"/></a:solidFill>'
                    f'<a:latin typeface="{typeface}"/><a:ea typeface="Microsoft YaHei"/></a:rPr>'
                    f'<a:t>{escape(para_txt)}</a:t></a:r></a:p>'
                )
            parts.append(
                f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{nm}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
                f'<p:spPr><a:xfrm{rot_attr}><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
                f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>'
                f'<p:txBody><a:bodyPr wrap="square" lIns="0" rIns="0" tIns="0" bIns="0" anchor="{valgn}"/>'
                f'<a:lstStyle/>{"".join(paras)}</p:txBody></p:sp>'
            )

    parts.append("</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>")
    parts.append(MORPH_TRANSITION_XML)

    if anim_ids:
        tparts = [
            '<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
            '<p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        ]
        nid = 3
        for idx, spid in enumerate(anim_ids[:5]):
            delay = idx * 130
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
    LET.fromstring(out, PARSER)
    return out


def build_generative_dna_stages(
    orig_idx: int,
    headline: str,
    points: list[str],
    dna: dict[str, Any],
    native_media: list[dict[str, Any]],
    deck_title: str,
    category: str,
    industry: str,
    n_stages: int,
) -> list[dict[str, Any]]:
    """
    Create 2-4 generative Morph stages driven continuously by content ratios & DNA tokens
    (no 8-template stencil), keeping the exact original deck palette & native/DNA-vector art.
    """
    prefix = f"!!s{orig_idx:02d}"
    bg, panel, card, ink, muted, rule, acc1, acc2 = (
        dna["bg"], dna["panel"], dna["card"], dna["ink"], dna["muted"], dna["rule"], dna["acc1"], dna["acc2"]
    )
    hfont = dna["head_font"]
    bfont = dna["body_font"]
    raw_hf = dna.get("raw_head_font")
    raw_bf = dna.get("raw_body_font")

    # Continuous layout geometry computed from slide index & content vector
    phi = (orig_idx * 0.618033988749895 + len(headline) * 0.031) % 1.0
    flip = (orig_idx % 2 == 1)
    split_x = round(14.5 + 3.8 * math.sin(phi * math.pi), 2)
    margin = round(1.5 + 0.55 * ((phi * 3.0) % 1.0), 2)

    if native_media:
        base_asset = native_media[(orig_idx - 1) % len(native_media)]
    else:
        base_asset = make_dna_procedural_plate(dna, orig_idx)

    lead_txt = points[0] if points else f"{deck_title} — structured {category.lower()} analysis for {industry}."
    detail_pts = points[1:4] if len(points) > 1 else [lead_txt]
    headline_clean = clean_title_for_slide(headline)[:68]
    head_sz = 36.0 if len(headline_clean) < 26 else (30.0 if len(headline_clean) < 44 else 25.0)
    ghost_col = blend_hex(bg, acc1, 0.18 if dna["is_dark"] else 0.14)

    stages: list[dict[str, Any]] = []
    for st in range(n_stages):
        layers: list[dict[str, Any]] = []
        stage_asset = crop_native_media_variant(base_asset, st) if native_media else base_asset
        pw, ph = safe_pic_box(CANVAS_W_CM - split_x - margin if not flip else split_x - margin * 1.4, 13.6, stage_asset["aspect"])

        if st == 0:
            # STAGE 1: Atmospheric Tension & Oversized Focus Anchor (points rest off-canvas for Morph glide)
            bg_band_w = round(CANVAS_W_CM * (0.36 + 0.18 * phi), 2)
            layers.append({"kind": "shape", "preset": "rect", "name": f"{prefix}-bgband", "x": 0.0 if not flip else CANVAS_W_CM - bg_band_w, "y": 0.0, "w": bg_band_w, "h": CANVAS_H_CM, "fill": panel})
            layers.append({"kind": "text", "name": f"{prefix}-num", "text": f"{orig_idx:02d}", "x": CANVAS_W_CM - 11.5 if not flip else 1.4, "y": -0.4, "w": 10.5, "h": 7.4, "font": "display", "size": 148.0, "bold": True, "color": ghost_col, "align": "r" if not flip else "l"})

            art_x = round((CANVAS_W_CM - pw - margin) if not flip else margin, 2)
            art_y = round((CANVAS_H_CM - ph) * 0.5, 2)
            layers.append({"kind": "pic", "name": f"{prefix}-art", "asset": stage_asset, "x": art_x, "y": art_y, "w": pw, "h": ph, "border": rule, "shadow": not dna["is_dark"]})
            layers.append({"kind": "shape", "preset": "rect", "name": f"{prefix}-rule", "x": margin if not flip else art_x + pw + 1.0, "y": 4.2, "w": 4.4, "h": 0.14, "fill": acc1})
            layers.append({"kind": "text", "name": f"{prefix}-kicker", "text": f"{orig_idx:02d} // {category.upper()} · {industry.upper()}", "x": margin if not flip else art_x + pw + 1.0, "y": 3.45, "w": 12.8, "h": 0.55, "font": "mono", "size": 9.5, "bold": True, "color": acc1})
            layers.append({"kind": "text", "name": f"{prefix}-title", "text": wrap_headline(headline_clean, 18, 3), "x": margin if not flip else art_x + pw + 1.0, "y": 4.85, "w": min(14.5, CANVAS_W_CM - pw - margin * 2.5), "h": 6.4, "font": hfont, "raw_font": raw_hf, "size": head_sz + 3.0, "bold": True, "color": ink, "line_spacing": 1.05, "animate": True})
            layers.append({"kind": "text", "name": f"{prefix}-sub", "text": lead_txt[:150], "x": margin if not flip else art_x + pw + 1.0, "y": CANVAS_H_CM + 1.2, "w": 13.0, "h": 4.2, "font": bfont, "raw_font": raw_bf, "size": 13.0, "color": muted})
            for pi in range(min(3, len(detail_pts))):
                layers.append({"kind": "shape", "preset": "rect", "name": f"{prefix}-card-{pi}", "x": CANVAS_W_CM + 2.0, "y": 13.2, "w": 8.6, "h": 3.8, "fill": card, "line": rule})
                layers.append({"kind": "text", "name": f"{prefix}-pt-{pi}", "text": detail_pts[pi][:115], "x": CANVAS_W_CM + 2.4, "y": 13.6, "w": 7.8, "h": 3.0, "font": bfont, "raw_font": raw_bf, "size": 11.0, "color": muted})

        elif st == 1:
            # STAGE 2: Progressive Unfold — headline settles & visual + cards glide into asymmetric reading field
            layers.append({"kind": "shape", "preset": "rect", "name": f"{prefix}-bgband", "x": 0.0, "y": 0.0, "w": CANVAS_W_CM, "h": 3.2, "fill": panel})
            layers.append({"kind": "text", "name": f"{prefix}-num", "text": f"{orig_idx:02d}", "x": CANVAS_W_CM - 7.5, "y": 0.3, "w": 6.0, "h": 2.6, "font": "display", "size": 58.0, "bold": True, "color": blend_hex(panel, acc1, 0.25), "align": "r"})
            layers.append({"kind": "shape", "preset": "rect", "name": f"{prefix}-rule", "x": margin, "y": 3.2, "w": CANVAS_W_CM - margin * 2, "h": 0.12, "fill": acc1})
            layers.append({"kind": "text", "name": f"{prefix}-kicker", "text": f"{orig_idx:02d} // LAYER EXPANSION", "x": margin, "y": 0.65, "w": 18.0, "h": 0.5, "font": "mono", "size": 9.5, "bold": True, "color": acc1})
            layers.append({"kind": "text", "name": f"{prefix}-title", "text": wrap_headline(headline_clean, 30, 2), "x": margin, "y": 1.25, "w": 24.5, "h": 1.8, "font": hfont, "raw_font": raw_hf, "size": max(24.0, head_sz - 4.0), "bold": True, "color": ink})

            w2, h2 = safe_pic_box(13.8, 8.6, stage_asset["aspect"])
            ax2 = margin if not flip else CANVAS_W_CM - margin - w2
            layers.append({"kind": "pic", "name": f"{prefix}-art", "asset": stage_asset, "x": ax2, "y": 4.0, "w": w2, "h": h2, "border": rule})
            tx2 = ax2 + w2 + 1.1 if not flip else margin
            tw2 = CANVAS_W_CM - w2 - margin * 2 - 1.1
            layers.append({"kind": "text", "name": f"{prefix}-sub", "text": lead_txt[:220], "x": tx2, "y": 4.4, "w": tw2, "h": 5.8, "font": bfont, "raw_font": raw_bf, "size": 14.5, "color": ink, "line_spacing": 1.38, "animate": True})

            n_pts = min(3, len(detail_pts))
            card_gap = 0.85
            usable_w = CANVAS_W_CM - margin * 2
            cw = (usable_w - card_gap * max(0, n_pts - 1)) / max(1, n_pts)
            for pi in range(n_pts):
                cx_p = margin + pi * (cw + card_gap)
                layers.append({"kind": "shape", "preset": "rect", "name": f"{prefix}-card-{pi}", "x": cx_p, "y": 13.25, "w": cw, "h": 4.35, "fill": card, "line": acc2 if pi == 0 else rule})
                layers.append({"kind": "text", "name": f"{prefix}-pt-{pi}", "text": detail_pts[pi][:130], "x": cx_p + 0.55, "y": 13.7, "w": cw - 1.1, "h": 3.45, "font": bfont, "raw_font": raw_bf, "size": 11.5, "color": muted if pi > 0 else ink, "line_spacing": 1.28, "animate": True})

        elif st == 2:
            # STAGE 3: Camera Zoom / Ma Negative-Space Pause or Structural Contrast View
            layers.append({"kind": "shape", "preset": "rect", "name": f"{prefix}-bgband", "x": 0.0, "y": 0.0, "w": CANVAS_W_CM, "h": 1.1, "fill": acc1 if not dna["is_monochrome"] else panel})
            layers.append({"kind": "text", "name": f"{prefix}-kicker", "text": f"{orig_idx:02d} // THESIS & DETAIL", "x": margin, "y": 0.28, "w": 18.0, "h": 0.5, "font": "mono", "size": 9.5, "bold": True, "color": dna["on_acc1"] if not dna["is_monochrome"] else ink})
            layers.append({"kind": "shape", "preset": "rect", "name": f"{prefix}-rule", "x": margin, "y": 13.1, "w": 5.0, "h": 0.14, "fill": acc2})
            w3, h3 = safe_pic_box(16.8, 10.6, stage_asset["aspect"])
            ax3 = round(CANVAS_W_CM - margin - w3 if flip else margin, 2)
            layers.append({"kind": "pic", "name": f"{prefix}-art", "asset": stage_asset, "x": ax3, "y": 2.4, "w": w3, "h": h3, "border": rule})
            tx3 = margin if flip else ax3 + w3 + 1.2
            tw3 = CANVAS_W_CM - w3 - margin * 2 - 1.2
            layers.append({"kind": "text", "name": f"{prefix}-title", "text": wrap_headline(headline_clean, 20, 3), "x": tx3, "y": 2.6, "w": tw3, "h": 4.2, "font": hfont, "raw_font": raw_hf, "size": 26.0, "bold": True, "color": ink})
            layers.append({"kind": "text", "name": f"{prefix}-sub", "text": (detail_pts[-1] if detail_pts else lead_txt)[:230], "x": tx3, "y": 7.3, "w": tw3, "h": 5.5, "font": bfont, "raw_font": raw_bf, "size": 14.0, "color": muted, "line_spacing": 1.4, "animate": True})
            layers.append({"kind": "text", "name": f"{prefix}-num", "text": f"{orig_idx:02d}", "x": tx3, "y": 13.6, "w": tw3, "h": 3.2, "font": "display", "size": 52.0, "bold": True, "color": acc1})
            for pi in range(min(3, len(detail_pts))):
                layers.append({"kind": "shape", "preset": "rect", "name": f"{prefix}-card-{pi}", "x": margin + pi * 9.8, "y": CANVAS_H_CM + 1.2, "w": 9.0, "h": 3.5, "fill": card, "line": rule})
                layers.append({"kind": "text", "name": f"{prefix}-pt-{pi}", "text": detail_pts[pi][:120], "x": margin + pi * 9.8 + 0.4, "y": CANVAS_H_CM + 1.5, "w": 8.2, "h": 2.8, "font": bfont, "raw_font": raw_bf, "size": 11.0, "color": muted})

        else:
            # STAGE 4: Full Architectural Synthesis Panel (tight typography + all takeaways stacked)
            layers.append({"kind": "shape", "preset": "rect", "name": f"{prefix}-bgband", "x": 1.2, "y": 1.2, "w": CANVAS_W_CM - 2.4, "h": CANVAS_H_CM - 2.4, "fill": card, "line": rule})
            layers.append({"kind": "shape", "preset": "rect", "name": f"{prefix}-rule", "x": 2.2, "y": 4.8, "w": 6.2, "h": 0.14, "fill": acc1})
            layers.append({"kind": "text", "name": f"{prefix}-kicker", "text": f"SYNTHESIS // SLIDE {orig_idx:02d}", "x": 2.2, "y": 2.0, "w": 16.0, "h": 0.55, "font": "mono", "size": 9.5, "bold": True, "color": acc1})
            layers.append({"kind": "text", "name": f"{prefix}-title", "text": wrap_headline(headline_clean, 24, 2), "x": 2.2, "y": 2.7, "w": 19.5, "h": 1.9, "font": hfont, "raw_font": raw_hf, "size": 24.0, "bold": True, "color": ink})
            layers.append({"kind": "text", "name": f"{prefix}-num", "text": f"{orig_idx:02d}", "x": 25.5, "y": 1.8, "w": 6.0, "h": 2.8, "font": "display", "size": 56.0, "bold": True, "color": acc2, "align": "r"})
            w4, h4 = safe_pic_box(10.8, 10.6, stage_asset["aspect"])
            layers.append({"kind": "pic", "name": f"{prefix}-art", "asset": stage_asset, "x": 20.8, "y": 5.4, "w": w4, "h": h4, "border": rule})
            layers.append({"kind": "text", "name": f"{prefix}-sub", "text": lead_txt[:180], "x": 2.2, "y": 5.5, "w": 17.5, "h": 3.0, "font": bfont, "raw_font": raw_bf, "size": 13.5, "color": muted, "line_spacing": 1.35})
            for pi in range(min(3, len(detail_pts))):
                py_c = 9.0 + pi * 2.55
                layers.append({"kind": "shape", "preset": "rect", "name": f"{prefix}-card-{pi}", "x": 2.2, "y": py_c, "w": 17.5, "h": 2.2, "fill": panel, "line": acc1 if pi == 0 else rule})
                layers.append({"kind": "text", "name": f"{prefix}-pt-{pi}", "text": detail_pts[pi][:150], "x": 2.7, "y": py_c + 0.35, "w": 16.5, "h": 1.6, "font": bfont, "raw_font": raw_bf, "size": 11.5, "color": ink, "valign": "ctr", "animate": True})

        stages.append({"bg": bg, "dna": dna, "layers": layers})
    return stages


# ---------------------------------------------------------------------------
# Native Rich Slide Layer Deconstructor (lxml True XML Staging)
# ---------------------------------------------------------------------------

def _is_background_node(tag: str, box: tuple[int, int, int, int], text: str, cx_emu: int, cy_emu: int) -> bool:
    _, y, bw, bh = box
    if tag in ("pic", "grpSp", "graphicFrame"):
        return bw >= cx_emu * 0.85 and bh >= cy_emu * 0.85 and tag != "graphicFrame"
    clean_t = text.strip()
    if bw >= cx_emu * 0.72 and bh >= cy_emu * 0.72 and len(clean_t) < 20:
        return True
    if not clean_t and min(bw, bh) <= int(0.18 * EMU_PER_CM):
        return True
    if not clean_t and bh <= int(0.12 * cy_emu) and (y < int(0.08 * cy_emu) or y + bh > int(0.92 * cy_emu)):
        return True
    return False


def deconstruct_native_slide_stages(
    slide_bytes: bytes,
    orig_idx: int,
    cx_emu: int,
    cy_emu: int,
    dna: dict[str, Any],
    native_media: list[dict[str, Any]],
    deck_title: str,
    category: str,
    industry: str,
    force_n_stages: int | None = None,
) -> tuple[list[bytes], bool]:
    """
    Inspect `slide{i}.xml` layers:
      - If bare/plain (`<= 2` unstyled text shapes, zero images/groups/diagrams), return (None, True)
        so the caller builds generative DNA stages.
      - Otherwise deconstruct the original XML into 2-4 progressive Morph stages preserving
        exact native styling, embedded images, groups, and DNA palette coherence.
    """
    root = LET.fromstring(slide_bytes, PARSER)
    sp_tree = root.find(f".//{{{NS_P}}}spTree")
    if sp_tree is None:
        return [], True

    children = list(sp_tree)
    drawable_indices: list[int] = []
    bg_indices: list[int] = []
    content_items: list[tuple[int, str, tuple[int, int, int, int], str, int, list[str]]] = []
    has_rich_visual = False

    for ci, ch in enumerate(children):
        tag = ch.tag.split("}")[-1]
        if tag in ("nvGrpSpPr", "grpSpPr"):
            continue
        box = _extract_node_box(ch)
        if box is None:
            continue
        bx, by, bw, bh = box
        # Ignore elements already parked off-canvas (e.g. Morph pre-staging from original deck)
        if bx >= cx_emu - 36000 or bx + bw <= 36000 or by >= cy_emu - 36000 or by + bh <= 36000:
            continue
        if tag in ("pic", "grpSp", "graphicFrame"):
            has_rich_visual = True
        txt, max_sz, paras = _node_text_info(ch)
        if _is_background_node(tag, box, txt, cx_emu, cy_emu):
            bg_indices.append(ci)
            _set_cNvPr_name(ch, f"!!s{orig_idx:02d}-bg-{len(bg_indices):02d}")
        else:
            content_items.append((ci, tag, box, txt, max_sz, paras))
            drawable_indices.append(ci)

    # Check if slide has custom styled shapes (solid fills/borders beyond plain white box)
    if not has_rich_visual:
        styled_shapes = 0
        for ci, tag, box, txt, max_sz, paras in content_items:
            spPr = children[ci].find(f"{{{NS_P}}}spPr")
            sh, salpha = resolve_fill_hex(spPr, dna["scheme_map"])
            if sh and salpha > 30000 and color_dist(sh, dna["bg"]) > 18:
                styled_shapes += 1
        if styled_shapes == 0 and len(content_items) <= 2:
            # Bare plain text slide -> hand over to continuous generative DNA builder!
            return [], True

    if not content_items:
        _inject_bg_if_missing(root, dna["bg"])
        _ensure_unique_shape_ids(root)
        return [attach_morph_transition_lxml(root)], False

    # Rank content nodes: always prioritize real slide headline text, then primary focal visual
    def anchor_score(item: tuple[int, str, tuple[int, int, int, int], str, int, list[str]]) -> float:
        _, tag, box, txt, max_sz, _ = item
        x, y, bw, bh = box
        clean_t = txt.strip()
        s = 0.0
        if len(clean_t) >= 2:
            s += 220.0 + (max_sz / 25.0) + (65.0 if len(clean_t) <= 75 else 10.0)
            s += (1.0 - min(1.0, y / max(1, cy_emu))) * 40.0
        elif tag in ("pic", "grpSp"):
            s += 110.0 + (bw * bh) / max(1, cx_emu * cy_emu) * 90.0
        else:
            s += (bw * bh) / max(1, cx_emu * cy_emu) * 40.0
        return s

    ranked = sorted(content_items, key=anchor_score, reverse=True)
    anchor_ci = ranked[0][0]
    secondary_items = [it for it in content_items if it[0] != anchor_ci]
    secondary_items.sort(key=lambda it: (it[2][1] // int(1.2 * EMU_PER_CM), it[2][0]))

    # Keep headline + 1..2 primary visual framing shapes visible on Stage 1 (especially Cover slide_01)
    visual_frame_cis = {
        it[0] for it in sorted(
            [it for it in secondary_items if not it[3].strip() or it[1] in ("pic", "grpSp")],
            key=lambda it: it[2][2] * it[2][3],
            reverse=True,
        )[: (2 if orig_idx == 1 else 1)]
    }
    stageable_secondary = [it for it in secondary_items if it[0] not in visual_frame_cis]

    # Assign stable !!actor names onto base root once so Stage 1, 2, 3 match perfectly!
    _set_cNvPr_name(children[anchor_ci], f"!!s{orig_idx:02d}-layer-00")
    for sj, it in enumerate(secondary_items, start=1):
        _set_cNvPr_name(children[it[0]], f"!!s{orig_idx:02d}-layer-{sj:02d}")

    _inject_bg_if_missing(root, dna["bg"])
    _ensure_unique_shape_ids(root)

    total_words = sum(len(it[3].split()) for it in content_items)
    M = len(content_items)
    if force_n_stages is not None:
        n_stages = force_n_stages
    elif M <= 2 and total_words < 20:
        n_stages = 2
    elif M <= 4 and total_words < 42:
        n_stages = 3
    else:
        n_stages = 4

    out_slides: list[bytes] = []

    if n_stages >= 2 and stageable_secondary:
        # STAGE 1: Camera Anchor Framing (headline + key visual frame on stage; secondary layers staged off-canvas)
        s1_root = copy.deepcopy(root)
        s1_children = list(s1_root.find(f".//{{{NS_P}}}spTree"))
        _shift_node_xfrm(s1_children[anchor_ci], 0, 0, scale=1.06)
        for idx_s, it in enumerate(stageable_secondary):
            bx, by, bw, bh = it[2]
            dy_off = (cy_emu - by) + int(0.8 * EMU_PER_CM) + (idx_s % 3) * int(0.45 * EMU_PER_CM)
            _shift_node_xfrm(s1_children[it[0]], 0, dy_off, scale=0.92)
        out_slides.append(attach_morph_transition_lxml(s1_root))

    if n_stages >= 3 and len(stageable_secondary) >= 2:
        # STAGE 2: Wave 1 Unfold (first half glides onto stage cleanly; second wave enters next)
        s2_root = copy.deepcopy(root)
        s2_children = list(s2_root.find(f".//{{{NS_P}}}spTree"))
        half = max(1, len(stageable_secondary) // 2)
        _shift_node_xfrm(s2_children[anchor_ci], 0, -int(0.15 * EMU_PER_CM), scale=1.02)
        for it in stageable_secondary[half:]:
            bx, by, _, _ = it[2]
            dy_off = (cy_emu - by) + int(0.9 * EMU_PER_CM)
            _shift_node_xfrm(s2_children[it[0]], 0, dy_off, scale=0.95)
        out_slides.append(attach_morph_transition_lxml(s2_root))

    # STAGE 3 (Full Native Composition): Complete original slide in 100% its exact design & coordinates
    full_root = copy.deepcopy(root)
    out_slides.append(attach_morph_transition_lxml(full_root))

    if n_stages >= 4 and len(out_slides) < n_stages:
        # STAGE 4: Camera Accent / Synthesis Framing (zoom focal visual / headline + pull-out takeaway)
        s4_root = copy.deepcopy(root)
        s4_children = list(s4_root.find(f".//{{{NS_P}}}spTree"))
        _shift_node_xfrm(s4_children[anchor_ci], 0, int(0.28 * EMU_PER_CM), scale=1.07)
        for it in stageable_secondary[2:]:
            bx, by, _, _ = it[2]
            _shift_node_xfrm(s4_children[it[0]], cx_emu - bx + int(1.0 * EMU_PER_CM), 0, scale=0.90)
        out_slides.append(attach_morph_transition_lxml(s4_root))

    return out_slides, False


# ---------------------------------------------------------------------------
# Upgraded High-Fidelity OOXML Slide PNG Rasterizer (2x-Aware, CJK-Safe)
# ---------------------------------------------------------------------------

def _paste_with_shadow(base: Image.Image, overlay: Image.Image, x0: int, y0: int, shadow: bool) -> None:
    if shadow:
        sh = Image.new("RGBA", (overlay.width + 44, overlay.height + 44), (0, 0, 0, 0))
        alpha = overlay.split()[3]
        sh_fill = Image.new("RGBA", overlay.size, (0, 0, 0, 70))
        sh.paste(sh_fill, (22, 22), alpha)
        sh = sh.filter(ImageFilter.GaussianBlur(12))
        base.paste(sh, (x0 - 16, y0 - 10), sh)
    base.paste(overlay, (x0, y0), overlay)


def _open_asset_bytes(asset: dict[str, Any]) -> Image.Image:
    if "raw_bytes" in asset:
        return Image.open(io.BytesIO(asset["raw_bytes"])).convert("RGBA")
    return Image.open(asset["path"]).convert("RGBA")


def render_keyframe_png(spec: dict[str, Any], out_png: Path) -> None:
    """Render 2x-supersampled (1920x1080 -> 960x540) 1:1 preview matching generative DNA frame."""
    W, H = 1920, 1080
    px_per_cm = W / CANVAS_W_CM
    base = Image.new("RGBA", (W, H), hex_rgba(spec["bg"]))

    for lyr in spec["layers"]:
        x = int(round(lyr["x"] * px_per_cm))
        y = int(round(lyr["y"] * px_per_cm))
        w = max(2, int(round(lyr["w"] * px_per_cm)))
        h = max(2, int(round(lyr["h"] * px_per_cm)))
        if x >= W or y >= H or x + w <= 0 or y + h <= 0:
            continue

        if lyr["kind"] == "pic":
            try:
                pic = _open_asset_bytes(lyr["asset"]).resize((w, h), Image.Resampling.LANCZOS)
                if lyr.get("rounded"):
                    mask = Image.new("L", (w, h), 0)
                    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=24, fill=255)
                    pic.putalpha(mask)
                if lyr.get("border"):
                    dr = ImageDraw.Draw(pic)
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


def render_ooxml_slide_png_from_bytes(
    zin: zipfile.ZipFile,
    raw_xml: bytes,
    rel_map: dict[str, str],
    cx_emu: int,
    cy_emu: int,
    dna: dict[str, Any],
) -> bytes:
    """High-fidelity pure-Pillow rasterizer (960x540) handling groups, schemeClr, shapes, and CJK."""
    W, H = 960, 540
    names_set = set(zin.namelist())
    root = LET.fromstring(raw_xml, PARSER)
    scheme_map = dna["scheme_map"]

    bg_hex = dna["bg"]
    bg_pr = root.find(f".//{{{NS_P}}}bg/{{{NS_P}}}bgPr")
    if bg_pr is not None:
        bh, balpha = resolve_fill_hex(bg_pr, scheme_map)
        if bh and balpha > 40000:
            bg_hex = bh

    img = Image.new("RGBA", (W, H), hex_rgba(bg_hex))

    # Optional picture slide background
    if bg_pr is not None:
        blip_bg = bg_pr.find(f".//{{{NS_A}}}blip")
        if blip_bg is not None:
            emb = blip_bg.attrib.get(f"{{{NS_R}}}embed") or ""
            mp = rel_map.get(emb, "")
            if mp in names_set:
                try:
                    with Image.open(io.BytesIO(zin.read(mp))) as bim:
                        bg_im = bim.convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)
                    img.paste(bg_im, (0, 0), bg_im)
                except Exception:
                    pass

    sx = W / max(1, cx_emu)
    sy = H / max(1, cy_emu)
    smin = min(sx, sy)
    default_txt_hex = dna["ink"]

    def draw_node(node: LET._Element, map_fn: Any) -> None:
        tag = node.tag.split("}")[-1]
        if tag == "grpSp":
            grpPr = node.find(f"{{{NS_P}}}grpSpPr")
            gxf = grpPr.find(f"{{{NS_A}}}xfrm") if grpPr is not None else None
            if gxf is not None:
                goff = gxf.find(f"{{{NS_A}}}off")
                gext = gxf.find(f"{{{NS_A}}}ext")
                coff = gxf.find(f"{{{NS_A}}}chOff")
                cext = gxf.find(f"{{{NS_A}}}chExt")
                if None not in (goff, gext, coff, cext):
                    gx, gy = float(goff.attrib.get("x", 0)), float(goff.attrib.get("y", 0))
                    gw, gh = max(1.0, float(gext.attrib.get("cx", 1))), max(1.0, float(gext.attrib.get("cy", 1)))
                    cx0, cy0 = float(coff.attrib.get("x", 0)), float(coff.attrib.get("y", 0))
                    cw0, ch0 = max(1.0, float(cext.attrib.get("cx", 1))), max(1.0, float(cext.attrib.get("cy", 1)))

                    def child_map(nx: float, ny: float, nw: float, nh: float) -> tuple[float, float, float, float]:
                        mx = gx + (nx - cx0) * (gw / cw0)
                        my = gy + (ny - cy0) * (gh / ch0)
                        mw = nw * (gw / cw0)
                        mh = nh * (gh / ch0)
                        return map_fn(mx, my, mw, mh)

                    for ch in list(node):
                        if ch.tag.split("}")[-1] in ("sp", "pic", "grpSp", "cxnSp"):
                            draw_node(ch, child_map)
                    return

        box = _extract_node_box(node)
        if box is None:
            return
        ux, uy, uw, uh = map_fn(*box)
        x0 = int(round(ux * sx))
        y0 = int(round(uy * sy))
        bw = max(2, int(round(uw * sx)))
        bh = max(2, int(round(uh * sy)))
        if x0 >= W or y0 >= H or x0 + bw <= 0 or y0 + bh <= 0:
            return

        if tag == "pic":
            blip = node.find(f".//{{{NS_A}}}blip")
            if blip is not None:
                emb = blip.attrib.get(f"{{{NS_R}}}embed") or ""
                mp = rel_map.get(emb, "")
                if mp in names_set:
                    try:
                        with Image.open(io.BytesIO(zin.read(mp))) as pim:
                            p_rgba = pim.convert("RGBA").resize((bw, bh), Image.Resampling.LANCZOS)
                        img.paste(p_rgba, (x0, y0), p_rgba)
                    except Exception:
                        pass
            return

        if tag in ("sp", "cxnSp"):
            spPr = node.find(f"{{{NS_P}}}spPr")
            rot_deg = 0.0
            if spPr is not None:
                xf_el = spPr.find(f"{{{NS_A}}}xfrm")
                if xf_el is not None and xf_el.attrib.get("rot"):
                    rot_deg = int(xf_el.attrib["rot"]) / 60000.0

                fill_rgba = None
                if spPr.find(f"{{{NS_A}}}noFill") is None:
                    fh, falpha = resolve_fill_hex(spPr, scheme_map)
                    if fh:
                        fill_rgba = hex_rgba(fh, falpha)

                ln_rgba = None
                ln_w = 1
                ln_el = spPr.find(f"{{{NS_A}}}ln")
                if ln_el is not None and ln_el.find(f"{{{NS_A}}}noFill") is None:
                    lh, lalpha = resolve_fill_hex(ln_el, scheme_map)
                    if lh:
                        ln_rgba = hex_rgba(lh, lalpha)
                        ln_w = max(1, int(round(int(ln_el.attrib.get("w", 12700)) * smin)))

                prst_el = spPr.find(f"{{{NS_A}}}prstGeom")
                prst = prst_el.attrib.get("prst", "rect") if prst_el is not None else "rect"

                if fill_rgba or ln_rgba:
                    sh_im = Image.new("RGBA", (bw + 4, bh + 4), (0, 0, 0, 0))
                    sdr = ImageDraw.Draw(sh_im, "RGBA")
                    bx_e, by_e = bw + 1, bh + 1
                    if prst in ("ellipse", "oval"):
                        sdr.ellipse([2, 2, bx_e, by_e], fill=fill_rgba, outline=ln_rgba, width=ln_w)
                    elif prst == "roundRect":
                        rad = max(4, min(28, min(bw, bh) // 4))
                        sdr.rounded_rectangle([2, 2, bx_e, by_e], radius=rad, fill=fill_rgba, outline=ln_rgba, width=ln_w)
                    elif prst in ("line", "straightConnector1"):
                        sdr.line([(2, 2), (bx_e, by_e)], fill=ln_rgba or fill_rgba, width=max(1, ln_w))
                    elif prst == "triangle":
                        sdr.polygon([(bw // 2 + 2, 2), (bx_e, by_e), (2, by_e)], fill=fill_rgba, outline=ln_rgba)
                    elif prst == "diamond":
                        sdr.polygon([(bw // 2 + 2, 2), (bx_e, bh // 2 + 2), (bw // 2 + 2, by_e), (2, bh // 2 + 2)], fill=fill_rgba, outline=ln_rgba)
                    else:
                        sdr.rectangle([2, 2, bx_e, by_e], fill=fill_rgba, outline=ln_rgba, width=ln_w)
                    if abs(rot_deg) > 1.0:
                        sh_im = sh_im.rotate(-rot_deg, resample=Image.Resampling.BICUBIC, expand=True)
                        rx = x0 + bw // 2 - sh_im.width // 2
                        ry = y0 + bh // 2 - sh_im.height // 2
                        img.paste(sh_im, (rx, ry), sh_im)
                    else:
                        img.paste(sh_im, (x0 - 2, y0 - 2), sh_im)

            txBody = node.find(f"{{{NS_P}}}txBody")
            if txBody is not None:
                bodyPr = txBody.find(f"{{{NS_A}}}bodyPr")
                valgn = bodyPr.attrib.get("anchor", "t") if bodyPr is not None else "t"
                lines_to_draw: list[tuple[str, str, int, bool, str]] = []
                for p_el in txBody.findall(f"{{{NS_A}}}p"):
                    pPr = p_el.find(f"{{{NS_A}}}pPr")
                    algn = pPr.attrib.get("algn", "l") if pPr is not None else "l"
                    def_rPr = pPr.find(f"{{{NS_A}}}defRPr") if pPr is not None else None
                    runs: list[str] = []
                    first_sz = int(def_rPr.attrib["sz"]) if (def_rPr is not None and def_rPr.attrib.get("sz", "").isdigit()) else 1600
                    first_clr = default_txt_hex
                    first_bold = False
                    first_role = dna["body_font"]
                    for r_el in p_el.findall(f"{{{NS_A}}}r"):
                        t_el = r_el.find(f"{{{NS_A}}}t")
                        if t_el is not None and t_el.text:
                            runs.append(html.unescape(t_el.text))
                            rPr = r_el.find(f"{{{NS_A}}}rPr")
                            if rPr is not None and len(runs) == 1:
                                if rPr.attrib.get("sz", "").isdigit():
                                    first_sz = int(rPr.attrib["sz"])
                                first_bold = rPr.attrib.get("b") == "1"
                                ch_res, _ = resolve_fill_hex(rPr, scheme_map)
                                if ch_res:
                                    first_clr = ch_res
                                fel = rPr.find(f"{{{NS_A}}}latin")
                                if fel is not None and fel.attrib.get("typeface"):
                                    first_role = _classify_font_role(fel.attrib["typeface"])
                    ptxt = re.sub(r"\s+", " ", "".join(runs)).strip()
                    if not ptxt or "AVANT //" in ptxt or "SPEC //" in ptxt:
                        continue
                    px_sz = max(9, min(58, int(round((first_sz / 100.0) * (smin * EMU_PER_CM / 28.3465) * 1.1))))
                    lines_to_draw.append((ptxt, first_clr, px_sz, first_bold, first_role))

                if lines_to_draw:
                    tdr = ImageDraw.Draw(img, "RGBA")
                    wrapped_items: list[tuple[str, Any, str, int, str]] = []
                    total_h = 0
                    for ptxt, clr, px_sz, bold, frole in lines_to_draw:
                        role_eff = "sans_bold" if bold and frole == "sans" else ("serif" if frole == "serif" else ("mono" if frole == "mono" else "sans"))
                        font = load_ttf(role_eff, px_sz, ptxt)
                        cur = ""
                        for word in ptxt.split(" "):
                            test = f"{cur} {word}".strip()
                            if tdr.textlength(test, font=font) <= max(36, bw - 8) or not cur:
                                cur = test
                            else:
                                wrapped_items.append((cur, font, clr, int(px_sz * 1.18), algn))
                                total_h += int(px_sz * 1.18)
                                cur = word
                        if cur:
                            wrapped_items.append((cur, font, clr, int(px_sz * 1.24), algn))
                            total_h += int(px_sz * 1.24)

                    cur_y = y0 + 4 if valgn == "t" else (y0 + max(2, (bh - total_h) // 2) if valgn == "ctr" else y0 + max(2, bh - total_h))
                    for line_str, font, clr, step_h, algn in wrapped_items:
                        if cur_y > y0 + bh - 2 or cur_y >= H:
                            break
                        tw = tdr.textlength(line_str, font=font)
                        lx = x0 + 4 if algn == "l" else (x0 + max(2, (bw - tw) / 2) if algn == "ctr" else x0 + max(2, bw - tw - 4))
                        tdr.text((lx, cur_y), line_str, font=font, fill=hex_rgba(clr))
                        cur_y += step_h

    sp_tree = root.find(f".//{{{NS_P}}}spTree")
    if sp_tree is not None:
        for child in list(sp_tree):
            if child.tag.split("}")[-1] in ("sp", "pic", "grpSp", "cxnSp"):
                draw_node(child, lambda x, y, w, h: (x, y, w, h))

    q = img.convert("RGB").quantize(colors=256, method=Image.Quantize.FASTOCTREE)
    buf = io.BytesIO()
    q.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Core Per-Deck Orchestrator (`expand_single_pptx`)
# ---------------------------------------------------------------------------

def _load_rel_map(zin: zipfile.ZipFile, slide_part: str) -> tuple[dict[str, str], str]:
    rels_part = f"ppt/slides/_rels/{Path(slide_part).name}.rels"
    rel_map: dict[str, str] = {}
    rels_xml = ""
    if rels_part in zin.namelist():
        rels_xml = zin.read(rels_part).decode("utf-8", "ignore")
        try:
            rroot = LET.fromstring(rels_xml.encode("utf-8"), PARSER)
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
    return rel_map, rels_xml


def expand_single_pptx(
    src_path: Path,
    dst_path: Path,
    slug: str,
    deck_idx: int,
    meta_info: dict[str, Any],
    sync_previews: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    with zipfile.ZipFile(src_path, "r") as zin:
        names = zin.namelist()
        names_set = set(names)
        if "ppt/av_organic_v2.marker" in names_set and not force:
            return {"slug": slug, "status": "already-organic-v2"}

        pres_xml = zin.read("ppt/presentation.xml").decode("utf-8", "ignore")
        pres_rels = zin.read("ppt/_rels/presentation.xml.rels").decode("utf-8", "ignore")
        ct_xml = zin.read("[Content_Types].xml").decode("utf-8", "ignore")

        rel_root = LET.fromstring(pres_rels.encode("utf-8"), PARSER)
        rid_to_target = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rel_root if rel.attrib.get("Id")}

        # Recover ordered original slide*.xml paths (idempotent even when re-running --force)
        orig_slide_parts: list[str] = []
        sld_ids_raw = re.findall(r"<p:sldId\b[^>]*/?\s*>", pres_xml)
        for tag in sld_ids_raw:
            mrid = re.search(r'\br:id="([^"]+)"', tag)
            if mrid:
                t_str = rid_to_target.get(mrid.group(1), "").lstrip("/")
                if t_str and not t_str.startswith("ppt/"):
                    t_str = "ppt/" + t_str
                if t_str and "av_slide_" not in t_str and t_str in names_set:
                    orig_slide_parts.append(t_str)

        if not orig_slide_parts:
            orig_slide_parts = sorted(
                [n for n in names if re.match(r"^ppt/slides/slide\d+\.xml$", n)],
                key=lambda s: int("".join(filter(str.isdigit, Path(s).stem)) or 0),
            )

        k = len(orig_slide_parts)
        if k == 0:
            return {"slug": slug, "status": "empty-skip", "family": "Editorial Archive"}

        cx_emu, cy_emu = CANVAS_W_EMU, CANVAS_H_EMU
        m_sz = re.search(r'<p:sldSz\b[^>]*cx="(\d+)"[^>]*cy="(\d+)"', pres_xml)
        if m_sz:
            cx_emu, cy_emu = int(m_sz.group(1)), int(m_sz.group(2))

        title = clean_title_for_slide(meta_info.get("title") or src_path.stem)
        category = meta_info.get("category") or "Strategy"
        industry = meta_info.get("industry") or "Enterprise"

        fallback_fam = pick_design_family(slug, category, industry, deck_idx)
        dna = extract_original_dna(zin, slug, orig_slide_parts, cx_emu, cy_emu, fallback_fam)
        native_media = extract_native_deck_media(zin, dna["card"])

        sample_target = next(iter(rid_to_target.values()), "slides/slide1.xml")
        uses_abs_ppt = sample_target.startswith("/ppt/")
        layouts = sorted([n for n in names if re.match(r"^ppt/slideLayouts/slideLayout\d+\.xml$", n)])
        layout_target_rel = "../slideLayouts/" + Path(layouts[-1] if layouts else "ppt/slideLayouts/slideLayout1.xml").name

        _, s1_rels_xml = _load_rel_map(zin, orig_slide_parts[0])
        if s1_rels_xml:
            m_lay = re.search(r'Type="[^"]*slideLayout"[^>]*Target="([^"]+)"', s1_rels_xml) or re.search(r'Target="([^"]*slideLayout[^"]*)"', s1_rels_xml)
            if m_lay:
                layout_target_rel = m_lay.group(1)

        existing_rids = set(rid_to_target.keys())
        max_sld_num = max([int(m.group(1)) for m in re.finditer(r'\bid="(\d+)"', pres_xml)] + [255])

        # Determine which slides get full multi-stage expansion when deck is huge (K > 24)
        new_slides_bytes: dict[str, bytes] = {}
        new_slide_rels_bytes: dict[str, bytes] = {}
        new_media_bytes: dict[str, bytes] = {}
        new_pres_rels_xml: list[str] = []
        new_ct_overrides: list[str] = []
        final_sld_id_xml: list[str] = []
        preview_jobs: list[tuple[int, str, Any]] = []

        expand_set: set[int]
        if k <= 24:
            expand_set = set(range(1, k + 1))
        else:
            step = max(2, k // 18)
            expand_set = {1, k} | set(range(1, k + 1, step))

        slide_seq = 0
        for orig_i, sp in enumerate(orig_slide_parts, start=1):
            raw_sp = zin.read(sp)
            rel_map, raw_rels_xml = _load_rel_map(zin, sp)

            should_expand = orig_i in expand_set
            # Minimum stage boost for tiny decks (< 5 original slides) so final count >= 11 organically
            min_stages = 3 if (k <= 4 and should_expand) else None

            stage_xmls, use_generative = deconstruct_native_slide_stages(
                raw_sp, orig_i, cx_emu, cy_emu, dna, native_media, title, category, industry,
                force_n_stages=min_stages if should_expand else 1,
            )

            if not use_generative:
                # Emit deconstructed authentic XML stages inheriting native .rels (minus notesSlide)
                clean_rels = re.sub(r'<Relationship\b[^>]*Type="[^"]*notesSlide[^"]*"[^>]*/>\s*', "", raw_rels_xml)
                if not clean_rels:
                    clean_rels = (
                        '<?xml version="1.0" encoding="utf-8"?>'
                        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                        f'<Relationship Id="rId1" Type="{NS_R}/slideLayout" Target="{layout_target_rel}"/></Relationships>'
                    )
                for stage_bytes in stage_xmls:
                    slide_seq += 1
                    fname = f"av_slide_{slide_seq:03d}.xml"
                    new_slides_bytes[f"ppt/slides/{fname}"] = stage_bytes
                    new_slide_rels_bytes[f"ppt/slides/_rels/{fname}.rels"] = clean_rels.encode("utf-8")
                    preview_jobs.append((slide_seq, "xml", (stage_bytes, rel_map)))
            else:
                # Bare/plain slide -> build progressive generative DNA stages in authentic deck palette
                root_tmp = LET.fromstring(raw_sp, PARSER)
                paras: list[str] = []
                for p in root_tmp.iter(f"{{{NS_A}}}p"):
                    txt = re.sub(r"\s+", " ", "".join(html.unescape(t.text) for t in p.iter(f"{{{NS_A}}}t") if t.text)).strip()
                    if txt:
                        paras.append(txt)
                hl = paras[0] if paras else f"{title} — Stage {orig_i:02d}"
                pts = paras[1:] if len(paras) > 1 else [hl]
                n_gen = min_stages or (4 if (len(" ".join(paras).split()) >= 36 or len(pts) >= 4) else (3 if len(pts) >= 2 else 2))
                if not should_expand:
                    n_gen = 1

                gen_specs = build_generative_dna_stages(
                    orig_i, hl, pts, dna, native_media, title, category, industry, n_gen
                )
                for st_i, gspec in enumerate(gen_specs):
                    slide_seq += 1
                    fname = f"av_slide_{slide_seq:03d}.xml"
                    pic_rids: dict[str, str] = {}
                    rels_extra: list[str] = []
                    for lyr in gspec["layers"]:
                        if lyr["kind"] == "pic":
                            mname = f"av_art_{slide_seq:03d}_{len(pic_rids)+1}.jpg"
                            new_media_bytes[f"ppt/media/{mname}"] = lyr["asset"]["raw_bytes"]
                            rid_k = f"rId{len(pic_rids)+2}"
                            pic_rids[lyr["name"]] = rid_k
                            rels_extra.append(f'<Relationship Id="{rid_k}" Type="{NS_R}/image" Target="../media/{mname}"/>')
                    s_bytes = build_generative_dna_ooxml(gspec, cx_emu, cy_emu, pic_rids)
                    new_slides_bytes[f"ppt/slides/{fname}"] = s_bytes
                    new_slide_rels_bytes[f"ppt/slides/_rels/{fname}.rels"] = (
                        '<?xml version="1.0" encoding="utf-8"?>'
                        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                        f'<Relationship Id="rId1" Type="{NS_R}/slideLayout" Target="{layout_target_rel}"/>'
                        + "".join(rels_extra)
                        + "</Relationships>"
                    ).encode("utf-8")
                    preview_jobs.append((slide_seq, "spec", gspec))

        # Populate presentation.xml.rels, Content_Types, and final unified single-hand <p:sldIdLst>
        for seq_num in range(1, slide_seq + 1):
            fname = f"av_slide_{seq_num:03d}.xml"
            max_sld_num += 1
            new_rid = f"rIdAv{seq_num:03d}"
            while new_rid in existing_rids:
                new_rid += "x"
            existing_rids.add(new_rid)
            target_val = f"/ppt/slides/{fname}" if uses_abs_ppt else f"slides/{fname}"
            new_pres_rels_xml.append(f'<Relationship Id="{new_rid}" Type="{NS_R}/slide" Target="{target_val}"/>')
            new_ct_overrides.append(
                f'<Override PartName="/ppt/slides/{fname}" '
                f'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            )
            final_sld_id_xml.append(f'<p:sldId id="{max_sld_num}" r:id="{new_rid}"/>')

        new_pres_xml = re.sub(
            r"<p:sldIdLst\b[^>]*>.*?</p:sldIdLst>",
            f'<p:sldIdLst xmlns:r="{NS_R}">{"".join(final_sld_id_xml)}</p:sldIdLst>',
            pres_xml,
            count=1,
            flags=re.S,
        )
        LET.fromstring(new_pres_xml.encode("utf-8"), PARSER)

        cleaned_pres_rels = re.sub(r'<Relationship\b[^>]*Target="[^"]*av_slide_[^"]*"[^>]*/>\s*', "", pres_rels)
        cleaned_pres_rels = cleaned_pres_rels.replace("</Relationships>", f"{''.join(new_pres_rels_xml)}</Relationships>")
        LET.fromstring(cleaned_pres_rels.encode("utf-8"), PARSER)

        cleaned_ct = re.sub(r'<Override\b[^>]*PartName="/ppt/slides/av_slide_[^"]*"[^>]*/>\s*', "", ct_xml)
        if not re.search(r'Extension="jpe?g"', cleaned_ct, flags=re.IGNORECASE):
            cleaned_ct = cleaned_ct.replace("</Types>", '<Default Extension="jpg" ContentType="image/jpeg"/></Types>')
        if not re.search(r'Extension="png"', cleaned_ct, flags=re.IGNORECASE):
            cleaned_ct = cleaned_ct.replace("</Types>", '<Default Extension="png" ContentType="image/png"/></Types>')
        cleaned_ct = cleaned_ct.replace("</Types>", f"{''.join(new_ct_overrides)}</Types>")
        LET.fromstring(cleaned_ct.encode("utf-8"), PARSER)

        # Render clean 1:1 previews straight from our newly generated stages (never stale PNGs)
        if sync_previews:
            max_prev = 16 if (CURATED_OUT_DIR in dst_path.parents or "curated" in slug or slug.startswith(("corpus-", "style-"))) else 8
            preview_dir = PREVIEWS_DIR / slug
            preview_dir.mkdir(parents=True, exist_ok=True)
            for old_png in preview_dir.glob("slide_*.png"):
                old_png.unlink(missing_ok=True)
            for seq_num, pkind, pdata in preview_jobs:
                if seq_num > max_prev:
                    break
                out_png = preview_dir / f"slide_{seq_num:02d}.png"
                if pkind == "spec":
                    render_keyframe_png(pdata, out_png)
                else:
                    stage_bytes, rmap = pdata
                    out_png.write_bytes(render_ooxml_slide_png_from_bytes(zin, stage_bytes, rmap, cx_emu, cy_emu, dna))

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = dst_path.with_suffix(".exp.tmp.pptx")
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
            skip_prefixes = ("ppt/slides/av_slide_", "ppt/slides/_rels/av_slide_", "ppt/media/av_art_", "ppt/av_expanded_v1.json")
            for info in zin.infolist():
                if any(info.filename.startswith(sp_f) for sp_f in skip_prefixes):
                    continue
                raw = zin.read(info.filename)
                if info.filename == "ppt/presentation.xml":
                    raw = new_pres_xml.encode("utf-8")
                elif info.filename == "ppt/_rels/presentation.xml.rels":
                    raw = cleaned_pres_rels.encode("utf-8")
                elif info.filename == "[Content_Types].xml":
                    raw = cleaned_ct.encode("utf-8")
                zi = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(zi, raw)

            for part_name, pbytes in {**new_slides_bytes, **new_slide_rels_bytes, **new_media_bytes}.items():
                zout.writestr(part_name, pbytes)

        if not zipfile.is_zipfile(tmp_path):
            tmp_path.unlink(missing_ok=True)
            raise RuntimeError(f"Output invalid zip for {slug}")
        shutil.move(str(tmp_path), str(dst_path))

    return {
        "slug": slug,
        "status": "expanded",
        "orig": k,
        "final": slide_seq,
        "family": dna["label"],
        "family_id": dna["id"],
        "bg": dna["bg"],
        "is_monochrome": dna["is_monochrome"],
    }


def _curated_worker(task: tuple[dict[str, Any], int, bool]) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
    item, idx, force = task
    slug = item["slug"]
    src = Path(item["path"])
    dst = CURATED_OUT_DIR / f"{slug}.pptx"
    try:
        res = expand_single_pptx(src, dst, slug, deck_idx=idx, meta_info=item, sync_previews=True, force=force)
        return item, res, None
    except Exception as exc:
        return item, None, str(exc)


def run_curated(force: bool, family_map: dict[str, dict[str, str]], only_slugs: set[str] | None = None) -> None:
    CURATED_OUT_DIR.mkdir(parents=True, exist_ok=True)
    curated = json.loads(CURATED_INDEX.read_text(encoding="utf-8"))
    curated.sort(key=lambda x: (0 if x.get("slug") == "modnexus-global-modding-union" else 1))

    family_map["modnexus-global-modding-union"] = {"id": "modnexus_flagship", "label": "MODNEXUS Flagship"}
    tasks = []
    for idx, item in enumerate(curated):
        slug = item["slug"]
        if slug == "modnexus-global-modding-union":
            continue
        if only_slugs and slug not in only_slugs:
            continue
        if not Path(item["path"]).exists():
            print(f"  [SKIP MISSING] {slug}: {item['path']}")
            continue
        tasks.append((item, idx, force))

    print(f"[CURATED] Processing {len(tasks)} curated decks via DNA-Preserving Organic Choreography (MODNEXUS #1 untouched)...", flush=True)
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
            if only_slugs:
                print(f"  [TEST CURATED] {slug} -> {res}", flush=True)

    CURATED_INDEX.write_text(json.dumps(curated, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[CURATED COMPLETE] Processed {done_cnt} curated decks -> {CURATED_INDEX}", flush=True)


def _scraped_worker(task: tuple[str, int, dict[str, Any], bool]) -> tuple[str, str, dict[str, Any] | None, str | None]:
    p_str, deck_idx, meta_info, force = task
    p = Path(p_str)
    slug = slugify(p.stem)
    try:
        res = expand_single_pptx(p, p, slug, deck_idx=deck_idx, meta_info=meta_info, sync_previews=True, force=force)
        return p.name, slug, res, None
    except Exception as exc:
        return p.name, slug, None, str(exc)


def run_scraped(force: bool, limit: int, family_map: dict[str, dict[str, str]]) -> None:
    meta_map = json.loads(SCRAPED_META.read_text(encoding="utf-8")) if SCRAPED_META.exists() else {}
    files = sorted(SCRAPED_DIR.glob("*.pptx"))
    if limit > 0:
        files = files[:limit]
    total = len(files)
    done_cnt = skip_cnt = err_cnt = 0

    tasks = []
    for idx, p in enumerate(files):
        meta = meta_map.get(p.name, {}) if isinstance(meta_map, dict) else {}
        meta_info = {
            "title": meta.get("inferred_title") or meta.get("title") or p.stem,
            "category": meta.get("inferred_category") or meta.get("category") or "Strategy",
            "industry": meta.get("industry") or "Enterprise",
        }
        tasks.append((str(p), idx + 100, meta_info, force))

    print(f"[SCRAPED] Processing {total} decks via DNA-Preserving Organic Choreography (8 workers)...", flush=True)
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
    parser.add_argument("--slugs", nargs="*", default=None, help="Optional list of curated slugs to rebuild for fast testing")
    args = parser.parse_args()

    family_map: dict[str, dict[str, str]] = (
        json.loads(FAMILY_MAP_PATH.read_text(encoding="utf-8")) if FAMILY_MAP_PATH.exists() else {}
    )

    if args.mode in ("curated", "all"):
        run_curated(force=args.force, family_map=family_map, only_slugs=set(args.slugs) if args.slugs else None)
    if args.mode in ("scraped", "all") and not args.slugs:
        run_scraped(force=args.force, limit=args.limit, family_map=family_map)

    FAMILY_MAP_PATH.write_text(json.dumps(family_map, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[DONE] Saved design family registry ({len(family_map)} entries) -> {FAMILY_MAP_PATH}", flush=True)


if __name__ == "__main__":
    main()
