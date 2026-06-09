"""In-memory cache of user behavior sequences from user_behavior.csv.

Indexed by user_id → list of product_ids ordered by timestamp.
Used as a fallback for LSTM context when Neo4j BOUGHT history is empty
(e.g. new bookstore customers not yet in the knowledge graph)."""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List

log = logging.getLogger("ai-service.behavior_cache")

_cache: Dict[int, List[int]] = {}


def load(rows: List[Dict]) -> None:
    """Build the cache from pre-loaded behavior rows.

    Each row must have keys: user_id (int), product_id (int), timestamp (str).
    Sequences are sorted by timestamp so the last entry is the most recent."""
    by_user: Dict[int, List] = defaultdict(list)
    for r in rows:
        by_user[r["user_id"]].append((r["timestamp"], r["product_id"]))

    global _cache
    _cache = {}
    for uid, events in by_user.items():
        events.sort(key=lambda e: e[0])
        _cache[uid] = [e[1] for e in events]

    log.info("BehaviorCache loaded: %d users indexed", len(_cache))


def get_history(user_id: int, limit: int = 5) -> List[int]:
    """Return the last `limit` product_ids from the user's behavior history."""
    seq = _cache.get(user_id, [])
    return seq[-limit:] if seq else []


def is_loaded() -> bool:
    return bool(_cache)
