"""
Build 4-Layer Anti-Duplication Registry:
  1. sha256 file hashes
  2. normalized stems (strips gh_/ia_/sc_ prefix & _4hex suffix)
  3. source URLs (from scraped_meta.json & curated_index.json)
  4. inner slide1..3 non-injected <a:t> text sha256 hashes
Emits D:\\code\\ppt_studio\\existing_fingerprints.json for BlackArch Wave-7.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

BASE = Path(r"D:\code\ppt_studio")
OUT_JSON = BASE / "existing_fingerprints.json"


def norm_stem(stem: str) -> str:
    s = re.sub(r"^(?:gh|ia|sc)[-_]+", "", stem.strip(), flags=re.IGNORECASE)
    s = re.sub(r"[-_][0-9a-f]{4}$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[^a-z0-9]+", "", s.lower())
    return s


def extract_inner_text_hash(pptx_path: Path) -> str | None:
    try:
        with zipfile.ZipFile(pptx_path, "r") as z:
            pres_rels = z.read("ppt/_rels/presentation.xml.rels").decode("utf-8", "ignore") if "ppt/_rels/presentation.xml.rels" in z.namelist() else ""
            # Only hash non-av original slide files in numeric order
            orig_slides = sorted(
                [n for n in z.namelist() if re.match(r"^ppt/slides/slide\d+\.xml$", n)],
                key=lambda s: int("".join(filter(str.isdigit, Path(s).stem)) or 0),
            )
            chunks: list[str] = []
            for sf in orig_slides[:3]:
                raw = z.read(sf).decode("utf-8", "ignore")
                for t in re.findall(r"<a:t>([^<]+)</a:t>", raw):
                    ts = t.strip()
                    if ts and not any(x in ts.upper() for x in ("AVANT //", "MORPH ·", "✦ MORPH", "⚡ KINETIC")):
                        chunks.append(ts.lower())
            joined = re.sub(r"\s+", "", "".join(chunks))
            if len(joined) >= 10:
                return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:24]
    except Exception:
        pass
    return None


def main() -> None:
    sha256_set: set[str] = set()
    stem_set: set[str] = set()
    url_set: set[str] = set()
    text_set: set[str] = set()

    # Load URLs from scraped_meta.json & curated_index.json
    scraped_meta = BASE / "corpus_scraped" / "scraped_meta.json"
    if scraped_meta.exists():
        meta = json.loads(scraped_meta.read_text(encoding="utf-8"))
        if isinstance(meta, dict):
            for k, v in meta.items():
                ns = norm_stem(Path(k).stem)
                if ns:
                    stem_set.add(ns)
                if isinstance(v, dict):
                    u = v.get("source_url") or v.get("sourceUrl") or ""
                    if u:
                        url_set.add(u.strip())

    curated_idx = BASE / "curated_index.json"
    if curated_idx.exists():
        cur = json.loads(curated_idx.read_text(encoding="utf-8"))
        for item in cur:
            if item.get("sourceUrl"):
                url_set.add(item["sourceUrl"].strip())
            if item.get("slug"):
                stem_set.add(norm_stem(item["slug"]))

    scan_dirs = [
        BASE / "corpus_scraped",
        BASE / "corpus",
        BASE / "corpus_curated",
        BASE / "corpus_curated_v2",
        BASE / "examples_out",
    ]
    scanned = 0
    for d in scan_dirs:
        if not d.exists():
            continue
        for p in d.glob("*.pptx"):
            if p.name.endswith(".tmp.pptx"):
                continue
            scanned += 1
            data = p.read_bytes()
            sha256_set.add(hashlib.sha256(data).hexdigest())
            ns = norm_stem(p.stem)
            if ns:
                stem_set.add(ns)
            th = extract_inner_text_hash(p)
            if th:
                text_set.add(th)

    payload = {
        "sha256": sorted(sha256_set),
        "norm_stems": sorted(stem_set),
        "urls": sorted(url_set),
        "text_hashes": sorted(text_set),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"[DEDUP REGISTRY] Scanned {scanned} pptx | sha256={len(sha256_set)} "
        f"| stems={len(stem_set)} | urls={len(url_set)} | text_hashes={len(text_set)} -> {OUT_JSON}",
        flush=True,
    )


if __name__ == "__main__":
    main()
