"""
OOXML Blueprint & Morph/Animation Corpus Analyzer
Reads every .pptx under corpus/ and reference styles/, extracting design tokens,
typography, transitions (including p159:morph), !! morph-actor pairs, and p:timing stats.
"""

import json
import os
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "p14": "http://schemas.microsoft.com/office/powerpoint/2010/main",
    "p159": "http://schemas.microsoft.com/office/powerpoint/2015/09/main",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
}


def analyze_pptx(pptx_path: Path) -> dict:
    info = {
        "file": pptx_path.name,
        "path": str(pptx_path),
        "size_kb": round(pptx_path.stat().st_size / 1024, 1),
        "slides": 0,
        "total_shapes": 0,
        "avg_shapes_per_slide": 0.0,
        "transitions": Counter(),
        "morph_slides": 0,
        "morph_actors": set(),
        "animation_slides": 0,
        "fonts": Counter(),
        "colors": Counter(),
        "theme_fonts": {},
    }

    try:
        with zipfile.ZipFile(pptx_path, "r") as z:
            names = z.namelist()
            slide_files = sorted(
                [
                    n for n in names
                    if n.startswith("ppt/slides/")
                    and n.endswith(".xml")
                    and (Path(n).name.startswith("slide") or Path(n).name.startswith("av_slide_"))
                ],
                key=lambda s: (0 if Path(s).name.startswith("av_slide_") else 1, int("".join(filter(str.isdigit, Path(s).stem)) or 0)),
            )
            info["slides"] = len(slide_files)

            if "ppt/theme/theme1.xml" in names:
                t_root = ET.fromstring(z.read("ppt/theme/theme1.xml"))
                maj = t_root.find(".//a:majorFont/a:latin", NS)
                min_f = t_root.find(".//a:minorFont/a:latin", NS)
                info["theme_fonts"] = {
                    "major": maj.attrib.get("typeface") if maj is not None else None,
                    "minor": min_f.attrib.get("typeface") if min_f is not None else None,
                }

            prev_actors = set()
            paired_morph_transitions = 0

            for sf in slide_files:
                root = ET.fromstring(z.read(sf))
                # Shapes
                sps = root.findall(".//p:sp", NS) + root.findall(".//p:pic", NS) + root.findall(".//p:graphicFrame", NS)
                info["total_shapes"] += len(sps)

                slide_actors = set()
                for cnv in root.findall(".//p:cNvPr", NS):
                    nm = cnv.attrib.get("name", "")
                    if nm.startswith("!!"):
                        slide_actors.add(nm)
                        info["morph_actors"].add(nm)

                # Transitions
                morph_el = root.find(".//p159:morph", NS)
                has_trans = root.findall(".//p:transition", NS)
                if morph_el is not None:
                    info["morph_slides"] += 1
                    info["transitions"]["morph"] += 1
                    if slide_actors & prev_actors:
                        paired_morph_transitions += 1
                elif has_trans:
                    for tr in has_trans:
                        for child in tr:
                            tag = child.tag.split("}")[-1]
                            info["transitions"][tag] += 1

                # Animations
                if root.find(".//p:timing", NS) is not None:
                    info["animation_slides"] += 1

                # Fonts & Colors
                for rpr in root.findall(".//a:rPr", NS) + root.findall(".//a:defRPr", NS):
                    lat = rpr.find("a:latin", NS)
                    if lat is not None and lat.attrib.get("typeface"):
                        info["fonts"][lat.attrib["typeface"]] += 1

                for srgb in root.findall(".//a:srgbClr", NS):
                    val = srgb.attrib.get("val")
                    if val:
                        info["colors"][f"#{val.upper()}"] += 1

                prev_actors = slide_actors

            info["paired_morph_slides"] = paired_morph_transitions
            if info["slides"]:
                info["avg_shapes_per_slide"] = round(info["total_shapes"] / info["slides"], 1)

    except Exception as exc:
        info["error"] = str(exc)

    return {
        "file": info["file"],
        "path": info["path"],
        "size_kb": info["size_kb"],
        "slides": info["slides"],
        "avg_shapes_per_slide": info["avg_shapes_per_slide"],
        "morph_slides": info["morph_slides"],
        "paired_morph_slides": info.get("paired_morph_slides", 0),
        "morph_actor_count": len(info["morph_actors"]),
        "animation_slides": info["animation_slides"],
        "transitions": dict(info["transitions"]),
        "top_fonts": [f for f, _ in info["fonts"].most_common(5)],
        "top_colors": [c for c, _ in info["colors"].most_common(8)],
        "theme_fonts": info["theme_fonts"],
        **({"error": info["error"]} if "error" in info else {}),
    }


def main():
    roots = [
        Path(r"D:\code\ppt_studio\corpus"),
        Path(r"D:\code\ppt_studio\refs\OfficeCLI\skills\morph-ppt\reference\styles"),
    ]
    pptx_files = []
    for r in roots:
        if r.exists():
            pptx_files.extend(sorted(r.rglob("*.pptx")))

    results = [analyze_pptx(p) for p in pptx_files]
    out_json = Path(r"D:\code\ppt_studio\corpus_blueprints.json")
    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Analyzed {len(results)} PPTX files -> {out_json}")
    print(f"{'File':<34} {'Slides':>6} {'Shapes/Sl':>9} {'Morph':>5} {'Pairs':>5} {'Anim':>4}  Top Fonts")
    print("-" * 100)
    for r in results:
        fonts = ", ".join(r["top_fonts"][:3]) or "-"
        print(
            f"{r['file'][:33]:<34} {r['slides']:>6} {r['avg_shapes_per_slide']:>9} "
            f"{r['morph_slides']:>5} {r['paired_morph_slides']:>5} {r['animation_slides']:>4}  {fonts}"
        )


if __name__ == "__main__":
    main()
