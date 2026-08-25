"""
Update data_manifest.json with SHA256 for gold files (P1 FAIR provenance).

Computes SHA256 for each file listed in manifest where path exists, updates
`sha256` field, sets `version` timestamp, and ensures DOI placeholders are
preserved. Used after ingestion or training to keep manifest in sync.

Usage:
  python -m data.update_manifest
  python -m data.update_manifest --manifest data/data_manifest.json

Citations: [@wilkinson2016fair; @gebru2021datasheets]
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def update_manifest(manifest_path: Path | None = None) -> Dict[str, Any]:
    if manifest_path is None:
        manifest_path = Path(__file__).parent / "data_manifest.json"
        # Also try sibling data/ if running from different cwd
        if not manifest_path.exists():
            manifest_path = Path(__file__).resolve().parent / "data_manifest.json"
    # Resolve to absolute
    manifest_path = manifest_path.resolve()
    if not manifest_path.exists():
        # Try alternative: freshroute-optimizer-model/data/data_manifest.json from repo root
        alt = Path(__file__).resolve().parents[1] / "data" / "data_manifest.json"
        if alt.exists():
            manifest_path = alt
        else:
            raise FileNotFoundError(f"manifest not found: {manifest_path}")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_dir = manifest_path.parent  # data/ dir
    # Also consider repo root data/ for gold files
    updated = 0
    for entry in data.get("files", []):
        rel = entry.get("path", "")
        # Try multiple bases: data/ dir, manifest parent, repo root
        candidates = [
            base_dir / rel,
            base_dir / Path(rel).name,
            Path(__file__).resolve().parents[1] / rel,
            Path.cwd() / rel,
        ]
        # Also handle data/gold/* vs gold/*
        # Normalize rel that starts with data/
        if rel.startswith("data/"):
            candidates.append(base_dir / rel.replace("data/", "", 1))
            candidates.append(Path(__file__).resolve().parents[1] / rel)

        found: Path | None = None
        for c in candidates:
            if c.exists() and c.is_file():
                found = c
                break
        if found is None:
            # Check gold files explicitly
            gold_name = Path(rel).name
            gold_candidates = [
                base_dir / "gold" / gold_name,
                Path(__file__).resolve().parents[1] / "data" / "gold" / gold_name,
                Path(__file__).resolve().parents[1] / "gold" / gold_name,
            ]
            for gc in gold_candidates:
                if gc.exists():
                    found = gc
                    break
        if found and found.exists():
            sha = _sha256(found)
            entry["sha256"] = sha
            entry["bytes"] = found.stat().st_size
            entry["updated"] = datetime.now(timezone.utc).isoformat()
            updated += 1
        else:
            # Keep pending if not found
            if entry.get("sha256", "").startswith("pending"):
                pass

    # Update meta
    data["_meta"]["generated"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"updated {updated} entries in {manifest_path}")
    return data


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=str, default=None, help="path to data_manifest.json")
    args = ap.parse_args()
    path = Path(args.manifest) if args.manifest else None
    update_manifest(path)
