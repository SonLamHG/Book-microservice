"""Seed the Neo4j Knowledge Graph from the on-disk dataset
`ai-service/data/graph_triples.csv` (plus the product corpus for node
attributes).

Phases:
  1. Wipe existing graph + apply uniqueness constraints.
  2. Insert Category, Product nodes from product_corpus.jsonl.
  3. Insert User nodes + apply edges from graph_triples.csv
     (IN_CATEGORY, BOUGHT, VIEWED, SIMILAR).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .driver import get_driver
from ..datasets import load_graph_triples, load_product_corpus

log = logging.getLogger("ai-service.graph.seed")


CREATE_CONSTRAINTS = [
    "CREATE CONSTRAINT user_id_unique     IF NOT EXISTS FOR (u:User)     REQUIRE u.id IS UNIQUE",
    "CREATE CONSTRAINT product_id_unique  IF NOT EXISTS FOR (p:Product)  REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT category_id_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.id IS UNIQUE",
]
WIPE = "MATCH (n) DETACH DELETE n"


def seed_graph(
    products: Optional[List[Dict[str, Any]]] = None,
    orders: Optional[List[Dict[str, Any]]] = None,    # kept for backwards compat — ignored
) -> bool:
    """Re-seed the graph from the canonical on-disk dataset.

    `products` is preferred from caller (typically fetched from
    product-service); falls back to product_corpus.jsonl.  `orders`
    is accepted but no longer used — edges come from graph_triples.csv
    now.
    """
    drv = get_driver()
    if drv is None:
        log.warning("Skipping graph seed: no Neo4j driver")
        return False

    if not products:
        products = load_product_corpus()
    triples = load_graph_triples()

    if not products or not triples:
        log.warning("Skipping graph seed: products=%d, triples=%d",
                    len(products or []), len(triples))
        return False

    with drv.session() as s:
        s.run(WIPE)
        for q in CREATE_CONSTRAINTS:
            s.run(q)

        # Categories first — from product corpus.
        categories = {}
        for p in products:
            cid = p.get("category_id")
            if cid is None:
                continue
            categories[cid] = p.get("category", "")
        s.run(
            "UNWIND $rows AS r MERGE (c:Category {id: r.id}) SET c.name = r.name",
            rows=[{"id": cid, "name": name} for cid, name in categories.items()],
        )

        # Products.
        s.run(
            """
            UNWIND $rows AS p
            MERGE (prod:Product {id: p.id})
              SET prod.name = p.name,
                  prod.price = p.price,
                  prod.product_type = p.product_type,
                  prod.category_id = p.category_id
            """,
            rows=[
                {
                    "id": int(p.get("id", p.get("product_id"))),
                    "name": p.get("name", ""),
                    "price": float(p.get("price", 0)),
                    "product_type": p.get("type") or p.get("product_type", "book"),
                    "category_id": p.get("category_id"),
                }
                for p in products
            ],
        )

        # Group edges by type for batched insert.
        by_edge: Dict[str, List[Dict[str, Any]]] = {}
        for t in triples:
            by_edge.setdefault(t["edge_type"], []).append(t)

        # IN_CATEGORY: Product → Category
        rows = by_edge.get("IN_CATEGORY", [])
        if rows:
            s.run(
                """
                UNWIND $rows AS r
                MATCH (p:Product {id: r.source_id}),
                      (c:Category {id: r.target_id})
                MERGE (p)-[:IN_CATEGORY]->(c)
                """,
                rows=rows,
            )

        # BOUGHT: User → Product
        rows = by_edge.get("BOUGHT", [])
        if rows:
            s.run(
                """
                UNWIND $rows AS r
                MERGE (u:User {id: r.source_id})
                WITH u, r
                MATCH (p:Product {id: r.target_id})
                MERGE (u)-[b:BOUGHT]->(p)
                  ON CREATE SET b.count = r.weight
                  ON MATCH  SET b.count = r.weight
                """,
                rows=rows,
            )

        # VIEWED: User → Product
        rows = by_edge.get("VIEWED", [])
        if rows:
            s.run(
                """
                UNWIND $rows AS r
                MERGE (u:User {id: r.source_id})
                WITH u, r
                MATCH (p:Product {id: r.target_id})
                MERGE (u)-[v:VIEWED]->(p)
                  ON CREATE SET v.count = r.weight
                  ON MATCH  SET v.count = r.weight
                """,
                rows=rows,
            )

        # SIMILAR: Product → Product
        rows = by_edge.get("SIMILAR", [])
        if rows:
            s.run(
                """
                UNWIND $rows AS r
                MATCH (a:Product {id: r.source_id}),
                      (b:Product {id: r.target_id})
                MERGE (a)-[sim:SIMILAR]->(b)
                  ON CREATE SET sim.weight = r.weight, sim.source = 'dataset'
                  ON MATCH  SET sim.weight = r.weight
                """,
                rows=rows,
            )

        # Final sanity log.
        result = s.run(
            "MATCH (n) WITH labels(n) AS l, count(*) AS c RETURN l, c"
        )
        for record in result:
            log.info("Graph node count: %s = %d", record["l"], record["c"])

    return True
