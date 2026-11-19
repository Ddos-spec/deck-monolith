"""
BlackArch Wave-7 High-Speed Harvest Engine (Target: 215+ New Unique Decks -> 1,050+ Total)
Enforces 4-layer anti-duplication against existing_fingerprints.json + local BlackArch corpus:
  1. Source URL deduplication
  2. Normalized filename stem deduplication
  3. Exact SHA-256 binary deduplication
  4. Inner slide 1..3 <a:t> content SHA-256 deduplication
Combines parallel Archive.org metadata workers + GitHub Code Search + GitHub Repo Tree workers
and streams downloads immediately until TARGET_NEW is reached.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = Path("/var/tmp/pptx_mega")
DECKS_W7 = BASE / "decks_w7"
DECKS_W7.mkdir(parents=True, exist_ok=True)
META_OUT = BASE / "w7_meta.json"
REG_PATH = BASE / "existing_fingerprints.json"

GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

TARGET_NEW = 215
LOCK = threading.Lock()

seen_urls: set[str] = set()
seen_hashes: set[str] = set()
seen_norm_stems: set[str] = set()
seen_text_hashes: set[str] = set()
existing_names: set[str] = set()


def norm_stem(stem: str) -> str:
    s = re.sub(r"^(?:gh|ia|sc)[-_]+", "", stem.strip(), flags=re.IGNORECASE)
    s = re.sub(r"[-_][0-9a-f]{4}$", "", s, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def inner_text_hash(z: zipfile.ZipFile) -> str | None:
    orig_slides = sorted(
        [n for n in z.namelist() if re.match(r"^ppt/slides/slide\d+\.xml$", n)],
        key=lambda s: int("".join(filter(str.isdigit, Path(s).stem)) or 0),
    )
    chunks: list[str] = []
    for sf in orig_slides[:3]:
        try:
            root = ET.fromstring(z.read(sf))
            for t in root.iter(f"{NS_A}t"):
                if t.text and t.text.strip():
                    ts = t.text.strip()
                    if not any(tok in ts.upper() for tok in ("AVANT //", "MORPH", "KINETIC")):
                        chunks.append(ts.lower())
        except Exception:
            pass
    joined = re.sub(r"\s+", "", "".join(chunks))
    if len(joined) >= 10:
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:24]
    return None


def load_existing_fingerprints() -> None:
    if REG_PATH.exists():
        reg = json.loads(REG_PATH.read_text(encoding="utf-8"))
        seen_hashes.update(reg.get("sha256") or [])
        seen_norm_stems.update(reg.get("norm_stems") or [])
        seen_urls.update(reg.get("urls") or [])
        seen_text_hashes.update(reg.get("text_hashes") or [])

    for mp in [
        Path("/tmp/pptx_harvest/scraped_meta.json"),
        BASE / "mega_meta.json",
        BASE / "w2_meta.json",
        BASE / "w3_meta.json",
        BASE / "w4_meta.json",
        BASE / "w6_meta.json",
        META_OUT,
    ]:
        if mp.exists():
            try:
                m = json.loads(mp.read_text(encoding="utf-8"))
                for k, v in m.items():
                    existing_names.add(k)
                    seen_norm_stems.add(norm_stem(Path(k).stem))
                    if isinstance(v, dict) and v.get("source_url"):
                        seen_urls.add(v["source_url"].strip())
            except Exception:
                pass

    for d in [
        Path("/tmp/pptx_harvest/decks"),
        Path("/tmp/pptx_harvest/decks_batch2"),
        BASE / "decks",
        BASE / "decks_w2",
        BASE / "decks_w3",
        BASE / "decks_w4",
        BASE / "decks_w6",
        DECKS_W7,
    ]:
        if d.exists():
            for p in d.glob("*.pptx"):
                existing_names.add(p.name)
                seen_norm_stems.add(norm_stem(p.stem))
                try:
                    seen_hashes.add(hashlib.sha256(p.read_bytes()).hexdigest())
                except Exception:
                    pass

    print(
        f"[W7-Init] hashes={len(seen_hashes)}, stems={len(seen_norm_stems)}, "
        f"urls={len(seen_urls)}, text_hashes={len(seen_text_hashes)}",
        flush=True,
    )


def fetch_url(url: str, headers: dict[str, str] | None = None, timeout: int = 12) -> bytes:
    hdrs = {"User-Agent": UA}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_gh(url: str, timeout: int = 12) -> bytes:
    return fetch_url(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GH_TOKEN}",
        },
        timeout=timeout,
    )


def discover_archive_parallel(limit: int = 450) -> list[tuple[str, str, str]]:
    """Parallel Archive.org search + metadata fetcher (fast!)."""
    idents: list[str] = []
    seen_id: set[str] = set()
    queries = [
        "format%3A%22Powerpoint%22",
        "pptx+AND+presentation",
        "pptx+AND+%28strategy+OR+marketing+OR+finance+OR+design%29",
        "pptx+AND+%28engineering+OR+architecture+OR+science+OR+report%29",
    ]
    for q in queries:
        for pg in (1, 2, 3, 4):
            try:
                u = (
                    f"https://archive.org/advancedsearch.php?q={q}"
                    f"&fl[]=identifier&rows=100&page={pg}&output=json"
                )
                data = json.loads(fetch_url(u, timeout=10).decode("utf-8"))
                for d in data.get("response", {}).get("docs", []):
                    ident = d.get("identifier")
                    if ident and ident not in seen_id:
                        seen_id.add(ident)
                        idents.append(ident)
            except Exception:
                pass
            if len(idents) >= 700:
                break
        if len(idents) >= 700:
            break

    print(f"[W7-Archive] Inspecting {len(idents)} Archive.org items in 16 threads...", flush=True)
    cands: list[tuple[str, str, str]] = []

    def check_item(ident: str) -> list[tuple[str, str, str]]:
        found = []
        try:
            meta = json.loads(fetch_url(f"https://archive.org/metadata/{ident}/files", timeout=8).decode("utf-8"))
            for f in meta.get("result", []):
                fname = f.get("name", "")
                sz = int(f.get("size") or 0)
                if fname.lower().endswith(".pptx") and 18_000 <= sz <= 14_000_000:
                    dl = f"https://archive.org/download/{ident}/{urllib.parse.quote(fname)}"
                    stem_clean = re.sub(r"[^a-zA-Z0-9._-]+", "-", Path(fname).stem)[:34]
                    out_fn = f"ia_{re.sub(r'[^a-zA-Z0-9-]+', '-', ident)[:20]}_{stem_clean}_{hashlib.md5(dl.encode()).hexdigest()[:4]}.pptx"
                    if dl not in seen_urls and norm_stem(Path(out_fn).stem) not in seen_norm_stems:
                        found.append((out_fn, dl, f"Internet Archive ({ident})"))
                        if len(found) >= 2:
                            break
        except Exception:
            pass
        return found

    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = [ex.submit(check_item, ident) for ident in idents[:650]]
        for fut in as_completed(futs):
            cands.extend(fut.result())
            if len(cands) >= limit:
                break

    print(f"[W7-Archive] Discovered {len(cands)} unseen Archive.org .pptx candidates", flush=True)
    return cands[:limit]


def discover_github_code_search(limit: int = 350) -> list[tuple[str, str, str]]:
    """Direct GitHub /search/code for .pptx files across topics (respects rate limit)."""
    keywords = [
        "presentation", "pitch", "strategy", "architecture", "report",
        "design", "marketing", "workshop", "analytics", "roadmap",
        "finance", "security", "proposal", "ecommerce", "cloud",
    ]
    out: list[tuple[str, str, str]] = []
    seen_raw: set[str] = set()
    for kw in keywords:
        if len(out) >= limit:
            break
        for pg in (1, 2):
            try:
                u = f"https://api.github.com/search/code?q={kw}+extension:pptx+size:>22000&per_page=50&page={pg}"
                data = json.loads(fetch_gh(u, 12).decode("utf-8"))
                for it in data.get("items", []):
                    html_u = it.get("html_url", "")
                    repo = it.get("repository", {})
                    fn = repo.get("full_name", "")
                    path = it.get("path", "")
                    if not fn or not path.lower().endswith(".pptx"):
                        continue
                    # Extract branch/ref from html_url: https://github.com/user/repo/blob/BRANCH/path
                    m_br = re.search(r"/blob/([^/]+)/", html_u)
                    br = m_br.group(1) if m_br else repo.get("default_branch", "main")
                    dl = f"https://raw.githubusercontent.com/{fn}/{br}/{urllib.parse.quote(path)}"
                    repo_short = re.sub(r"[^a-zA-Z0-9-]+", "-", fn.split("/")[-1])[:20]
                    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", Path(path).stem)[:40]
                    h4 = hashlib.md5(dl.encode()).hexdigest()[:4]
                    out_fn = f"gh_{repo_short}_{stem}_{h4}.pptx"
                    if dl not in seen_urls and dl not in seen_raw and norm_stem(Path(out_fn).stem) not in seen_norm_stems:
                        seen_raw.add(dl)
                        out.append((out_fn, dl, f"GitHub ({fn})"))
                time.sleep(1.1)  # stay safely under 30 code-search reqs/min secondary cap
            except Exception as e:
                if "403" in str(e) or "429" in str(e):
                    time.sleep(8.0)
                    break
                time.sleep(1.5)
    print(f"[W7-GitHubCode] Discovered {len(out)} unseen GitHub .pptx candidates", flush=True)
    return out[:limit]


def download_and_validate(cand: tuple[str, str, str]) -> tuple[str, dict] | None:
    fname, url, src_name = cand
    ns = norm_stem(Path(fname).stem)
    with LOCK:
        if url in seen_urls or fname in existing_names or ns in seen_norm_stems:
            return None

    out_p = DECKS_W7 / fname
    if out_p.exists():
        return None
    try:
        raw = fetch_url(url, timeout=16)
        if not (18_000 <= len(raw) <= 14_000_000):
            return None
        fhash = hashlib.sha256(raw).hexdigest()
        with LOCK:
            if fhash in seen_hashes:
                return None

        out_p.write_bytes(raw)
        if not zipfile.is_zipfile(out_p):
            out_p.unlink(missing_ok=True)
            return None

        with zipfile.ZipFile(out_p, "r") as z:
            names = z.namelist()
            if "ppt/presentation.xml" not in names:
                out_p.unlink(missing_ok=True)
                return None
            slide_files = sorted(
                [n for n in names if re.match(r"^ppt/slides/slide\d+\.xml$", n)],
                key=lambda s: int("".join(filter(str.isdigit, Path(s).stem)) or 0),
            )
            if len(slide_files) < 3:
                out_p.unlink(missing_ok=True)
                return None

            th = inner_text_hash(z)
            real_elements = 0
            snippets: list[str] = []
            for sf in slide_files[:5]:
                sraw = z.read(sf).decode("utf-8", "ignore")
                real_elements += len(re.findall(r"<p:(?:sp|pic|graphicFrame|grpSp)\b", sraw))
                for t in re.findall(r"<a:t>([^<]+)</a:t>", sraw):
                    if t.strip():
                        snippets.append(t.strip())

            snippet_txt = " ".join(snippets[:30])[:800]
            if real_elements < 2 and len(snippet_txt) < 18:
                out_p.unlink(missing_ok=True)
                return None

        with LOCK:
            if fhash in seen_hashes or ns in seen_norm_stems or (th and th in seen_text_hashes):
                out_p.unlink(missing_ok=True)
                return None
            seen_hashes.add(fhash)
            seen_norm_stems.add(ns)
            seen_urls.add(url)
            existing_names.add(fname)
            if th:
                seen_text_hashes.add(th)

        return fname, {
            "filename": fname,
            "source_url": url,
            "source": src_name,
            "inferred_title": Path(fname).stem,
            "snippet_text": snippet_txt,
            "sha256": fhash,
            "text_hash": th or "",
            "slides_orig": len(slide_files),
        }
    except Exception:
        out_p.unlink(missing_ok=True)
        return None


def main() -> None:
    load_existing_fingerprints()
    meta_out: dict[str, dict] = {}
    if META_OUT.exists():
        try:
            meta_out = json.loads(META_OUT.read_text(encoding="utf-8"))
        except Exception:
            meta_out = {}

    accepted = len(list(DECKS_W7.glob("*.pptx")))

    # Stage 1: Archive.org parallel + download immediately
    cands = discover_archive_parallel(limit=420)
    # Stage 2: If needed, GitHub code search
    if len(cands) < 350:
        cands.extend(discover_github_code_search(limit=350))

    print(f"[W7-Download] Validating {len(cands)} candidates across 14 workers (cur={accepted}, target={TARGET_NEW})...", flush=True)
    with ThreadPoolExecutor(max_workers=14) as ex:
        futs = [ex.submit(download_and_validate, c) for c in cands]
        for fut in as_completed(futs):
            res = fut.result()
            if res is None:
                continue
            fn, info = res
            meta_out[fn] = info
            accepted += 1
            if accepted % 20 == 0 or accepted >= TARGET_NEW:
                print(f"  [W7-OK] Accepted {accepted}/{TARGET_NEW}: {fn}", flush=True)
                META_OUT.write_text(json.dumps(meta_out, indent=2, ensure_ascii=False), encoding="utf-8")
            if accepted >= TARGET_NEW:
                break

    META_OUT.write_text(json.dumps(meta_out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[W7-DONE] Total unique decks in {DECKS_W7}: {len(list(DECKS_W7.glob('*.pptx')))}", flush=True)


if __name__ == "__main__":
    main()
