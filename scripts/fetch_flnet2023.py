#!/usr/bin/env python3
"""Download the FLNET2023 *CSV* dataset from the project's anonymous SharePoint share.

FLNET2023 (Kumar et al., MILCOM 2023 — the *primary* dataset for this thesis)
is published via the repo github.com/nsol-nmsu/FML-Network, which points to a
Microsoft SharePoint/OneDrive-for-Business share. The full share is multiple
terabytes because it also ships PCAP packet captures; we only need the
CICFlowMeter **CSV** network-flow files (~3 GB), which is all `load_flnet2023`
consumes.

The share grants *anonymous* access: fetching the share URL sets a `FedAuth`
cookie (tenant-anon membership) and redirects to the folder's server-relative
path. With that cookie we can walk the folder tree via the SharePoint REST API
and stream individual files — no login required.

We mirror the remote layout under data/flnet2023/<Category>/... but:
  * skip every `PCAP` folder (the multi-TB packet captures), and
  * skip the top-level `TEST` folder (mixed traffic that would otherwise be
    misread as a 6th class by the top-level-folder labelling in the loader).

Resumable: a file already present locally with the same byte size is skipped.

    python3 scripts/fetch_flnet2023.py                 # default: data/flnet2023
    python3 scripts/fetch_flnet2023.py --out data/flnet2023 --dry-run
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

SHARE_URL = ("https://eltnmsu-my.sharepoint.com/:f:/g/personal/pratyay_nmsu_edu/"
             "ErDns0cRITtEsawkCgfqYTIB7BGJ_YDfp9r-p_80v3GxIQ?e=UimpBG")
HOST = "https://eltnmsu-my.sharepoint.com"
WEB = f"{HOST}/personal/pratyay_nmsu_edu/_api/web"
# Server-relative root of the shared folder (from the share-link redirect target).
ROOT = "/personal/pratyay_nmsu_edu/Documents/Dataset"

# Folders we never descend into / never treat as a class.
SKIP_FOLDER_NAMES = {"pcap"}          # skip anywhere in the tree (huge captures)
SKIP_TOPLEVEL_NAMES = {"test"}        # skip only at the Dataset root (bogus class)

JSON_HEADERS = {"Accept": "application/json;odata=nometadata"}


def _srv_literal(path: str) -> str:
    """URL-encode a server-relative path for use inside an OData string literal
    (single quotes doubled per OData, everything else percent-encoded but keeping
    the path separators)."""
    return quote(path.replace("'", "''"), safe="/()")


def open_session() -> requests.Session:
    """Anonymous session carrying the share's FedAuth cookie."""
    s = requests.Session()
    s.headers.update({"User-Agent": "flnet-fetch/1.0"})
    r = s.get(SHARE_URL, allow_redirects=True, timeout=60)
    r.raise_for_status()
    if not any(c.name == "FedAuth" for c in s.cookies):
        raise SystemExit("ERROR: no FedAuth cookie — the share may no longer be "
                         "anonymously accessible; supply the CSVs manually.")
    return s


def list_folders(s: requests.Session, srv_path: str) -> list[str]:
    url = f"{WEB}/GetFolderByServerRelativeUrl('{_srv_literal(srv_path)}')/Folders?$select=Name"
    r = s.get(url, headers=JSON_HEADERS, timeout=60)
    r.raise_for_status()
    return [f["Name"] for f in r.json().get("value", [])]


def list_files(s: requests.Session, srv_path: str) -> list[dict]:
    url = (f"{WEB}/GetFolderByServerRelativeUrl('{_srv_literal(srv_path)}')/Files"
           "?$select=Name,Length,ServerRelativeUrl")
    r = s.get(url, headers=JSON_HEADERS, timeout=60)
    r.raise_for_status()
    return r.json().get("value", [])


def gather_csvs(s: requests.Session, srv_path: str, top_level: bool = False) -> list[dict]:
    """Recursively collect CSV file records under srv_path, honouring skip rules."""
    out: list[dict] = []
    for f in list_files(s, srv_path):
        if f["Name"].lower().endswith(".csv"):
            out.append(f)
    for name in list_folders(s, srv_path):
        low = name.lower()
        if low in SKIP_FOLDER_NAMES:
            continue
        if top_level and low in SKIP_TOPLEVEL_NAMES:
            continue
        out.extend(gather_csvs(s, f"{srv_path}/{name}", top_level=False))
    return out


def download(s: requests.Session, srv_url: str, dest: Path, expected: int,
             retries: int = 3) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{WEB}/GetFileByServerRelativeUrl('{_srv_literal(srv_url)}')/$value"
    for attempt in range(1, retries + 1):
        try:
            with s.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                got = 0
                with open(tmp, "wb") as fh:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        if chunk:
                            fh.write(chunk)
                            got += len(chunk)
                if expected and got != expected:
                    raise IOError(f"size mismatch: got {got} want {expected}")
                tmp.replace(dest)
            return
        except Exception as e:
            if attempt == retries:
                raise
            print(f"    retry {attempt}/{retries} ({type(e).__name__}: {e})", flush=True)
            time.sleep(2 * attempt)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/flnet2023",
                    help="local root to mirror the CSV tree into")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be downloaded, then exit")
    args = ap.parse_args()

    out_root = Path(args.out)
    s = open_session()
    print(f"enumerating {ROOT} (CSV only, skipping PCAP + TEST) ...", flush=True)
    records = gather_csvs(s, ROOT, top_level=True)
    if not records:
        raise SystemExit("ERROR: no CSV files found under the share.")

    total_bytes = sum(int(r["Length"]) for r in records)
    print(f"found {len(records)} CSV files, {total_bytes/1e9:.2f} GB total\n", flush=True)

    # Map each remote file to a local path that preserves <Category>/... structure.
    def local_path(srv_url: str) -> Path:
        rel = srv_url[len(ROOT):].lstrip("/")   # e.g. DDoS/CSV/Dataset-1-BOT.csv
        return out_root / rel

    done_bytes = 0
    for i, rec in enumerate(sorted(records, key=lambda r: r["ServerRelativeUrl"]), 1):
        srv_url = rec["ServerRelativeUrl"]
        size = int(rec["Length"])
        dest = local_path(srv_url)
        tag = f"[{i:>3}/{len(records)}] {dest.relative_to(out_root)} ({size/1e6:.1f} MB)"
        if dest.exists() and dest.stat().st_size == size:
            print(f"{tag} SKIP (present)", flush=True)
            done_bytes += size
            continue
        if args.dry_run:
            print(f"{tag} would download", flush=True)
            continue
        print(f"{tag} downloading ...", flush=True)
        download(s, srv_url, dest, size)
        done_bytes += size
        print(f"      ok  ({done_bytes/1e9:.2f}/{total_bytes/1e9:.2f} GB)", flush=True)

    print("\nFLNET2023 CSV download complete." if not args.dry_run
          else "\n(dry run — nothing downloaded)")
    print(f"root: {out_root.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
