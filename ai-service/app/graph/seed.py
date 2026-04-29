"""Seed the Knowledge Graph with User/Product nodes and BOUGHT/VIEWED/SIMILAR
edges built from the existing seed data in book-service and order-service."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from .driver import get_driver

log = logging.getLogger("ai-service.graph.seed")


CREATE_CONSTRAINTS = [
    "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
    "CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT category_id_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.id IS UNIQUE",
]

WIPE = "MATCH (n) DETACH DELETE n"


def seed_graph(products: List[Dict[str, Any]], orders: List[Dict[str, Any]]) -> bool:
    """Build the graph in 4 phases:
       1. wipe + constraints
       2. Product + Category nodes
       3. User nodes + BOUGHT edges (from real orders)
       4. SIMILAR edges (from co-purchase + same-category) and VIEWED (synthetic)
    """
    drv = get_driver()
    if drv is None or not products:
        log.warning("Skipping graph seed (driver=%s, products=%d)", drv is not None, len(products))
        return False

    with drv.session() as s:
        s.run(WIPE)
        for q in CREATE_CONSTRAINTS:
            s.run(q)

        # Categories first.
        category_ids = {p.get("category_id") for p in products if p.get("category_id")}
        s.run(
            "UNWIND $cats AS cid "
            "MERGE (c:Category {id: cid})",
            cats=list(category_ids),
        )

        # Products.
        s.run(
            """
            UNWIND $products AS p
            MERGE (prod:Product {id: p.id})
              SET prod.name = p.name,
                  prod.price = p.price,
                  prod.product_type = p.product_type,
                  prod.category_id = p.category_id
            WITH prod, p
            MATCH (c:Category {id: p.category_id})
            MERGE (prod)-[:IN_CATEGORY]->(c)
            """,
            products=[
                {
                    "id": int(p["id"]),
                    "name": p.get("name", ""),
                    "price": float(p.get("price", 0)),
                    "product_type": p.get("product_type", "book"),
                    "category_id": p.get("category_id"),
                }
                for p in products
            ],
        )

        # Users + BOUGHT edges.
        bought_pairs: list[tuple[int, int, int]] = []
        co_purchase: dict[int, set[int]] = {}
        for o in orders:
            cust = o.get("customer_id")
            if cust is None:
                continue
            items = o.get("items") or []
            book_ids = [int(it["book_id"]) for it in items if it.get("book_id")]
            for bid in book_ids:
                bought_pairs.append((int(cust), bid, int(o.get("id", 0))))
                for other in book_ids:
                    if other != bid:
                        co_purchase.setdefault(bid, set()).add(other)

        if bought_pairs:
            s.run(
                """
                UNWIND $rows AS r
                MERGE (u:User {id: r.user_id})
                WITH u, r
                MATCH (p:Product {id: r.product_id})
                MERGE (u)-[b:BOUGHT]->(p)
                  ON CREATE SET b.first_order_id = r.order_id, b.count = 1
                  ON MATCH  SET b.count = coalesce(b.count, 0) + 1
                """,
                rows=[
                    {"user_id": uid, "product_id": pid, "order_id": oid}
                    for uid, pid, oid in bought_pairs
                ],
            )

        # SIMILAR edges from co-purchase signal.
        sim_rows = [
            {"a": a, "b": b, "weight": 1.0}
            for a, peers in co_purchase.items()
            for b in peers
        ]
        if sim_rows:
            s.run(
                """
                UNWIND $rows AS r
                MATCH (a:Product {id: r.a}), (b:Product {id: r.b})
                MERGE (a)-[s:SIMILAR]->(b)
                  ON CREATE SET s.weight = r.weight, s.source = 'co_purchase'
                  ON MATCH  SET s.weight = s.weight + r.weight
                """,
                rows=sim_rows,
            )

        # SIMILAR edges from shared category (lighter weight, transitive within category).
        s.run(
            """
            MATCH (a:Product)-[:IN_CATEGORY]->(c:Category)<-[:IN_CATEGORY]-(b:Product)
            WHERE a.id < b.id
            MERGE (a)-[s:SIMILAR]->(b)
              ON CREATE SET s.weight = 0.3, s.source = 'category'
              ON MATCH  SET s.weight = s.weight + 0.0   // keep co-purchase weight if present
            """
        )

        # VIEWED edges (synthetic — assume each user has viewed everything in
        # the categories they bought from). This gives the graph some
        # exploratory signal beyond explicit purchases.
        s.run(
            """
            MATCH (u:User)-[:BOUGHT]->(:Product)-[:IN_CATEGORY]->(c:Category)<-[:IN_CATEGORY]-(p:Product)
            WHERE NOT (u)-[:BOUGHT]->(p)
            MERGE (u)-[:VIEWED]->(p)
            """
        )

        # Quick sanity log.
        result = s.run(
            "MATCH (n) WITH labels(n) AS l, count(*) AS c RETURN l, c"
        )
        for record in result:
            log.info("Graph node count: %s = %d", record["l"], record["c"])

    return True
