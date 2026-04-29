"""Cypher recommendation queries on the Knowledge Graph."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from .driver import get_driver

log = logging.getLogger("ai-service.graph.queries")


# Recommend products that are SIMILAR to anything the user has BOUGHT,
# excluding what they already own. Score = sum of (BOUGHT count × SIMILAR weight).
RECOMMEND_CYPHER = """
MATCH (u:User {id: $user_id})-[b:BOUGHT]->(p:Product)-[s:SIMILAR]->(rec:Product)
WHERE NOT (u)-[:BOUGHT]->(rec)
WITH rec, sum(coalesce(b.count, 1) * coalesce(s.weight, 1.0)) AS score
RETURN rec.id AS product_id, rec.name AS name, score
ORDER BY score DESC
LIMIT $top_k
"""


# Fallback when the user has no purchase history: surface popular products
# (the most-bought across all users).
POPULAR_CYPHER = """
MATCH (:User)-[b:BOUGHT]->(p:Product)
WITH p, sum(coalesce(b.count, 1)) AS popularity
RETURN p.id AS product_id, p.name AS name, popularity AS score
ORDER BY score DESC
LIMIT $top_k
"""


def graph_recommend(user_id: int, top_k: int = 10) -> List[Dict[str, Any]]:
    drv = get_driver()
    if drv is None:
        return []
    with drv.session() as s:
        rows = s.run(RECOMMEND_CYPHER, user_id=int(user_id), top_k=int(top_k)).data()
        if not rows:
            rows = s.run(POPULAR_CYPHER, top_k=int(top_k)).data()
    return rows


def user_history(user_id: int, limit: int = 50) -> List[int]:
    """Return product ids the user has BOUGHT, most recent (by order_id) first."""
    drv = get_driver()
    if drv is None:
        return []
    cypher = """
    MATCH (u:User {id: $user_id})-[b:BOUGHT]->(p:Product)
    RETURN p.id AS product_id, coalesce(b.first_order_id, 0) AS oid
    ORDER BY oid DESC
    LIMIT $limit
    """
    with drv.session() as s:
        rows = s.run(cypher, user_id=int(user_id), limit=int(limit)).data()
    return [r["product_id"] for r in rows]
