"""Loaders for the three on-disk training datasets that the AI service consumes:

  ai-service/data/
    user_behavior.csv    → LSTM training sequences
    graph_triples.csv    → Neo4j seed (nodes + edges)
    product_corpus.jsonl → FAISS RAG + product metadata source-of-truth

Each loader returns plain Python structures; callers (lstm.train, graph.seed,
rag.index) consume them without needing to know the on-disk format.
"""
from __future__ import annotations

import csv
import json
import logging
from typing import Any, Dict, List

from . import config

log = logging.getLogger("ai-service.datasets")

BEHAVIOR_PATH = config.BEHAVIOR_CSV_PATH
TRIPLES_PATH  = config.GRAPH_CSV_PATH
CORPUS_PATH   = config.CORPUS_JSONL_PATH


# ─── product corpus ───────────────────────────────────────────────────

def load_product_corpus() -> List[Dict[str, Any]]:
    """Returns the product catalogue (27 items, hand-curated).

    The on-disk file uses `product_id` as the primary key column; we
    rename it to `id` here so consumers see the same shape they would
    get back from product-service via REST. Other corpus-only fields
    (keywords, brand_or_author, category name) are preserved verbatim."""
    if not CORPUS_PATH.exists():
        log.warning("Corpus file missing: %s", CORPUS_PATH)
        return []
    out: List[Dict[str, Any]] = []
    with CORPUS_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if "product_id" in entry and "id" not in entry:
                entry["id"] = entry["product_id"]
            # Map corpus `type` field to the REST `product_type` field.
            if "type" in entry and "product_type" not in entry:
                entry["product_type"] = entry["type"]
            out.append(entry)
    log.info("Loaded product corpus: %d items from %s", len(out), CORPUS_PATH.name)
    return out


# ─── user behaviour log ──────────────────────────────────────────────

def load_user_behavior() -> List[Dict[str, Any]]:
    """Returns list of behaviour events.
    Each event is a dict with keys: user_id, product_id, action, timestamp."""
    if not BEHAVIOR_PATH.exists():
        log.warning("Behavior file missing: %s", BEHAVIOR_PATH)
        return []
    rows: List[Dict[str, Any]] = []
    with BEHAVIOR_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "user_id":    int(r["user_id"]),
                "product_id": int(r["product_id"]),
                "action":     r["action"],
                "timestamp":  r["timestamp"],
            })
    log.info("Loaded user behavior log: %d events from %s",
             len(rows), BEHAVIOR_PATH.name)
    return rows


def behavior_sequences_per_user(rows: List[Dict[str, Any]]) -> Dict[int, List[int]]:
    """Group behaviour rows by user, sort by timestamp, return ordered
    product-id sequence per user. Skips users with too-short history.
    Used directly by LSTM training as the sequence corpus."""
    by_user: Dict[int, List[Dict[str, Any]]] = {}
    for r in rows:
        by_user.setdefault(r["user_id"], []).append(r)
    out: Dict[int, List[int]] = {}
    for uid, events in by_user.items():
        events.sort(key=lambda e: e["timestamp"])
        seq = [e["product_id"] for e in events]
        if len(seq) >= 3:
            out[uid] = seq
    return out


# ─── graph triples ───────────────────────────────────────────────────

def load_graph_triples() -> List[Dict[str, Any]]:
    """Returns explicit graph edges. Each entry has:
       source_type, source_id, edge_type, target_type, target_id, weight."""
    if not TRIPLES_PATH.exists():
        log.warning("Graph triples file missing: %s", TRIPLES_PATH)
        return []
    rows: List[Dict[str, Any]] = []
    with TRIPLES_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "source_type": r["source_type"],
                "source_id":   int(r["source_id"]),
                "edge_type":   r["edge_type"],
                "target_type": r["target_type"],
                "target_id":   int(r["target_id"]),
                "weight":      float(r["weight"]),
            })
    log.info("Loaded graph triples: %d edges from %s",
             len(rows), TRIPLES_PATH.name)
    return rows
