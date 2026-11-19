"""
AI Visual Director & Organic Layer Deconstruction Linter (`ai_slide_director.py`)
Executable tooling for external AI agents to plan, choreograph, and audit .pptx decks:
  1. `storyboard` — Produces an organic, DNA-preserving multi-stage layer-deconstruction
                    storyboard JSON (zero rigid 8-template stencils, zero fixed 15-slide
                    quota). Can extract real color/typography DNA directly from an existing
                    `--pptx` file or synthesize continuous proportion-driven stages from a
                    topic brief, pairing persistent `!!sXX-layer-YY` Morph IDs.
  2. `audit`      — Scans any `.pptx` archive and outputs a 0-100 quality scorecard covering
                    internal DNA color coherence (zero multi-designer clash), `<p159:morph>`
                    coverage, `!!` actor pairing across adjacent slides, word-density bloat,
                    XML entity leaks, and unmapped ZIP parts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from lxml import etree as LET

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from expand_to_avant_garde_15 import (
    CANVAS_H_CM,
    CANVAS_H_EMU,
    CANVAS_W_CM,
    CANVAS_W_EMU,
    DESIGN_FAMILIES,
    NS_A,
    NS_P,
    PARSER,
    color_dist,
    extract_original_dna,
    parse_theme_info,
    pick_design_family,
    resolve_fill_hex,
)


def _continuous_stage_zones(beat_idx: int, stage_idx: int, n_stages: int, density: int) -> dict[str, dict[str, float]]:
    """Compute continuous, non-stencil 16:9 actor coordinates driven by content density & golden angle."""
    phi = (beat_idx * 0.618033988749895 + density * 0.047) % 1.0
    flip = (beat_idx % 2 == 1)
    margin = round(1.5 + 0.55 * ((phi * 3.0) % 1.0), 2)
    split_x = round(14.4 + 3.6 * math.sin(phi * math.pi), 2)
    pfx = f"!!s{beat_idx:02d}"

    if stage_idx == 0:
        art_w = round(CANVAS_W_CM - split_x - margin if not flip else split_x - margin * 1.3, 2)
        art_x = round(CANVAS_W_CM - art_w - margin if not flip else margin, 2)
        tx = margin if not flip else round(art_x + art_w + 1.0, 2)
        tw = round(max(10.5, CANVAS_W_CM - art_w - margin * 2.4), 2)
        return {
            f"{pfx}-bgband": {"x": 0.0 if not flip else round(CANVAS_W_CM - split_x, 2), "y": 0.0, "w": round(split_x, 2), "h": CANVAS_H_CM},
            f"{pfx}-layer-00": {"x": tx, "y": 4.6, "w": tw, "h": 6.4},
            f"{pfx}-layer-01": {"x": art_x, "y": 2.4, "w": art_w, "h": 14.2},
            f"{pfx}-layer-02": {"x": tx, "y": 20.2, "w": tw, "h": 3.8},  # staged off-canvas for Morph glide
        }
    elif stage_idx == 1:
        art_w = round(12.8 + 2.2 * phi, 2)
        art_x = margin if not flip else round(CANVAS_W_CM - margin - art_w, 2)
        tx = round(art_x + art_w + 1.1, 2) if not flip else margin
        tw = round(CANVAS_W_CM - art_w - margin * 2 - 1.1, 2)
        return {
            f"{pfx}-bgband": {"x": 0.0, "y": 0.0, "w": CANVAS_W_CM, "h": 3.2},
            f"{pfx}-layer-00": {"x": margin, "y": 1.1, "w": 24.0, "h": 1.9},
            f"{pfx}-layer-01": {"x": art_x, "y": 4.0, "w": art_w, "h": 8.6},
            f"{pfx}-layer-02": {"x": tx, "y": 4.4, "w": tw, "h": 6.2},
        }
    else:
        art_w = round(15.6 + 1.8 * phi, 2)
        art_x = round(CANVAS_W_CM - margin - art_w, 2) if flip else margin
        tx = margin if flip else round(art_x + art_w + 1.1, 2)
        tw = round(CANVAS_W_CM - art_w - margin * 2 - 1.1, 2)
        return {
            f"{pfx}-bgband": {"x": 0.0, "y": 0.0, "w": CANVAS_W_CM, "h": 1.1},
            f"{pfx}-layer-00": {"x": tx, "y": 2.5, "w": tw, "h": 4.2},
            f"{pfx}-layer-01": {"x": art_x, "y": 2.3, "w": art_w, "h": 10.8},
            f"{pfx}-layer-02": {"x": tx, "y": 7.4, "w": tw, "h": 5.8},
        }


def generate_storyboard(
    title: str,
    category: str,
    industry: str,
    beats: int = 0,
    source_pptx: Path | None = None,
) -> dict[str, Any]:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "deck"
    fallback_fam = pick_design_family(slug, category, industry, 0)

    if source_pptx and source_pptx.exists():
        with zipfile.ZipFile(source_pptx, "r") as zin:
            orig_slides = sorted(
                [n for n in zin.namelist() if re.match(r"^ppt/slides/slide\d+\.xml$", n)],
                key=lambda s: int("".join(filter(str.isdigit, Path(s).stem)) or 0),
            )
            dna = extract_original_dna(zin, slug, orig_slides, CANVAS_W_EMU, CANVAS_H_EMU, fallback_fam)
            beat_count = beats if beats > 0 else max(4, len(orig_slides))
            dna_source = f"extracted:{source_pptx.name}"
    else:
        dna = dict(fallback_fam, is_monochrome=False, raw_head_font="Bahnschrift", raw_body_font="Segoe UI")
        seed = int(hashlib.md5(slug.encode("utf-8")).hexdigest(), 16)
        beat_count = beats if beats > 0 else (5 + (seed % 5))  # organic 5..9 narrative beats -> ~14..28 slides
        dna_source = f"synthesized:{fallback_fam['id']}"

    stage_labels = [
        ("Layer Setup & Camera Framing", "Primary anchor enters slightly zoomed; supporting details rest off-canvas ready to Morph in."),
        ("Progressive Layer Unfold", "Camera pulls back while first wave of supporting copy/cards glides into position."),
        ("Full Composition Resolution", "All topic layers lock cleanly into balanced reading hierarchy."),
        ("Architectural Focus & Takeaway", "Camera shifts to spotlight the core proof or executive conclusion before next beat."),
    ]

    storyboard_slides = []
    slide_cursor = 0
    prev_actors: set[str] = set()
    for b in range(1, beat_count + 1):
        # Organic per-beat stage count (2..4) driven by beat complexity rather than fixed total
        density = 2 + ((b * 7 + len(title)) % 4)
        n_stages = 2 if (b == 1 or b == beat_count) else (4 if density >= 5 else 3)
        for st in range(n_stages):
            slide_cursor += 1
            zones = _continuous_stage_zones(b, st, n_stages, density)
            cur_actors = set(zones.keys())
            shared = sorted(cur_actors & prev_actors)
            st_name, st_note = stage_labels[min(st, len(stage_labels) - 1)]
            storyboard_slides.append({
                "slide": slide_cursor,
                "narrativeBeat": b,
                "stageInBeat": f"{st + 1}/{n_stages}",
                "stageRole": st_name,
                "backgroundHex": f"#{dna['bg']}",
                "accentHex": f"#{dna['acc1']}",
                "transition": '<p159:morph option="byObject"/>',
                "morphActorsPreservedFromPrev": shared,
                "boundingBoxesCm": zones,
                "artDirection": st_note,
            })
            prev_actors = cur_actors

    return {
        "title": title,
        "category": category,
        "industry": industry,
        "dnaSource": dna_source,
        "organicTotalSlides": len(storyboard_slides),
        "narrativeBeats": beat_count,
        "canvasCm": {"width": CANVAS_W_CM, "height": CANVAS_H_CM},
        "dnaPalette": {
            "id": dna["id"],
            "label": dna["label"],
            "isDark": dna["is_dark"],
            "isMonochrome": dna.get("is_monochrome", False),
            "bg": f"#{dna['bg']}",
            "panel": f"#{dna['panel']}",
            "card": f"#{dna['card']}",
            "ink": f"#{dna['ink']}",
            "acc1": f"#{dna['acc1']}",
            "acc2": f"#{dna['acc2']}",
            "headFont": dna.get("raw_head_font", dna["head_font"]),
            "bodyFont": dna.get("raw_body_font", dna["body_font"]),
        },
        "slides": storyboard_slides,
    }


def audit_pptx(pptx_path: Path) -> dict[str, Any]:
    if not pptx_path.exists():
        raise FileNotFoundError(f"PPTX not found: {pptx_path}")

    with zipfile.ZipFile(pptx_path, "r") as z:
        names = set(z.namelist())
        pres_xml = z.read("ppt/presentation.xml").decode("utf-8", "ignore")
        pres_rels = LET.fromstring(z.read("ppt/_rels/presentation.xml.rels"), PARSER)
        rid_to_target = {r.attrib["Id"]: r.attrib["Target"] for r in pres_rels if r.attrib.get("Id")}
        sld_rids = re.findall(r'r:id="([^"]+)"', pres_xml)
        ordered_slides = []
        for rid in sld_rids:
            tgt = rid_to_target.get(rid, "").lstrip("/")
            if tgt and not tgt.startswith("ppt/"):
                tgt = "ppt/" + tgt
            if tgt in names:
                ordered_slides.append(tgt)

        scheme_map, _, _ = parse_theme_info(z)
        total_slides = len(ordered_slides)
        morph_count = 0
        actor_sets: list[set[str]] = []
        bg_hexes: list[str] = []
        word_walls = []
        entity_leaks = []

        for idx, sp in enumerate(ordered_slides, start=1):
            raw_bytes = z.read(sp)
            raw_txt = raw_bytes.decode("utf-8", "ignore")
            if "<p159:morph" in raw_txt:
                morph_count += 1
            if "&amp;amp;" in raw_txt:
                entity_leaks.append(idx)

            root = LET.fromstring(raw_bytes, PARSER)
            bg_pr = root.find(f".//{{{NS_P}}}bg/{{{NS_P}}}bgPr")
            bh, balpha = resolve_fill_hex(bg_pr, scheme_map)
            if bh and balpha > 40000:
                bg_hexes.append(bh)

            actors = set()
            for cnv in root.iter(f"{{{NS_P}}}cNvPr"):
                nm = cnv.attrib.get("name", "")
                if nm.startswith("!!"):
                    actors.add(nm)
            actor_sets.append(actors)

            for sp_node in root.iter(f"{{{NS_P}}}sp"):
                words = " ".join(t.text or "" for t in sp_node.iter(f"{{{NS_A}}}t")).split()
                if len(words) > 65:
                    word_walls.append({"slide": idx, "words": len(words)})

        unmatched_json = [n for n in names if n.endswith(".json")]
        paired_morph = 0
        for i in range(len(actor_sets) - 1):
            if actor_sets[i] & actor_sets[i + 1]:
                paired_morph += 1

        # DNA Palette Coherence check: flag sudden jarring background switches (>2 unrelated palettes)
        bg_clusters: list[str] = []
        for bh in bg_hexes:
            if all(color_dist(bh, c) > 65 for c in bg_clusters):
                bg_clusters.append(bh)
        dna_clash = len(bg_clusters) > 3

    score = 100
    findings: list[str] = []
    if total_slides < 10:
        score -= 15
        findings.append(f"Only {total_slides} slides; expand organically with layer staging beats.")
    morph_ratio = morph_count / max(1, total_slides)
    if morph_ratio < 0.5:
        score -= 20
        findings.append(f"Low <p159:morph> coverage ({morph_count}/{total_slides} slides).")
    if total_slides > 1 and paired_morph == 0:
        score -= 20
        findings.append("No matching !!-prefixed shapes across adjacent slides (Morph cannot track objects).")
    if dna_clash:
        score -= 15
        findings.append(f"DNA palette clash detected: {len(bg_clusters)} unrelated slide background clusters ({bg_clusters[:4]}).")
    if word_walls:
        score -= min(15, len(word_walls) * 3)
        findings.append(f"{len(word_walls)} text boxes exceed 65 words (wall-of-text risk).")
    if entity_leaks:
        score -= 10
        findings.append(f"Double-escaped XML entity (&amp;amp;) found on slides: {entity_leaks[:5]}.")
    if unmatched_json:
        score -= 15
        findings.append(f"Unmapped .json entries in ZIP can crash PowerPoint COM: {unmatched_json}.")

    return {
        "file": str(pptx_path),
        "score": max(0, score),
        "totalSlides": total_slides,
        "morphSlides": morph_count,
        "pairedMorphTransitions": paired_morph,
        "backgroundClusters": [f"#{c}" for c in bg_clusters[:6]],
        "dnaCoherent": not dna_clash,
        "wordWallsOver65Words": len(word_walls),
        "doubleEscapedEntitySlides": entity_leaks,
        "findings": findings if findings else ["Coherent original DNA palette, organic layer choreography, and valid Morph transitions."],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Visual Director & Organic Layer Deconstruction Linter")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sb = sub.add_parser("storyboard", help="Generate an organic DNA-preserving layer-deconstruction storyboard JSON")
    sb.add_argument("--title", required=True)
    sb.add_argument("--category", default="Strategy")
    sb.add_argument("--industry", default="Enterprise")
    sb.add_argument("--beats", type=int, default=0, help="Number of core narrative beats (0 = organic)")
    sb.add_argument("--pptx", type=Path, default=None, help="Optional source .pptx to extract authentic DNA palette from")

    au = sub.add_parser("audit", help="Audit an existing .pptx for DNA coherence, Morph pairing & OOXML hygiene")
    au.add_argument("pptx_path", type=Path)

    args = parser.parse_args()
    if args.cmd == "storyboard":
        res = generate_storyboard(args.title, args.category, args.industry, args.beats, args.pptx)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.cmd == "audit":
        res = audit_pptx(args.pptx_path)
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
