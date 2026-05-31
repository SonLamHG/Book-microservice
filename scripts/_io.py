"""Tiny helpers shared by preprocess scripts.

Kept in a private module so download_datasets.py and preprocess.py
don't repeat themselves. Anything reused by 2+ scripts goes here.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List

REPO_ROOT = Path(__file__).resolve().parent.parent
AI_DATA_DIR = REPO_ROOT / "ai-service" / "data"
RAW_DIR = AI_DATA_DIR / "raw"


def stable_int(s: str, lo: int, hi: int) -> int:
    """Deterministic int in [lo, hi] from a string. Used to fabricate
    stable prices/stock from book titles so two preprocess runs produce
    the same output."""
    h = hashlib.md5(s.encode("utf-8")).hexdigest()
    return lo + int(h, 16) % (hi - lo + 1)


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False))
            f.write("\n")
            n += 1
    return n


def write_csv(path: Path, header: List[str], rows: Iterable[Iterable[Any]]) -> int:
    n = 0
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
            n += 1
    return n


def deterministic_rng(seed: int = 42) -> random.Random:
    return random.Random(seed)
