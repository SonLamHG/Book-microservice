"""Generate the two training datasets:
  - user_behavior.csv : Synthetic but realistic user-behavior log used by
                        the LSTM training pipeline.
  - graph_triples.csv : Explicit (User, Product, Category) nodes + edges
                        consumed by Neo4j seed.

Both are derived from a fixed seed (42) so the output is reproducible.
The third dataset, product_corpus.jsonl, is hand-curated and committed
alongside this file — not regenerated here.

Run:  python generate_datasets.py
"""
from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
CORPUS_PATH    = DATA_DIR / "product_corpus.jsonl"
BEHAVIOR_PATH  = DATA_DIR / "user_behavior.csv"
TRIPLES_PATH   = DATA_DIR / "graph_triples.csv"

# ---------------------------------------------------------------------
# Personas — anchor user interests to make the dataset realistic.
# Each entry maps customer_id → list of preferred category_ids.
# ---------------------------------------------------------------------
PERSONAS = {
    1: {  # Nguyen Van A — Literature lover
        "name": "Nguyen Van A",
        "categories": [1, 4, 5],
        "weight": {1: 0.5, 4: 0.3, 5: 0.2},
    },
    2: {  # Tran Thi B — Software engineer
        "name": "Tran Thi B",
        "categories": [2, 7, 6],
        "weight": {2: 0.55, 7: 0.30, 6: 0.15},
    },
    3: {  # Le Van C — Business + casual tech
        "name": "Le Van C",
        "categories": [3, 2, 5],
        "weight": {3: 0.5, 2: 0.3, 5: 0.2},
    },
    4: {  # Pham Thi D — Lifestyle / fashion
        "name": "Pham Thi D",
        "categories": [9, 5, 4],
        "weight": {9: 0.55, 5: 0.25, 4: 0.20},
    },
    5: {  # Hoang E — Gadget enthusiast
        "name": "Hoang E",
        "categories": [6, 7, 8],
        "weight": {6: 0.50, 7: 0.30, 8: 0.20},
    },
}

# ---------------------------------------------------------------------
# Real purchases from seed_data.sql (these MUST appear as purchase
# events in the behavior log so the dataset is consistent with the
# rest of the system).
# ---------------------------------------------------------------------
SEED_PURCHASES = [
    # (customer_id, [product_ids])
    (1, [1, 3, 5, 15]),   # order 1
    (2, [6]),             # order 2
    (1, [4, 9]),          # order 3 (customer 1 also bought from order 3? No — order 3 is customer_id=1 in seed_data.sql)
]


def load_products():
    products = []
    with CORPUS_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                products.append(json.loads(line))
    return products


def by_category(products):
    out = defaultdict(list)
    for p in products:
        out[p["category_id"]].append(p["product_id"])
    return out


def generate_behavior():
    rng = random.Random(42)
    products = load_products()
    cat_to_pids = by_category(products)

    # Behaviour log starts 30 days ago, evenly spread.
    start = datetime(2026, 4, 1, 8, 0, 0)
    rows = []

    for cust_id, persona in PERSONAS.items():
        cat_weight = persona["weight"]

        # 1) Browsing — 30–45 view events.
        n_views = rng.randint(30, 45)
        for _ in range(n_views):
            # weighted category choice
            cats = list(cat_weight.keys())
            weights = list(cat_weight.values())
            cat = rng.choices(cats, weights=weights, k=1)[0]
            if not cat_to_pids[cat]:
                continue
            pid = rng.choice(cat_to_pids[cat])
            ts = start + timedelta(
                days=rng.randint(0, 29),
                hours=rng.randint(7, 23),
                minutes=rng.randint(0, 59),
            )
            rows.append((cust_id, pid, "view", ts))

        # 2) Click — 30–50 % of distinct viewed products.
        distinct_viewed = list({r[1] for r in rows if r[0] == cust_id})
        rng.shuffle(distinct_viewed)
        n_clicks = max(3, int(len(distinct_viewed) * rng.uniform(0.30, 0.50)))
        for pid in distinct_viewed[:n_clicks]:
            ts = start + timedelta(
                days=rng.randint(0, 29),
                hours=rng.randint(8, 23),
                minutes=rng.randint(0, 59),
            )
            rows.append((cust_id, pid, "click", ts))

        # 3) Add-to-cart — small subset of clicked.
        clicked = [r[1] for r in rows if r[0] == cust_id and r[2] == "click"]
        n_carts = rng.randint(3, min(6, len(clicked) or 3))
        for pid in rng.sample(clicked, k=min(n_carts, len(clicked))):
            ts = start + timedelta(
                days=rng.randint(0, 29),
                hours=rng.randint(9, 22),
                minutes=rng.randint(0, 59),
            )
            rows.append((cust_id, pid, "add_to_cart", ts))

    # 4) Real purchases (anchored to seed_data.sql).
    for cust_id, pids in SEED_PURCHASES:
        for pid in pids:
            # ensure full funnel exists before the purchase
            base_ts = start + timedelta(days=rng.randint(20, 28),
                                        hours=rng.randint(10, 20))
            for offset, action in enumerate(["view", "click", "add_to_cart", "purchase"]):
                rows.append((cust_id, pid, action,
                             base_ts + timedelta(minutes=5 * offset)))

    # Sort by timestamp for readability.
    rows.sort(key=lambda r: (r[3], r[0]))

    with BEHAVIOR_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["user_id", "product_id", "action", "timestamp"])
        for r in rows:
            w.writerow([r[0], r[1], r[2], r[3].isoformat()])

    print(f"  {BEHAVIOR_PATH.name:30s}  {len(rows):5d} rows")
    return rows


def generate_graph_triples(behavior_rows):
    """Schema: source_type, source_id, edge_type, target_type, target_id, weight"""
    products = load_products()
    triples = []

    # 1) IN_CATEGORY edges (Product → Category).
    for p in products:
        triples.append(("Product", p["product_id"], "IN_CATEGORY",
                        "Category", p["category_id"], 1.0))

    # 2) BOUGHT edges (User → Product) aggregated.
    bought_counts = defaultdict(int)
    for uid, pid, action, ts in behavior_rows:
        if action == "purchase":
            bought_counts[(uid, pid)] += 1
    for (uid, pid), cnt in bought_counts.items():
        triples.append(("User", uid, "BOUGHT", "Product", pid, float(cnt)))

    # 3) VIEWED edges (User → Product) aggregated.
    view_counts = defaultdict(int)
    for uid, pid, action, ts in behavior_rows:
        if action in ("view", "click"):
            view_counts[(uid, pid)] += 1
    for (uid, pid), cnt in view_counts.items():
        triples.append(("User", uid, "VIEWED", "Product", pid, float(cnt)))

    # 4) SIMILAR edges (co-purchase) — products purchased by same user.
    user_purchases = defaultdict(set)
    for uid, pid, action, ts in behavior_rows:
        if action == "purchase":
            user_purchases[uid].add(pid)
    sim_weights = defaultdict(float)
    for pids in user_purchases.values():
        for a in pids:
            for b in pids:
                if a != b:
                    sim_weights[(a, b)] += 1.0
    for (a, b), w in sim_weights.items():
        triples.append(("Product", a, "SIMILAR", "Product", b, w))

    # 5) SIMILAR edges (same category) — lighter weight.
    by_cat = defaultdict(list)
    for p in products:
        by_cat[p["category_id"]].append(p["product_id"])
    for pids in by_cat.values():
        for a in pids:
            for b in pids:
                if a < b:
                    if (a, b) not in sim_weights:
                        triples.append(("Product", a, "SIMILAR",
                                        "Product", b, 0.3))

    with TRIPLES_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_type", "source_id", "edge_type",
                    "target_type", "target_id", "weight"])
        for t in triples:
            w.writerow(t)

    print(f"  {TRIPLES_PATH.name:30s}  {len(triples):5d} rows")
    return triples


if __name__ == "__main__":
    print("Generating AI training datasets (deterministic, seed=42)...")
    rows = generate_behavior()
    generate_graph_triples(rows)
    print("Done.")
