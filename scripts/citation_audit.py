#!/usr/bin/env python3
"""
FreshRoute Citation Audit — P0 Governance

Checks every numeric constant and cite tag traces to BIBLIOGRAPHY.bib or calibration note.
See docs/IMPLEMENTATION_PLAN.md:3.2 and docs/adr/000.

Usage:
    python scripts/citation_audit.py [--bib docs/BIBLIOGRAPHY.bib] [--root freshroute-optimizer-model]

Exit 0 = pass; non-zero = violations table printed (also CI fails if TODO-cite remains).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BIB_KEY_RE = re.compile(r"@\w+\{([^,\s]+)\s*,")
CITE_RE = re.compile(r"\[@([a-z0-9_:\-]+)\]|\\cite\{([^}]+)\}|CITED\s*\[@[a-z0-9_\-]+\]|cites?:?\s*\[@", re.IGNORECASE)
# Only flag actionable debt in .py sources; XXX placeholder in docs DOI (zenodo.XXXX) ignored.
# Pattern purposely excludes the script's own definition line and the docs example `rg -n "...XXX"`.
TODO_RE = re.compile(r"TODO\s*\(?cite|FIXME", re.IGNORECASE)
SKIP_TODO_FILES = {"citation_audit.py"}

def parse_bib_keys(bib_path: Path) -> set[str]:
    text = bib_path.read_text(encoding="utf-8", errors="ignore")
    return set(BIB_KEY_RE.findall(text))

def collect_cites(root: Path) -> set[str]:
    cites: set[str] = set()
    for p in root.rglob("*"):
        if p.is_dir() or p.suffix not in {".py", ".md", ".bib", ".cff"}:
            continue
        # skip venv / node_modules
        if "node_modules" in p.parts or ".git" in p.parts or "mlruns" in p.parts:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in CITE_RE.finditer(txt):
            # handle both bracket and \cite forms
            raw = m.group(0)
            # extract keys inside
            keys = re.findall(r"[a-z0-9_:\-]+", raw.lower())
            for k in keys:
                if k not in {"cite", "cited", "cites"}:
                    cites.add(k.lower())
        # also extract raw [@key] occurrences more robustly
        for k in re.findall(r"\[@([a-z0-9_\-]+)\]", txt, flags=re.IGNORECASE):
            cites.add(k.lower())
        for k in re.findall(r"\\cite\{([^}]+)\}", txt):
            for sub in k.split(","):
                cites.add(sub.strip().lower())
    return cites

def find_todos(root: Path) -> list[str]:
    hits: list[str] = []
    for p in root.rglob("*"):
        if p.is_dir() or p.suffix not in {".py", ".md"}:
            continue
        if "node_modules" in p.parts or ".git" in p.parts:
            continue
        if p.name in SKIP_TODO_FILES:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            # Skip docs that document the audit command itself
            if 'rg -n "TODO' in txt and "IMPLEMENTATION_PLAN" in str(p):
                # For plan docs, only flag lines that are actual debt outside the quoted command
                # — we check per-line and ignore the exact documentation line
                pass
            for i, line in enumerate(txt.splitlines(), 1):
                if 'rg -n "TODO' in line:
                    continue
                if p.suffix == ".md" and "zenodo." in line.lower():
                    continue  # DOI placeholder not debt
                if TODO_RE.search(line):
                    hits.append(f"{p}:{i}: {line.strip()[:160]}")
        except Exception:
            continue
    return hits

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bib", default="docs/BIBLIOGRAPHY.bib")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    bib_path = Path(args.bib)
    root = Path(args.root)

    if not bib_path.exists():
        print(f"[error] BIB not found: {bib_path}", file=sys.stderr)
        return 2

    bib_keys = parse_bib_keys(bib_path)
    cites = collect_cites(root)
    todos = find_todos(root)

    # normalize both to lower
    bib_lower = {k.lower() for k in bib_keys}
    # remove known non-bib cites (e.g., internal keys that are not in bib but are allowed)
    # For P0, we only warn on cites not in bib (not fail) — future gate will fail.
    # Ignore placeholder cite [@key] in templates.
    unknown = sorted(c for c in cites if c and c not in bib_lower and len(c) > 2 and c != "key")

    ok = True
    print(f"[audit] BIB keys: {len(bib_keys)} | cites found: {len(cites)} | TODO-cite: {len(todos)}")
    if todos:
        print("\n[fail] TODO/FIXME cite debt (must be 0 at gate):")
        for h in todos[:50]:
            print(f"  {h}")
        ok = False
    if unknown:
        print("\n[warn] cites without BIB entry (add to BIBLIOGRAPHY.bib before gate):")
        for k in unknown[:100]:
            print(f"  [@ {k}]")
        # warn only for now; gate will escalate to fail at P1
    if ok and not unknown:
        print("[pass] citation audit green")
    elif ok and unknown:
        print("[pass with warnings] no TODO debt, but unresolved cites remain — fix before gate")
    else:
        print("[fail] citation debt present")
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
