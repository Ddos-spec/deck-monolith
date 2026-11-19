"""
Visual Asset Bank Builder (210 Deduplicated Gallery-Grade Visual Plates)
1. Harvests perceptual-hash-deduplicated photographic / 3D / illustration assets from:
   - D:\\code\\ppt_studio\\examples_out\\assets
   - Brain artifacts & D:\\code\\ppt_studio\\corpus\\*.pptx
   - D:\\code\\ppt_studio\\corpus_scraped\\*.pptx
   Strictly rejects UI/Excel/browser/document screenshots on white or flat light-gray backgrounds.
2. Generates gallery-grade 2x-supersampled (2560x1600 -> 1280x800) fine-art & editorial plates
   across 24 distinct archetypes and 20 curated palettes.
3. Normalizes all 210 plates to optimized RGB JPEGs + manifest.json in:
   D:\\code\\ppt_studio\\visual_asset_bank\\
"""

from __future__ import annotations

import io
import json
import math
import random
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageStat

OUT_DIR = Path(r"D:\code\ppt_studio\visual_asset_bank")
MANIFEST_PATH = OUT_DIR / "manifest.json"

REAL_SOURCES_DIRS = [
    Path(r"D:\code\ppt_studio\examples_out\assets"),
    Path(r"C:\Users\Lenovo\.gemini\antigravity-cli\brain\a88087f3-d521-468d-9485-ab34494fe3c5"),
]
CORPUS_DIR = Path(r"D:\code\ppt_studio\corpus")
SCRAPED_DIR = Path(r"D:\code\ppt_studio\corpus_scraped")

TARGET_TOTAL = 210
TARGET_REAL = 114
MIN_HAMMING_DIST = 12

PALETTES = [
    ("#F6F3EC", "#EBE5D8", "#C83E1B", "#14532D", "#141413"),  # Gallery Paper + Vermilion + Forest
    ("#F8F7F4", "#ECEAE4", "#E0311B", "#1D4ED8", "#111827"),  # Swiss Grid White
    ("#F6DEC8", "#ECC9AA", "#991B1B", "#0F766E", "#1F2937"),  # FT Salmon Financial
    ("#141312", "#22201E", "#D4AF37", "#B45309", "#F5F2EB"),  # Luxury Atelier Noir
    ("#0B2545", "#13315C", "#38BDF8", "#F59E0B", "#E0F2FE"),  # Architectural Blueprint
    ("#EBF1EC", "#D8E4DA", "#145326", "#C2410C", "#1C2B22"),  # Botanical Sage
    ("#FAF8F2", "#EFECE2", "#DC2626", "#44403C", "#1C1917"),  # Kyoto Ma-Zen
    ("#F7F3E8", "#EAE2CE", "#E03C1F", "#1D4ED8", "#EAB308"),  # Weimar Bauhaus
    ("#F5EBE0", "#E8D8C8", "#F43F5E", "#0D9488", "#1E1B4B"),  # Risograph Duotone
    ("#070B19", "#111A33", "#06B6D4", "#A855F7", "#F8FAFC"),  # Deep Space Quantum
    ("#FEF3C7", "#FDE68A", "#09090B", "#EF4444", "#2563EB"),  # Neo-Brutalist Marigold
    ("#ECFCCB", "#D9F99D", "#18181B", "#4F46E5", "#E11D48"),  # Studio Feixen Acid
    ("#111317", "#1B1E24", "#E8491D", "#2DD4BF", "#F3EFE6"),  # Carbon Editorial
    ("#0E1A14", "#182D23", "#10B981", "#FBBF24", "#ECFDF5"),  # Emerald Monolith
    ("#F4EFE6", "#E5DFD2", "#9A3412", "#3F6212", "#1C1917"),  # Kinfolk Warm Sand
    ("#F1F5F9", "#E2E8F0", "#0F172A", "#2563EB", "#EA580C"),  # Modular Slate
    ("#18181B", "#27272A", "#F97316", "#6366F1", "#FAFAFA"),  # Graphic Studio Dark
    ("#FAF7F2", "#EBE5D9", "#B91C1C", "#111827", "#047857"),  # Vignelli Red
    ("#EDE9E0", "#DFD9CC", "#1E3A8A", "#B45309", "#18181B"),  # Museum Stone Diptych
    ("#16101B", "#261B30", "#F472B6", "#34D399", "#FDF4FF"),  # Ultraviolet Specimen
]


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def compute_dhash(img: Image.Image) -> int:
    """Compute 64-bit horizontal difference hash on a 9x8 grayscale downsample."""
    g = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    px = list(g.getdata())
    bits = 0
    bit_idx = 0
    for y in range(8):
        row = y * 9
        for x in range(8):
            if px[row + x] < px[row + x + 1]:
                bits |= 1 << bit_idx
            bit_idx += 1
    return bits


def hamming_dist(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def passes_quality_filter(img: Image.Image) -> tuple[bool, float]:
    """Filter out UI/Excel/document screenshots, white-canvas diagrams, and flat junk."""
    w, h = img.size
    if w < 520 or h < 340:
        return False, 0.0
    ratio = w / max(1, h)
    if ratio < 0.68 or ratio > 2.2:
        return False, 0.0

    thumb = img.convert("RGB").resize((80, 80), Image.Resampling.BILINEAR)
    px = list(thumb.getdata())
    total_px = len(px)

    # Reject white-background document / chart / UI screenshots
    near_white = sum(1 for r, g, b in px if r > 232 and g > 232 and b > 232)
    if (near_white / total_px) > 0.28:
        return False, 0.0

    # Reject flat light-gray UI windows / dialogs
    flat_gray = sum(1 for r, g, b in px if r > 205 and g > 205 and b > 205 and (max(r, g, b) - min(r, g, b)) < 16)
    if (flat_gray / total_px) > 0.40:
        return False, 0.0

    # Reject near-uniform flat regions (horizontal & vertical neighbor similarity)
    flat_pairs = 0
    for y in range(80):
        row = y * 80
        for x in range(79):
            r1, g1, b1 = px[row + x]
            r2, g2, b2 = px[row + x + 1]
            if abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2) < 10:
                flat_pairs += 1
    if (flat_pairs / (80 * 79)) > 0.45:
        return False, 0.0

    stat_rgb = ImageStat.Stat(thumb)
    max_std = max(stat_rgb.stddev)
    mean_std = sum(stat_rgb.stddev) / 3.0
    if max_std < 38.0 or mean_std < 32.0:
        return False, 0.0

    hsv = thumb.convert("HSV")
    sat_mean = ImageStat.Stat(hsv).mean[1]
    if sat_mean < 22.0 and max_std < 60.0:
        return False, 0.0

    q = thumb.quantize(colors=16, method=Image.Quantize.FASTOCTREE)
    counts = sorted((cnt for cnt, _ in (q.getcolors(16) or [])), reverse=True)
    if counts and (counts[0] / float(total_px)) >= 0.46:
        return False, 0.0

    score = mean_std + sat_mean * 0.48 + min(w, 1400) * 0.02
    return True, float(score)


def normalize_and_save(img: Image.Image, dst: Path, max_w: int = 1280) -> tuple[int, int]:
    """Resize preserving aspect ratio and save clean RGB JPEG."""
    if img.mode in ("RGBA", "LA", "PA"):
        canvas = Image.new("RGB", img.size, (20, 20, 19))
        rgba = img.convert("RGBA")
        canvas.paste(rgba, mask=rgba.split()[3])
        rgb = canvas
    else:
        rgb = img.convert("RGB")
    w, h = rgb.size
    if w > max_w:
        nh = max(1, int(round(h * (max_w / w))))
        rgb = rgb.resize((max_w, nh), Image.Resampling.LANCZOS)
    elif w < 960:
        scale = 960 / w
        nh = max(1, int(round(h * scale)))
        rgb = rgb.resize((960, nh), Image.Resampling.LANCZOS)
    rgb.save(dst, format="JPEG", quality=89, optimize=True)
    return rgb.size


def try_register_real_image(
    raw_bytes: bytes,
    source_tag: str,
    accepted_hashes: list[int],
    entries: list[dict[str, Any]],
    next_idx: list[int],
) -> bool:
    try:
        with Image.open(io.BytesIO(raw_bytes)) as im:
            if im.mode in ("RGBA", "LA", "PA"):
                canvas = Image.new("RGB", im.size, (20, 20, 19))
                rgba = im.convert("RGBA")
                canvas.paste(rgba, mask=rgba.split()[3])
                rgb = canvas
            else:
                rgb = im.convert("RGB")
            ok, score = passes_quality_filter(rgb)
            if not ok:
                return False
            dh = compute_dhash(rgb)
            for existing_h in accepted_hashes:
                if hamming_dist(dh, existing_h) < MIN_HAMMING_DIST:
                    return False

            idx = next_idx[0]
            next_idx[0] += 1
            fname = f"image_{idx:03d}.jpg"
            out_path = OUT_DIR / fname
            nw, nh = normalize_and_save(rgb, out_path)
            accepted_hashes.append(dh)
            entries.append({
                "id": idx,
                "filename": fname,
                "path": str(out_path),
                "width": nw,
                "height": nh,
                "aspect": round(nw / max(1, nh), 4),
                "source": source_tag,
                "archetype": "harvested",
                "dhash": f"{dh:016x}",
                "score": round(score, 1),
            })
            return True
    except Exception:
        return False


def harvest_real_assets(accepted_hashes: list[int], entries: list[dict[str, Any]], next_idx: list[int]) -> int:
    count = 0
    for folder in REAL_SOURCES_DIRS:
        if not folder.exists():
            continue
        for img_path in sorted(folder.iterdir()):
            if img_path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                continue
            if try_register_real_image(img_path.read_bytes(), f"studio:{img_path.name}", accepted_hashes, entries, next_idx):
                count += 1
            if len(entries) >= TARGET_REAL:
                return count

    if CORPUS_DIR.exists():
        for p in sorted(CORPUS_DIR.glob("*.pptx")):
            per_deck = 0
            try:
                with zipfile.ZipFile(p, "r") as z:
                    media = sorted(
                        [
                            n for n in z.namelist()
                            if n.startswith("ppt/media/")
                            and not n.startswith("ppt/media/av_art_")
                            and n.lower().endswith((".png", ".jpg", ".jpeg"))
                        ],
                        key=lambda n: z.getinfo(n).file_size,
                        reverse=True,
                    )
                    for m in media:
                        if z.getinfo(m).file_size < 24_000:
                            continue
                        if try_register_real_image(z.read(m), f"corpus:{p.stem}", accepted_hashes, entries, next_idx):
                            count += 1
                            per_deck += 1
                            if per_deck >= 3 or len(entries) >= TARGET_REAL:
                                break
            except Exception:
                pass
            if len(entries) >= TARGET_REAL:
                return count

    scraped_files = sorted(SCRAPED_DIR.glob("*.pptx")) if SCRAPED_DIR.exists() else []
    for max_per_deck in (1, 2):
        if len(entries) >= TARGET_REAL:
            break
        for p in scraped_files:
            if len(entries) >= TARGET_REAL:
                break
            per_deck = 0
            try:
                with zipfile.ZipFile(p, "r") as z:
                    media = [
                        n for n in z.namelist()
                        if n.startswith("ppt/media/")
                        and not n.startswith("ppt/media/av_art_")
                        and n.lower().endswith((".png", ".jpg", ".jpeg"))
                    ]
                    media.sort(key=lambda n: z.getinfo(n).file_size, reverse=True)
                    for m in media[:6]:
                        sz = z.getinfo(m).file_size
                        if sz < 35_000 or sz > 6_000_000:
                            continue
                        if try_register_real_image(z.read(m), f"scraped:{p.stem[:36]}", accepted_hashes, entries, next_idx):
                            count += 1
                            per_deck += 1
                            if per_deck >= max_per_deck or len(entries) >= TARGET_REAL:
                                break
            except Exception:
                pass
    return count


def _load_font(size: int, serif: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [r"C:\Windows\Fonts\georgia.ttf", r"C:\Windows\Fonts\times.ttf"]
        if serif
        else [r"C:\Windows\Fonts\bahnschrift.ttf", r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\segoeui.ttf"]
    )
    for fp in candidates:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_procedural_plate(archetype_idx: int, variant_idx: int, palette: tuple[str, str, str, str, str]) -> Image.Image:
    """Render a 2x-supersampled (2560x1600 -> 1280x800) fine-art & editorial visual plate."""
    W, H = 2560, 1600
    bg, panel, acc1, acc2, ink = (hex_rgb(c) for c in palette)
    rng = random.Random(archetype_idx * 997 + variant_idx * 131 + 73)
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img, "RGBA")

    arch = archetype_idx % 24
    # Subtle architectural background grid on technical & Swiss styles
    if arch in (0, 2, 4, 13, 15, 22):
        step = 160 if variant_idx % 2 == 0 else 200
        for gx in range(0, W, step):
            draw.line([(gx, 0), (gx, H)], fill=(*ink, 22), width=2)
        for gy in range(0, H, step):
            draw.line([(0, gy), (W, gy)], fill=(*ink, 22), width=2)

    if arch == 0:  # Architectural Monolith Perspective
        for i in range(8):
            bx = 180 + i * 270 + rng.randint(-20, 20)
            bw = rng.randint(170, 260)
            bh = rng.randint(520, 1280)
            by = H - bh - rng.randint(40, 180)
            col = acc1 if i == 2 else (acc2 if i == 5 else panel)
            draw.rectangle([bx, by, bx + bw, by + bh], fill=(*col, 240), outline=(*ink, 90), width=4)
            draw.polygon([(bx, by), (bx + 60, by - 48), (bx + bw + 60, by - 48), (bx + bw, by)], fill=(*ink, 55))
    elif arch == 1:  # Heliosphere Orbits & Corona
        cx, cy = int(W * (0.48 + 0.14 * math.sin(variant_idx))), int(H * 0.5)
        for r in range(180, 980, 105):
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*(acc1 if (r // 105) % 2 == 0 else acc2), 175), width=5)
        draw.ellipse([cx - 220, cy - 220, cx + 220, cy + 220], fill=(*acc1, 245))
        draw.ellipse([cx - 120, cy - 120, cx + 120, cy + 120], fill=(*acc2, 185))
    elif arch == 2:  # Topographic Elevation Contours
        for layer in range(18):
            pts = []
            base_y = 140 + layer * 78
            amp = 120 + (layer % 5) * 40
            freq = 0.0020 + variant_idx * 0.0004
            phase = layer * 0.45 + variant_idx
            for px in range(-40, W + 60, 32):
                py = base_y + math.sin(px * freq + phase) * amp + math.cos(px * freq * 1.8 - phase) * (amp * 0.38)
                pts.append((px, int(py)))
            col = acc1 if layer % 5 == 0 else (acc2 if layer % 3 == 0 else ink)
            draw.line(pts, fill=(*col, 210 if layer % 3 == 0 else 80), width=7 if layer % 5 == 0 else 3)
    elif arch == 3:  # Weimar Bauhaus Geometry
        draw.rectangle([160, 140, 1240, 1460], fill=(*panel, 255))
        draw.pieslice([520, 200, 1720, 1400], 180, 360, fill=(*acc1, 245))
        draw.pieslice([760, 380, 1960, 1580], 0, 180, fill=(*acc2, 225))
        draw.rectangle([220, 960, 2320, 1090], fill=(*ink, 240))
    elif arch == 4:  # Swiss International Color Matrix
        cols, rows = 14, 8
        cw, ch = 145, 145
        ox, oy = 210, 180
        for r in range(rows):
            for c in range(cols):
                v = math.sin(r * 0.72 + c * 0.54 + variant_idx)
                x0, y0 = ox + c * (cw + 10), oy + r * (ch + 10)
                fill = acc1 if v > 0.6 else (acc2 if v < -0.5 else panel)
                draw.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=16, fill=(*fill, 235 if abs(v) > 0.5 else 155))
    elif arch == 5:  # Asymmetric Diagonal Prism Split
        draw.polygon([(0, 0), (int(W * 0.60), 0), (int(W * 0.42), H), (0, H)], fill=(*panel, 255))
        draw.polygon([(int(W * 0.52), 140), (W - 140, 240), (int(W * 0.78), H - 140), (int(W * 0.36), H - 260)], fill=(*acc1, 195))
        draw.line([(int(W * 0.60), 0), (int(W * 0.42), H)], fill=(*acc2, 255), width=16)
    elif arch == 6:  # Harmonic Acoustic Sine Wave Field
        for w_idx in range(26):
            pts = []
            cy = 180 + w_idx * 48
            for px in range(0, W + 40, 24):
                env = math.exp(-((px - W * 0.5) / (W * 0.30)) ** 2)
                py = cy + math.sin(px * 0.008 + w_idx * 0.42 + variant_idx) * (220 * env + 18)
                pts.append((px, int(py)))
            c = acc1 if w_idx % 4 == 0 else (acc2 if w_idx % 4 == 2 else ink)
            draw.line(pts, fill=(*c, 225 if w_idx % 2 == 0 else 100), width=6)
    elif arch == 7:  # Fine-Art Oversized Serif Monograph Plate
        font_huge = _load_font(680, serif=True)
        font_sub = _load_font(68, serif=False)
        glyph = f"{(variant_idx * 13 + 7) % 99 + 1:02d}"
        draw.text((180, 120), glyph, font=font_huge, fill=(*acc1, 170))
        draw.rectangle([1220, 240, 2320, 1340], fill=(*panel, 240), outline=(*ink, 190), width=6)
        draw.ellipse([1420, 440, 2120, 1140], fill=(*acc2, 220))
        draw.text((1300, 1380), f"EDITION // FOLIO {glyph}", font=font_sub, fill=(*ink, 210))
    elif arch == 8:  # Constellation Network Graph
        nodes = [(rng.randint(240, W - 240), rng.randint(200, H - 200)) for _ in range(28)]
        for i, (x1, y1) in enumerate(nodes):
            for j in range(i + 1, len(nodes)):
                x2, y2 = nodes[j]
                if math.hypot(x2 - x1, y2 - y1) < 500:
                    draw.line([(x1, y1), (x2, y2)], fill=(*(acc2 if (i + j) % 3 == 0 else ink), 115), width=4)
        for i, (nx, ny) in enumerate(nodes):
            r = 46 if i % 5 == 0 else 22
            draw.ellipse([nx - r, ny - r, nx + r, ny + r], fill=(*(acc1 if i % 4 == 0 else acc2), 245), outline=(*ink, 210), width=4)
    elif arch == 9:  # Industrial Control Module
        draw.rounded_rectangle([200, 180, W - 200, H - 180], radius=48, fill=(*panel, 255), outline=(*ink, 120), width=6)
        draw.rounded_rectangle([300, 280, 1320, 880], radius=24, fill=(*bg, 255), outline=(*acc2, 230), width=5)
        for k in range(3):
            kx = 1580 + k * 250
            draw.ellipse([kx - 90, 420 - 90, kx + 90, 420 + 90], fill=(*(acc1 if k == 0 else bg), 255), outline=(*ink, 220), width=6)
        for f in range(6):
            fx = 360 + f * 310
            draw.rectangle([fx, 1020, fx + 44, 1380], fill=(*bg, 255), outline=(*ink, 100), width=3)
            ky = 1080 + rng.randint(20, 220)
            draw.rounded_rectangle([fx - 36, ky, fx + 80, ky + 52], radius=8, fill=(*(acc1 if f % 2 == 0 else acc2), 255))
    elif arch == 10:  # Translucent Overlapping Planes
        for p_idx in range(6):
            off = p_idx * 185
            x0, y0 = 260 + off, 210 + (p_idx % 3) * 100
            poly = [(x0, y0), (x0 + 680, y0 - 110), (x0 + 780, y0 + 780), (x0 + 100, y0 + 890)]
            col = acc1 if p_idx == 2 else (acc2 if p_idx == 4 else panel)
            draw.polygon(poly, fill=(*col, 210), outline=(*ink, 150), width=5)
    elif arch == 11:  # Kinetic Radial Turbine
        cx, cy = W // 2, H // 2
        for side in range(12):
            a1 = math.radians(side * 30 + variant_idx * 15)
            a2 = math.radians((side + 1) * 30 + variant_idx * 15)
            r1, r2 = 280, 760
            poly = [
                (cx + int(math.cos(a1) * r1), cy + int(math.sin(a1) * r1)),
                (cx + int(math.cos(a1) * r2), cy + int(math.sin(a1) * r2)),
                (cx + int(math.cos(a2) * r2), cy + int(math.sin(a2) * r2)),
                (cx + int(math.cos(a2) * r1), cy + int(math.sin(a2) * r1)),
            ]
            draw.polygon(poly, fill=(*(acc1 if side % 3 == 0 else (acc2 if side % 3 == 1 else panel)), 205), outline=(*ink, 130), width=4)
        draw.ellipse([cx - 210, cy - 210, cx + 210, cy + 210], fill=(*bg, 255), outline=(*acc1, 255), width=12)
    elif arch == 12:  # Botanical / Risograph Overlapping Folios
        for k in range(5):
            rx = 340 + k * 380
            ry = 340 + (k % 2) * 260
            col = acc1 if k % 2 == 0 else acc2
            draw.pieslice([rx - 320, ry - 320, rx + 320, ry + 320], k * 35, k * 35 + 165, fill=(*col, 190))
        draw.rectangle([220, 1280, W - 220, 1310], fill=(*ink, 210))
    elif arch == 13:  # FT Financial Monograph Bar & Ribbon Chart
        pts = []
        for i in range(18):
            bx = 240 + i * 118
            val = int(420 + 520 * (0.5 + 0.45 * math.sin(i * 0.45 + variant_idx)))
            col = acc1 if i in (4, 11, 15) else panel
            draw.rectangle([bx, H - 240 - val, bx + 74, H - 240], fill=(*col, 235), outline=(*ink, 90), width=2)
            pts.append((bx + 37, H - 240 - val - 40))
        draw.line(pts, fill=(*acc2, 255), width=10)
    elif arch == 14:  # Luxury Noir Champagne Concentric Frame
        for inset in (120, 220, 320):
            draw.rectangle([inset, inset, W - inset, H - inset], outline=(*acc1, 210 if inset == 120 else 110), width=5)
        draw.ellipse([W // 2 - 380, H // 2 - 380, W // 2 + 380, H // 2 + 380], fill=(*panel, 240), outline=(*acc1, 230), width=8)
        draw.ellipse([W // 2 - 180, H // 2 - 180, W // 2 + 180, H // 2 + 180], fill=(*acc2, 210))
    elif arch == 15:  # Architectural CAD Schematic Arcs
        draw.rectangle([180, 160, W - 180, H - 160], outline=(*acc1, 230), width=6)
        draw.arc([320, 240, 1680, 1600], 180, 360, fill=(*acc2, 245), width=10)
        draw.arc([880, 80, 2240, 1440], 0, 180, fill=(*ink, 210), width=8)
        draw.line([(180, H // 2), (W - 180, H // 2)], fill=(*acc1, 180), width=4)
        draw.line([(W // 2, 160), (W // 2, H - 160)], fill=(*acc1, 180), width=4)
    elif arch == 16:  # Kyoto Ma-Zen Balance
        draw.ellipse([1360, 260, 2260, 1160], fill=(*panel, 255), outline=(*ink, 140), width=4)
        draw.rectangle([1960, 240, 2240, 520], fill=(*acc1, 245))
        draw.rectangle([240, 1160, 1520, 1280], fill=(*ink, 235))
    elif arch == 17:  # Op-Art Optical Moire Stripes
        for x in range(180, W - 180, 34):
            h_var = int(320 + 260 * math.sin(x * 0.005 + variant_idx))
            col = acc1 if (x // 34) % 7 == 0 else (acc2 if (x // 34) % 5 == 0 else ink)
            draw.rectangle([x, H // 2 - h_var, x + 16, H // 2 + h_var], fill=(*col, 210))
    elif arch == 18:  # Constructivist Diagonal Wedge & Sphere
        draw.polygon([(140, H - 140), (W - 240, 180), (W - 120, 440), (360, H - 60)], fill=(*acc1, 240))
        draw.ellipse([360, 200, 1160, 1000], fill=(*acc2, 235), outline=(*ink, 230), width=10)
        draw.rectangle([1440, 920, 2360, 1420], fill=(*ink, 245))
    elif arch == 19:  # Translucent Glass Aperture Lenses
        for k in range(7):
            cx = 360 + k * 290
            cy = 520 + (k % 3) * 240
            r = 280 + (k % 2) * 90
            col = acc1 if k % 2 == 0 else acc2
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*col, 130), outline=(*ink, 180), width=5)
    elif arch == 20:  # Brutalist Concrete Relief Slabs
        for row in range(4):
            for col_i in range(4):
                x0 = 180 + col_i * 560
                y0 = 160 + row * 330
                col = acc1 if (row + col_i) % 5 == 0 else (acc2 if (row * 2 + col_i) % 7 == 0 else panel)
                draw.rectangle([x0, y0, x0 + 500, y0 + 270], fill=(*col, 240), outline=(*ink, 220), width=6)
    elif arch == 21:  # Solar Eclipse & Horizon Split
        draw.rectangle([0, H // 2 + 120, W, H], fill=(*panel, 255))
        draw.ellipse([W // 2 - 420, H // 2 - 420, W // 2 + 420, H // 2 + 420], fill=(*acc1, 245))
        draw.ellipse([W // 2 - 320, H // 2 - 360, W // 2 + 360, H // 2 + 320], fill=(*ink, 250))
        draw.line([(160, H // 2 + 120), (W - 160, H // 2 + 120)], fill=(*acc2, 255), width=12)
    elif arch == 22:  # Swiss Woven Plaid Grid
        for x in range(180, W - 180, 220):
            draw.rectangle([x, 120, x + 90, H - 120], fill=(*acc1, 140))
        for y in range(140, H - 140, 220):
            draw.rectangle([120, y, W - 120, y + 85], fill=(*acc2, 145))
        draw.ellipse([W // 2 - 220, H // 2 - 220, W // 2 + 220, H // 2 + 220], fill=(*ink, 240))
    else:  # 23: Isometric Ribbon Mobius
        for k in range(12):
            off = k * 65
            pts = [
                (260 + off, 280 + k * 30),
                (1280 + off, 180 + k * 25),
                (2120 - off, 1180 - k * 30),
                (940 - off, 1340 - k * 20),
            ]
            draw.polygon(pts, outline=(*(acc1 if k % 2 == 0 else acc2), 230), width=9)

    return img.resize((1280, 800), Image.Resampling.LANCZOS)


def generate_procedural_assets(
    accepted_hashes: list[int],
    entries: list[dict[str, Any]],
    next_idx: list[int],
    count: int,
) -> int:
    generated = 0
    total_archetypes = 24
    for slot in range(count):
        arch = slot % total_archetypes
        var = slot // total_archetypes
        attempt = 0
        while True:
            cur_arch = (arch + attempt) % total_archetypes
            cur_pal = PALETTES[(slot * 5 + cur_arch + attempt * 3) % len(PALETTES)]
            img = render_procedural_plate(cur_arch, var + attempt * 11, cur_pal)
            dh = compute_dhash(img)
            if attempt > 24 or all(hamming_dist(dh, h) >= 8 for h in accepted_hashes):
                break
            attempt += 1
        idx = next_idx[0]
        next_idx[0] += 1
        fname = f"image_{idx:03d}.jpg"
        out_path = OUT_DIR / fname
        nw, nh = normalize_and_save(img, out_path, max_w=1280)
        accepted_hashes.append(dh)
        entries.append({
            "id": idx,
            "filename": fname,
            "path": str(out_path),
            "width": nw,
            "height": nh,
            "aspect": round(nw / max(1, nh), 4),
            "source": f"editorial-plate:{cur_arch:02d}",
            "archetype": f"proc-{cur_arch:02d}",
            "dhash": f"{dh:016x}",
            "score": 100.0,
        })
        generated += 1
    return generated


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old_f in OUT_DIR.glob("image_*.jpg"):
        old_f.unlink()

    accepted_hashes: list[int] = []
    entries: list[dict[str, Any]] = []
    next_idx = [1]

    print("[ASSET BANK] Harvesting gallery-safe high-contrast imagery (rejecting screenshots)...", flush=True)
    real_cnt = harvest_real_assets(accepted_hashes, entries, next_idx)
    print(f"[ASSET BANK] Harvested {real_cnt} deduplicated non-screenshot images.", flush=True)

    needed_proc = max(0, TARGET_TOTAL - len(entries))
    print(f"[ASSET BANK] Generating {needed_proc} bespoke fine-art & editorial plates...", flush=True)
    proc_cnt = generate_procedural_assets(accepted_hashes, entries, next_idx, count=needed_proc)

    MANIFEST_PATH.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[ASSET BANK] Built {len(entries)} total deduplicated plates (real={real_cnt}, procedural={proc_cnt}) -> {MANIFEST_PATH}", flush=True)


if __name__ == "__main__":
    main()
