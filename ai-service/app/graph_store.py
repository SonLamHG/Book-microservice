from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations

from neo4j import GraphDatabase


@dataclass
class GraphConfig:
    uri: str
    user: str
    password: str
    database: str
    enabled: bool


class GraphStore:
    def __init__(self, config: GraphConfig):
        self.config = config
        self.driver = None
        if config.enabled:
            self.driver = GraphDatabase.driver(config.uri, auth=(config.user, config.password))

    @classmethod
    def from_env(cls) -> "GraphStore":
        enabled = os.getenv("NEO4J_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
        cfg = GraphConfig(
            uri=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "neo4jpassword"),
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
            enabled=enabled,
        )
        return cls(cfg)

    @property
    def ready(self) -> bool:
        return self.driver is not None

    def ensure_schema(self) -> None:
        if not self.ready:
            return
        with self.driver.session(database=self.config.database) as session:
            session.run("CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
            session.run("CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE")
            session.run("CREATE CONSTRAINT category_slug_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.slug IS UNIQUE")

    def ping(self) -> bool:
        if not self.ready:
            return False
        with self.driver.session(database=self.config.database) as session:
            rec = session.run("RETURN 1 AS ok").single()
            return bool(rec and rec["ok"] == 1)

    def upsert_event(self, user_id: int, product_id: int | None, action: str, timestamp: datetime) -> None:
        if not self.ready or product_id is None:
            return
        ts = timestamp.isoformat()
        query = """
        MERGE (u:User {id: $user_id})
        MERGE (p:Product {id: $product_id})
        MERGE (u)-[r:INTERACTED {action: $action}]->(p)
        ON CREATE SET r.count = 1, r.first_at = datetime($ts), r.last_at = datetime($ts)
        ON MATCH SET  r.count = r.count + 1, r.last_at = datetime($ts)
        """
        with self.driver.session(database=self.config.database) as session:
            session.run(query, user_id=user_id, product_id=product_id, action=action, ts=ts)

    def sync_products(self, products: list[dict]) -> int:
        if not self.ready:
            return 0

        records = []
        for p in products:
            if "id" not in p:
                continue
            category = p.get("category") or {}
            records.append(
                {
                    "product_id": int(p["id"]),
                    "name": str(p.get("name") or ""),
                    "price": float(p.get("price") or 0.0),
                    "category_slug": str(category.get("slug") or "uncategorized"),
                    "category_name": str(category.get("name") or "Uncategorized"),
                }
            )

        if not records:
            return 0

        query = """
        UNWIND $rows AS row
        MERGE (p:Product {id: row.product_id})
        SET p.name = row.name,
            p.price = row.price,
            p.updated_at = datetime()
        MERGE (c:Category {slug: row.category_slug})
        SET c.name = row.category_name
        MERGE (p)-[:BELONGS_TO_CATEGORY]->(c)
        """
        with self.driver.session(database=self.config.database) as session:
            session.run(query, rows=records)
        return len(records)

    def _clear_for_rebuild(self, reset: bool) -> None:
        if not self.ready:
            return
        with self.driver.session(database=self.config.database) as session:
            if reset:
                session.run("MATCH (n) DETACH DELETE n")
            else:
                session.run(
                    """
                    MATCH ()-[r:INTERACTED|VIEWED_AFTER|BOUGHT_WITH|SIMILAR|BELONGS_TO_CATEGORY]->()
                    DELETE r
                    """
                )
                session.run("MATCH (c:Category) DETACH DELETE c")

    def _build_viewed_after(self, events: list[object]) -> int:
        seq_rows: list[dict] = []
        events_by_user: dict[int, list[object]] = defaultdict(list)
        for e in events:
            if getattr(e, "product_id", None) is None:
                continue
            events_by_user[int(getattr(e, "user_id"))].append(e)

        pair_count: dict[tuple[int, int], int] = defaultdict(int)
        for _user, rows in events_by_user.items():
            rows_sorted = sorted(rows, key=lambda x: getattr(x, "timestamp"))
            for idx in range(1, len(rows_sorted)):
                prev_pid = int(getattr(rows_sorted[idx - 1], "product_id"))
                cur_pid = int(getattr(rows_sorted[idx], "product_id"))
                if prev_pid == cur_pid:
                    continue
                pair_count[(prev_pid, cur_pid)] += 1

        for (src, dst), cnt in pair_count.items():
            seq_rows.append({"src": src, "dst": dst, "count": cnt})

        if not seq_rows:
            return 0

        with self.driver.session(database=self.config.database) as session:
            session.run(
                """
                UNWIND $rows AS row
                MATCH (p1:Product {id: row.src}), (p2:Product {id: row.dst})
                MERGE (p1)-[r:VIEWED_AFTER]->(p2)
                SET r.count = row.count,
                    r.updated_at = datetime()
                """,
                rows=seq_rows,
            )
        return len(seq_rows)

    def _build_bought_with(self, events: list[object]) -> int:
        purchases_by_user: dict[int, set[int]] = defaultdict(set)
        for e in events:
            if str(getattr(e, "action", "")).lower() != "purchase":
                continue
            pid = getattr(e, "product_id", None)
            if pid is None:
                continue
            purchases_by_user[int(getattr(e, "user_id"))].add(int(pid))

        pair_count: dict[tuple[int, int], int] = defaultdict(int)
        for product_ids in purchases_by_user.values():
            if len(product_ids) < 2:
                continue
            for a, b in combinations(sorted(product_ids), 2):
                pair_count[(a, b)] += 1

        rows = [{"a": a, "b": b, "count": c} for (a, b), c in pair_count.items()]
        if not rows:
            return 0

        with self.driver.session(database=self.config.database) as session:
            session.run(
                """
                UNWIND $rows AS row
                MATCH (p1:Product {id: row.a}), (p2:Product {id: row.b})
                MERGE (p1)-[r:BOUGHT_WITH]->(p2)
                SET r.count = row.count,
                    r.updated_at = datetime()
                """,
                rows=rows,
            )
        return len(rows)

    def _build_similar(self) -> int:
        if not self.ready:
            return 0
        query = """
        MATCH (p1:Product)<-[:INTERACTED]-(:User)-[:INTERACTED]->(p2:Product)
        WHERE p1.id < p2.id
        WITH p1, p2, COUNT(*) AS common_interactions
        WHERE common_interactions >= 1
        MERGE (p1)-[s:SIMILAR]->(p2)
        SET s.score = common_interactions,
            s.updated_at = datetime()
        RETURN COUNT(s) AS c
        """
        with self.driver.session(database=self.config.database) as session:
            rec = session.run(query).single()
            return int(rec["c"]) if rec and rec.get("c") is not None else 0

    def rebuild_from_events(self, events: list[object], products: list[dict], reset: bool = False) -> dict:
        if not self.ready:
            return {"events": 0, "products": 0, "viewed_after": 0, "bought_with": 0, "similar": 0}

        self._clear_for_rebuild(reset=reset)
        self.ensure_schema()
        product_count = self.sync_products(products)

        ingested = 0
        with self.driver.session(database=self.config.database) as session:
            for e in events:
                product_id = getattr(e, "product_id", None)
                if product_id is None:
                    continue
                ts = getattr(e, "timestamp")
                if hasattr(ts, "isoformat"):
                    ts = ts.isoformat()
                session.run(
                    """
                    MERGE (u:User {id: $user_id})
                    MERGE (p:Product {id: $product_id})
                    MERGE (u)-[r:INTERACTED {action: $action}]->(p)
                    ON CREATE SET r.count = 1, r.first_at = datetime($ts), r.last_at = datetime($ts)
                    ON MATCH SET  r.count = r.count + 1, r.last_at = datetime($ts)
                    """,
                    user_id=int(getattr(e, "user_id")),
                    product_id=int(product_id),
                    action=str(getattr(e, "action")),
                    ts=ts,
                )
                ingested += 1

        viewed_after_count = self._build_viewed_after(events)
        bought_with_count = self._build_bought_with(events)
        similar_count = self._build_similar()

        return {
            "events": ingested,
            "products": product_count,
            "viewed_after": viewed_after_count,
            "bought_with": bought_with_count,
            "similar": similar_count,
        }

    def recommend(self, user_id: int, limit: int = 10) -> dict[int, float]:
        if not self.ready:
            return {}

        query = """
        MATCH (u:User {id: $user_id})-[:INTERACTED]->(p:Product)
        WITH COLLECT(DISTINCT p.id) AS touched_ids
        CALL {
          WITH touched_ids
          UNWIND touched_ids AS pid
          MATCH (p:Product {id: pid})-[s:SIMILAR]-(rec:Product)
          WHERE NOT rec.id IN touched_ids
          RETURN rec.id AS rid, SUM(COALESCE(s.score, 0)) * 1.2 AS part
          UNION ALL
          WITH touched_ids
          UNWIND touched_ids AS pid
          MATCH (p:Product {id: pid})-[bw:BOUGHT_WITH]-(rec:Product)
          WHERE NOT rec.id IN touched_ids
          RETURN rec.id AS rid, SUM(COALESCE(bw.count, 0)) * 1.0 AS part
          UNION ALL
          WITH touched_ids
          UNWIND touched_ids AS pid
          MATCH (p:Product {id: pid})-[v:VIEWED_AFTER]->(rec:Product)
          WHERE NOT rec.id IN touched_ids
          RETURN rec.id AS rid, SUM(COALESCE(v.count, 0)) * 0.8 AS part
        }
        WITH rid AS product_id, SUM(part) AS score
        ORDER BY score DESC
        LIMIT $limit
        RETURN product_id, score
        """
        with self.driver.session(database=self.config.database) as session:
            rows = session.run(query, user_id=user_id, limit=limit)
            return {int(r["product_id"]): float(r["score"]) for r in rows}

    def rag_retrieve(self, user_id: int, limit: int = 12) -> list[dict]:
        """
        Retrieve candidate products and evidence from KB_Graph for RAG-style chatbot response.
        """
        if not self.ready:
            return []

        query = """
        MATCH (u:User {id: $user_id})-[:INTERACTED]->(t:Product)
        WITH COLLECT(DISTINCT t.id) AS touched
        CALL {
          WITH touched
          UNWIND touched AS pid
          MATCH (p:Product {id: pid})-[r:SIMILAR]-(cand:Product)
          WHERE NOT cand.id IN touched
          RETURN cand.id AS product_id, 'SIMILAR' AS rel, SUM(COALESCE(r.score, 0)) AS rel_score, COLLECT(DISTINCT pid)[0..3] AS sources
          UNION ALL
          WITH touched
          UNWIND touched AS pid
          MATCH (p:Product {id: pid})-[r:VIEWED_AFTER]->(cand:Product)
          WHERE NOT cand.id IN touched
          RETURN cand.id AS product_id, 'VIEWED_AFTER' AS rel, SUM(COALESCE(r.count, 0)) AS rel_score, COLLECT(DISTINCT pid)[0..3] AS sources
          UNION ALL
          WITH touched
          UNWIND touched AS pid
          MATCH (p:Product {id: pid})-[r:BOUGHT_WITH]-(cand:Product)
          WHERE NOT cand.id IN touched
          RETURN cand.id AS product_id, 'BOUGHT_WITH' AS rel, SUM(COALESCE(r.count, 0)) AS rel_score, COLLECT(DISTINCT pid)[0..3] AS sources
          UNION ALL
          WITH touched
          UNWIND touched AS pid
          MATCH (p:Product {id: pid})-[:BELONGS_TO_CATEGORY]->(c:Category)<-[:BELONGS_TO_CATEGORY]-(cand:Product)
          WHERE NOT cand.id IN touched AND cand.id <> pid
          RETURN cand.id AS product_id, 'SAME_CATEGORY' AS rel, COUNT(*) * 1.0 AS rel_score, COLLECT(DISTINCT pid)[0..3] AS sources
        }
        RETURN product_id, rel, rel_score, sources
        """
        rel_weight = {
            "SIMILAR": 1.4,
            "VIEWED_AFTER": 0.8,
            "BOUGHT_WITH": 1.2,
            "SAME_CATEGORY": 0.6,
        }
        evidence_map = {
            "SIMILAR": "tương đồng sản phẩm (SIMILAR)",
            "VIEWED_AFTER": "chuỗi xem tiếp theo (VIEWED_AFTER)",
            "BOUGHT_WITH": "xu hướng mua kèm (BOUGHT_WITH)",
            "SAME_CATEGORY": "cùng danh mục đã quan tâm",
        }

        bucket: dict[int, dict] = {}
        with self.driver.session(database=self.config.database) as session:
            rows = session.run(query, user_id=user_id)
            for r in rows:
                pid = int(r["product_id"])
                rel = str(r["rel"])
                score = float(r["rel_score"] or 0.0) * rel_weight.get(rel, 1.0)
                sources = [int(x) for x in (r["sources"] or [])]

                item = bucket.setdefault(
                    pid,
                    {
                        "product_id": pid,
                        "score": 0.0,
                        "evidence": set(),
                        "source_products": set(),
                    },
                )
                item["score"] += score
                item["evidence"].add(evidence_map.get(rel, rel))
                item["source_products"].update(sources)

        out = []
        for item in bucket.values():
            out.append(
                {
                    "product_id": item["product_id"],
                    "score": float(item["score"]),
                    "evidence": sorted(item["evidence"]),
                    "source_products": sorted(item["source_products"]),
                }
            )
        out.sort(key=lambda x: x["score"], reverse=True)
        return out[:limit]
