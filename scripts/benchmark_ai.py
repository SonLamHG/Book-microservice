"""
AI Service Benchmark — ai-service port 8014

Measures each component independently then the hybrid:
  1. LSTM     — Hit Rate@K, coverage, latency via direct Python inference
  2. Graph    — Hit Rate@K, coverage, query latency via Neo4j HTTP
  3. RAG      — Semantic precision, intra/inter-category similarity, latency
  4. Hybrid   — End-to-end Hit Rate@K, NDCG@K, latency, component contribution

Leave-one-out protocol:
  For each user in user_behavior.csv, hold out the LAST product interaction
  as ground truth. Use the preceding interactions as context. Measure whether
  the held-out item appears in top-K recommendations.

Usage:
    py -3 scripts/benchmark_ai.py [--users N] [--topk K] [--verbose]

Options:
    --users N   max users to evaluate (default: 200, 0 = all)
    --topk  K   cutoff for Hit Rate / NDCG (default: 10)
    --verbose   print per-component details
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests

# ──────────────────────────────────────────────────────────
# Paths (relative to repo root)
# ──────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parent.parent
DATA_DIR       = REPO / "ai-service" / "data"
BEHAVIOR_CSV   = DATA_DIR / "user_behavior.csv"
CORPUS_JSONL   = DATA_DIR / "product_corpus.jsonl"

AI_BASE        = "http://localhost:8014"

# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────
class _Bench:
    def __init__(self, name: str):
        self.name = name
        self._times: List[float] = []

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *_):
        self._times.append((time.perf_counter() - self._t0) * 1000)

    def record(self, ms: float):
        self._times.append(ms)

    def stats(self) -> Dict[str, float]:
        if not self._times:
            return {}
        a = np.array(self._times)
        return {
            "n":    len(a),
            "mean": round(float(a.mean()), 1),
            "p50":  round(float(np.percentile(a, 50)), 1),
            "p95":  round(float(np.percentile(a, 95)), 1),
            "p99":  round(float(np.percentile(a, 99)), 1),
            "max":  round(float(a.max()), 1),
        }


def _bar(val: float, width: int = 20) -> str:
    filled = int(round(val * width))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _print_header(title: str):
    print(f"\n{'='*60}", flush=True)
    print(f"  {title}", flush=True)
    print(f"{'='*60}", flush=True)


def _print_metric(label: str, value, unit: str = "", note: str = ""):
    note_str = f"  ({note})" if note else ""
    print(f"  {label:<35} {value}{unit}{note_str}")


def _print_latency(bench: _Bench):
    s = bench.stats()
    if not s:
        print("  (no timing data)")
        return
    print(f"  Latency (ms, n={s['n']})")
    print(f"    mean={s['mean']}  p50={s['p50']}  p95={s['p95']}  p99={s['p99']}  max={s['max']}")


def _ndcg(recommended: List[int], relevant: int, k: int) -> float:
    for i, pid in enumerate(recommended[:k]):
        if pid == relevant:
            return 1.0 / math.log2(i + 2)
    return 0.0


# ──────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────
def load_behavior() -> Dict[int, List[int]]:
    """Return {user_id: [pid, pid, ...]} sorted by timestamp asc."""
    rows: Dict[int, List[Tuple[str, int]]] = defaultdict(list)
    with BEHAVIOR_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            uid  = int(row["user_id"])
            pid  = int(row["product_id"])
            ts   = row["timestamp"]
            rows[uid].append((ts, pid))
    return {uid: [pid for _, pid in sorted(v)] for uid, v in rows.items()}


def load_corpus() -> List[Dict[str, Any]]:
    with CORPUS_JSONL.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def build_loo_split(
    behavior: Dict[int, List[int]], max_users: int
) -> List[Tuple[int, List[int], int]]:
    """Leave-one-out: hold out last product, use rest as context.
    Returns list of (user_id, context_pids, target_pid)."""
    samples = []
    for uid, seq in behavior.items():
        if len(seq) < 2:
            continue
        samples.append((uid, seq[:-1], seq[-1]))
    if max_users and len(samples) > max_users:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(samples), max_users, replace=False)
        samples = [samples[i] for i in sorted(idx)]
    return samples


# ──────────────────────────────────────────────────────────
# 1. LSTM benchmark
# ──────────────────────────────────────────────────────────
def bench_lstm(samples: List[Tuple[int, List[int], int]], top_k: int, verbose: bool):
    _print_header("1. LSTM — next-product predictor")

    # Import directly (run from repo root, ai-service on PYTHONPATH via sys.path)
    sys.path.insert(0, str(REPO / "ai-service"))
    try:
        from app import config
        from app.datasets import load_product_corpus, load_user_behavior
        from app.lstm.inference import LSTMInference
    except ImportError as e:
        print(f"  [SKIP] Cannot import ai-service modules: {e}")
        print("  Run from repo root: py -3 scripts/benchmark_ai.py")
        return

    if not config.LSTM_WEIGHTS_PATH.exists():
        print("  [SKIP] No weights file found — run make train-ai first")
        return

    import torch
    checkpoint = torch.load(config.LSTM_WEIGHTS_PATH, map_location="cpu", weights_only=False)
    from app.lstm.model import LSTMModel
    from app.lstm.train import _seq_to_onehot

    num_products    = checkpoint["num_products"]
    hidden_dim      = checkpoint["hidden_dim"]
    seq_length      = checkpoint["seq_length"]
    prod_id_to_idx  = checkpoint["prod_id_to_idx"]
    idx_to_prod_id  = checkpoint["idx_to_prod_id"]

    model = LSTMModel(num_products, hidden_dim)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    _print_metric("Vocabulary (products + padding)", num_products)
    _print_metric("Hidden dim", hidden_dim)
    _print_metric("Sequence length", seq_length)

    bench_lat = _Bench("lstm_latency")
    hits_k    = {k: 0 for k in [1, 5, top_k]}
    ndcg_vals: List[float] = []
    n_covered = 0      # users LSTM returned any result for
    seen_pids: set     = set()
    n_total   = len(samples)

    for uid, ctx, target in samples:
        ctx_idx = [prod_id_to_idx.get(pid, 0) for pid in ctx[-seq_length:]]
        if not any(i != 0 for i in ctx_idx):
            continue

        t0 = time.perf_counter()
        x = _seq_to_onehot(ctx_idx, num_products, seq_length)
        with torch.no_grad():
            logits = model(torch.from_numpy(x).unsqueeze(0))
            probs  = torch.softmax(logits, dim=-1).squeeze(0).numpy()
        bench_lat.record((time.perf_counter() - t0) * 1000)

        ranked_idx = np.argsort(-probs)
        results: List[int] = []
        seen_ctx = set(ctx_idx)
        for i in ranked_idx:
            i = int(i)
            if i == 0 or i in seen_ctx:
                continue
            pid = idx_to_prod_id.get(i)
            if pid:
                results.append(pid)
                seen_pids.add(pid)
            if len(results) >= top_k:
                break

        if results:
            n_covered += 1

        for k in hits_k:
            if target in results[:k]:
                hits_k[k] += 1

        ndcg_vals.append(_ndcg(results, target, top_k))

    in_vocab = sum(1 for _, ctx, tgt in samples if prod_id_to_idx.get(tgt, 0) != 0)

    print()
    for k, hits in hits_k.items():
        rate = hits / n_total
        _print_metric(f"Hit Rate@{k:<3}", f"{rate:.3f}", f"  {_bar(rate)}",
                      f"{hits}/{n_total}")
    ndcg_mean = float(np.mean(ndcg_vals)) if ndcg_vals else 0.0
    _print_metric(f"NDCG@{top_k}", f"{ndcg_mean:.4f}")
    _print_metric("User coverage (got results)", f"{n_covered}/{n_total}",
                  f"  ({n_covered/n_total:.1%})")
    _print_metric("Target in vocabulary", f"{in_vocab}/{n_total}",
                  f"  ({in_vocab/n_total:.1%})")
    _print_metric("Unique products recommended", f"{len(seen_pids)}/{num_products-1}")
    _print_metric("Catalog coverage", f"{len(seen_pids)/(num_products-1):.1%}")
    print()
    _print_latency(bench_lat)

    if verbose:
        print("\n  Sample predictions for first 3 test users:")
        for uid, ctx, target in samples[:3]:
            ctx_idx = [prod_id_to_idx.get(pid, 0) for pid in ctx[-seq_length:]]
            x = _seq_to_onehot(ctx_idx, num_products, seq_length)
            with torch.no_grad():
                logits = model(torch.from_numpy(x).unsqueeze(0))
                probs  = torch.softmax(logits, dim=-1).squeeze(0).numpy()
            ranked = [idx_to_prod_id.get(int(i)) for i in np.argsort(-probs) if int(i) != 0]
            ranked = [p for p in ranked if p][:5]
            hit = "✓" if target in ranked else "✗"
            print(f"    user={uid}  target={target}  top5={ranked}  {hit}")


# ──────────────────────────────────────────────────────────
# 2. Graph benchmark
# ──────────────────────────────────────────────────────────
def bench_graph(samples: List[Tuple[int, List[int], int]], top_k: int, verbose: bool):
    _print_header("2. Knowledge Graph (Neo4j) — collaborative filtering")

    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("  [SKIP] neo4j driver not installed in host env")
        print("  Falling back to HTTP API endpoint...")
        return _bench_graph_http(samples, top_k, verbose)

    try:
        drv = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "bookstore-secret"))
        drv.verify_connectivity()
    except Exception as e:
        print(f"  [SKIP] Neo4j unreachable: {e}")
        return _bench_graph_http(samples, top_k, verbose)

    RECOMMEND_CYPHER = """
    MATCH (u:User {id: $user_id})-[b:BOUGHT]->(p:Product)-[s:SIMILAR]->(rec:Product)
    WHERE NOT (u)-[:BOUGHT]->(rec)
    WITH rec, sum(coalesce(b.count, 1) * coalesce(s.weight, 1.0)) AS score
    RETURN rec.id AS product_id, score
    ORDER BY score DESC LIMIT $top_k
    """
    POPULAR_CYPHER = """
    MATCH (:User)-[b:BOUGHT]->(p:Product)
    WITH p, sum(coalesce(b.count, 1)) AS popularity
    RETURN p.id AS product_id, popularity AS score
    ORDER BY score DESC LIMIT $top_k
    """

    bench_lat  = _Bench("graph_latency")
    hits_k     = {k: 0 for k in [1, 5, top_k]}
    ndcg_vals: List[float] = []
    n_covered  = 0
    n_personal = 0
    n_fallback = 0
    seen_pids: set = set()
    n_total    = len(samples)

    with drv.session() as s:
        # check graph stats
        n_users    = s.run("MATCH (u:User) RETURN count(u) AS c").single()["c"]
        n_products = s.run("MATCH (p:Product) RETURN count(p) AS c").single()["c"]
        n_bought   = s.run("MATCH ()-[b:BOUGHT]->() RETURN count(b) AS c").single()["c"]
        n_similar  = s.run("MATCH ()-[s:SIMILAR]->() RETURN count(s) AS c").single()["c"]

    _print_metric("Graph nodes — Users", n_users)
    _print_metric("Graph nodes — Products", n_products)
    _print_metric("Graph edges — BOUGHT", n_bought)
    _print_metric("Graph edges — SIMILAR", n_similar)
    _print_metric("Avg BOUGHT per user", f"{n_bought/max(n_users,1):.1f}")

    with drv.session() as s:
        for uid, ctx, target in samples:
            t0   = time.perf_counter()
            rows = s.run(RECOMMEND_CYPHER, user_id=uid, top_k=top_k * 4).data()
            if not rows:
                rows = s.run(POPULAR_CYPHER, top_k=top_k * 4).data()
                n_fallback += 1
            else:
                n_personal += 1
            bench_lat.record((time.perf_counter() - t0) * 1000)

            results = [int(r["product_id"]) for r in rows[:top_k]]
            seen_pids.update(results)

            if results:
                n_covered += 1
            for k in hits_k:
                if target in results[:k]:
                    hits_k[k] += 1
            ndcg_vals.append(_ndcg(results, target, top_k))

    drv.close()

    print()
    for k, hits in hits_k.items():
        rate = hits / n_total
        _print_metric(f"Hit Rate@{k:<3}", f"{rate:.3f}", f"  {_bar(rate)}", f"{hits}/{n_total}")
    ndcg_mean = float(np.mean(ndcg_vals)) if ndcg_vals else 0.0
    _print_metric(f"NDCG@{top_k}", f"{ndcg_mean:.4f}")
    _print_metric("User coverage (got results)", f"{n_covered}/{n_total}", f"  ({n_covered/n_total:.1%})")
    _print_metric("Personalised (BOUGHT history)", f"{n_personal}/{n_total}", f"  ({n_personal/n_total:.1%})")
    _print_metric("Fallback to popularity", f"{n_fallback}/{n_total}", f"  ({n_fallback/n_total:.1%})")
    _print_metric("Unique products recommended", f"{len(seen_pids)}/{n_products}")
    _print_metric("Catalog coverage", f"{len(seen_pids)/max(n_products,1):.1%}")
    print()
    _print_latency(bench_lat)


def _bench_graph_http(samples, top_k, verbose):
    """Fallback: use weight override w_graph=1,w_lstm=0,w_rag=0 for pure graph results."""
    try:
        requests.get(f"{AI_BASE}/health", timeout=3)
    except Exception as e:
        print(f"  [SKIP] ai-service unreachable: {e}")
        return

    bench_lat = _Bench("graph_http_latency")
    hits_k    = {k: 0 for k in [1, 5, top_k]}
    ndcg_vals: List[float] = []
    n_total   = min(len(samples), 100)
    n_personal = 0
    n_fallback = 0

    print("  Using weight override: w_lstm=0, w_graph=1, w_rag=0")
    for uid, ctx, target in samples[:n_total]:
        t0 = time.perf_counter()
        try:
            r = requests.get(
                f"{AI_BASE}/recommend",
                params={"user_id": uid, "w_lstm": 0, "w_graph": 1, "w_rag": 0},
                timeout=10,
            )
            recs = r.json().get("recommendations", [])
        except Exception:
            continue
        bench_lat.record((time.perf_counter() - t0) * 1000)

        results = [rec["product_id"] for rec in recs[:top_k]]
        # detect personalised vs fallback by checking if graph scores vary
        graph_scores = [rec["components"]["graph"] for rec in recs]
        if graph_scores and max(graph_scores) > 0:
            n_personal += 1
        else:
            n_fallback += 1

        for k in hits_k:
            if target in results[:k]:
                hits_k[k] += 1
        ndcg_vals.append(_ndcg(results, target, top_k))

    print()
    for k, hits in hits_k.items():
        rate = hits / n_total
        _print_metric(f"Hit Rate@{k:<3} (n={n_total})", f"{rate:.3f}", f"  {_bar(rate)}", f"{hits}/{n_total}")
    ndcg_mean = float(np.mean(ndcg_vals)) if ndcg_vals else 0.0
    _print_metric(f"NDCG@{top_k}", f"{ndcg_mean:.4f}")
    _print_metric("Personalised responses", f"{n_personal}/{n_total}", f"  ({n_personal/n_total:.1%})")
    _print_metric("Fallback (popularity)", f"{n_fallback}/{n_total}", f"  ({n_fallback/n_total:.1%})")
    _print_latency(bench_lat)


# ──────────────────────────────────────────────────────────
# 3. RAG benchmark
# ──────────────────────────────────────────────────────────
def bench_rag(corpus: List[Dict[str, Any]], top_k: int, verbose: bool, samples: Optional[List] = None):
    _print_header("3. RAG (FAISS + sentence-transformers) — semantic search")

    sys.path.insert(0, str(REPO / "ai-service"))
    try:
        from app.rag.index import FaissProductIndex
    except ImportError as e:
        print(f"  [SKIP] Direct FAISS eval skipped: {e}")
        print("  Falling back to leave-one-out evaluation via HTTP...")
        if samples is not None:
            _bench_rag_http(samples, corpus, top_k)
        return

    idx = FaissProductIndex()
    print("  Building FAISS index (loading sentence-transformers)...")
    t0 = time.perf_counter()
    idx.warmup(corpus)
    build_ms = (time.perf_counter() - t0) * 1000
    _print_metric("Index build time", f"{build_ms/1000:.1f}", "s")
    _print_metric("Products indexed", len(idx.products))
    _print_metric("Embedding model", "all-MiniLM-L6-v2 (384d)")

    # ---- Test queries with known-relevant books ----
    TEST_QUERIES: List[Tuple[str, List[str]]] = [
        ("python programming tutorial",
         ["Learning Python", "Python Cookbook", "Head First Python",
          "Fluent Python", "Programming Python"]),
        ("fantasy epic adventure tolkien",
         ["The Lord of the Rings", "The Hobbit", "The Fellowship of the Ring",
          "The Two Towers", "The Return of the King"]),
        ("business leadership management",
         ["Good to Great", "The 7 Habits", "How to Win Friends",
          "Rich Dad", "Who Moved My Cheese"]),
        ("self help personal development motivation",
         ["The Power of Habit", "Thinking Fast and Slow",
          "How to Win Friends & Influence People", "Outliers"]),
        ("children adventure magic school",
         ["Harry Potter", "The Giver", "A Wrinkle in Time"]),
        ("science physics universe cosmos",
         ["A Brief History of Time", "Cosmos", "The Universe in a Nutshell"]),
    ]

    bench_lat  = _Bench("rag_latency")
    query_hits = []

    print("\n  Semantic query relevance:")
    for query, relevant_keywords in TEST_QUERIES:
        t0 = time.perf_counter()
        results = idx.search(query, top_k=top_k)
        bench_lat.record((time.perf_counter() - t0) * 1000)

        if not results:
            query_hits.append(0.0)
            print(f"    '{query[:40]}' → (no results)")
            continue

        # Check if any result name contains a relevant keyword
        hit_at = None
        for i, r in enumerate(results[:top_k]):
            name_lower = r["name"].lower()
            if any(kw.lower() in name_lower for kw in relevant_keywords):
                hit_at = i + 1
                break

        precision = 1.0 if hit_at else 0.0
        query_hits.append(precision)
        top_names  = [r["name"][:35] for r in results[:3]]
        hit_str    = f"HIT@{hit_at}" if hit_at else "MISS"
        top_scores = [f"{r['score']:.3f}" for r in results[:3]]
        print(f"    [{hit_str}] '{query[:35]}'")
        if verbose:
            for i, (n, sc) in enumerate(zip(top_names, top_scores)):
                print(f"           #{i+1} {n}  ({sc})")

    semantic_precision = float(np.mean(query_hits))
    print()
    _print_metric("Semantic Precision (query hits)", f"{semantic_precision:.2f}",
                  f"  {_bar(semantic_precision)}", f"{sum(1 for h in query_hits if h)}/{len(query_hits)} queries")

    # ---- Intra vs inter-category cosine similarity ----
    print("\n  Intra vs Inter-category cosine similarity:")
    from sentence_transformers import SentenceTransformer
    cat_groups: Dict[int, List[str]] = defaultdict(list)
    for p in corpus:
        text = (
            f"BOOK | {p['name']} | by: {p.get('brand_or_author','')}"
            f" | {p.get('description','')[:200]}"
        )
        cat_groups[p["category_id"]].append(text)

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    intra_sims: List[float] = []
    inter_sims: List[float] = []
    cat_ids = sorted(cat_groups.keys())

    for cat_id in cat_ids:
        texts = cat_groups[cat_id][:20]  # sample 20 per category
        embs  = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        # intra: average pairwise cosine of same-category pairs
        for i in range(len(embs)):
            for j in range(i+1, len(embs)):
                intra_sims.append(float(np.dot(embs[i], embs[j])))

    # inter: sample across different categories
    cross_embs: Dict[int, np.ndarray] = {}
    for cat_id in cat_ids:
        texts = cat_groups[cat_id][:10]
        cross_embs[cat_id] = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    for i, c1 in enumerate(cat_ids):
        for c2 in cat_ids[i+1:]:
            for e1 in cross_embs[c1]:
                for e2 in cross_embs[c2]:
                    inter_sims.append(float(np.dot(e1, e2)))

    _print_metric("Intra-category cosine sim (mean)",
                  f"{np.mean(intra_sims):.4f}" if intra_sims else "n/a")
    _print_metric("Inter-category cosine sim (mean)",
                  f"{np.mean(inter_sims):.4f}" if inter_sims else "n/a")
    sep = float(np.mean(intra_sims) - np.mean(inter_sims)) if (intra_sims and inter_sims) else 0
    _print_metric("Separation (intra − inter)",
                  f"{sep:.4f}",
                  note="higher = better category clustering")

    print()
    _print_latency(bench_lat)
    # Also evaluate leave-one-out HR@K via HTTP for completeness
    if samples is not None:
        _bench_rag_http(samples, corpus, top_k)


def _bench_rag_http(samples: List[Tuple[int, List[int], int]], corpus: List[Dict[str, Any]], top_k: int):
    """Leave-one-out HR@K for RAG via HTTP using auto-generated title queries."""
    try:
        requests.get(f"{AI_BASE}/health", timeout=3)
    except Exception as e:
        print(f"\n  [SKIP] RAG HTTP eval — ai-service unreachable: {e}")
        return

    # Build pid → name lookup from corpus
    pid_to_name: Dict[int, str] = {
        int(p.get("product_id", p.get("id", 0))): p.get("name", "")
        for p in corpus
    }

    print("\n  Leave-one-out HR@K via HTTP (w_lstm=0, w_graph=0, w_rag=1):")
    bench_lat = _Bench("rag_http_latency")
    hits_k    = {k: 0 for k in [1, 5, top_k]}
    ndcg_vals: List[float] = []
    n_total   = min(len(samples), 100)
    n_query   = 0

    for uid, ctx, target in samples[:n_total]:
        # Build query from last 3 context product names
        names = [pid_to_name[pid] for pid in ctx[-3:] if pid in pid_to_name]
        query = " ".join(filter(None, names))
        if not query:
            continue
        n_query += 1

        t0 = time.perf_counter()
        try:
            r = requests.get(
                f"{AI_BASE}/recommend",
                params={"user_id": uid, "query": query, "w_lstm": 0, "w_graph": 0, "w_rag": 1},
                timeout=10,
            )
            recs = r.json().get("recommendations", [])
        except Exception:
            continue
        bench_lat.record((time.perf_counter() - t0) * 1000)

        results = [rec["product_id"] for rec in recs[:top_k]]
        for k in hits_k:
            if target in results[:k]:
                hits_k[k] += 1
        ndcg_vals.append(_ndcg(results, target, top_k))

    for k, hits in hits_k.items():
        rate = hits / max(n_query, 1)
        _print_metric(f"Hit Rate@{k:<3} (n={n_query})", f"{rate:.3f}", f"  {_bar(rate)}", f"{hits}/{n_query}")
    ndcg_mean = float(np.mean(ndcg_vals)) if ndcg_vals else 0.0
    _print_metric(f"NDCG@{top_k}", f"{ndcg_mean:.4f}")
    _print_latency(bench_lat)


# ──────────────────────────────────────────────────────────
# 4. Hybrid benchmark (via HTTP)
# ──────────────────────────────────────────────────────────
def bench_hybrid(samples: List[Tuple[int, List[int], int]], top_k: int, verbose: bool):
    _print_header("4. Hybrid Recommender — end-to-end via HTTP")
    print("  (With fixes: LSTM falls back to behavior.csv; RAG auto-activated from history)")

    try:
        r = requests.get(f"{AI_BASE}/health", timeout=5)
        info = r.json()
        _print_metric("Service status", info.get("status"))
        _print_metric("LSTM loaded", info.get("lstm_loaded"))
        _print_metric("FAISS indexed", info.get("faiss_indexed"))
        _print_metric("Products in index", info.get("products_in_index"))
    except Exception as e:
        print(f"  [SKIP] ai-service unreachable: {e}")
        return

    bench_lat   = _Bench("hybrid_latency")
    hits_k      = {k: 0 for k in [1, 5, top_k]}
    ndcg_vals:  List[float] = []
    contrib:    Dict[str, List[float]] = {"lstm": [], "graph": [], "rag": []}
    n_covered   = 0
    n_total     = len(samples)

    # Only send up to 200 HTTP calls to keep benchmark fast
    eval_samples = samples[:200]

    for uid, ctx, target in eval_samples:
        t0 = time.perf_counter()
        try:
            resp = requests.get(f"{AI_BASE}/recommend",
                                params={"user_id": uid}, timeout=15)
            recs = resp.json().get("recommendations", [])
        except Exception:
            continue
        bench_lat.record((time.perf_counter() - t0) * 1000)

        results = [r["product_id"] for r in recs]
        if results:
            n_covered += 1

        for k in hits_k:
            if target in results[:k]:
                hits_k[k] += 1
        ndcg_vals.append(_ndcg(results, target, top_k))

        # component contribution: how much each component contributed on average
        for rec in recs:
            for comp in contrib:
                contrib[comp].append(rec["components"].get(comp, 0.0))

    n_eval = len(eval_samples)
    print()
    for k, hits in hits_k.items():
        rate = hits / n_eval
        _print_metric(f"Hit Rate@{k:<3}", f"{rate:.3f}", f"  {_bar(rate)}", f"{hits}/{n_eval}")
    ndcg_mean = float(np.mean(ndcg_vals)) if ndcg_vals else 0.0
    _print_metric(f"NDCG@{top_k}", f"{ndcg_mean:.4f}")
    _print_metric("User coverage (got results)", f"{n_covered}/{n_eval}",
                  f"  ({n_covered/n_eval:.1%})")

    print("\n  Component contribution (avg normalised score):")
    for comp, vals in contrib.items():
        mean = float(np.mean(vals)) if vals else 0.0
        _print_metric(f"  {comp}", f"{mean:.4f}", f"  {_bar(mean)}")

    print()
    _print_latency(bench_lat)

    # ---- Hybrid vs single-component comparison (first 50 samples) ----
    print("\n  Weight sensitivity (first 50 samples):")
    configs = [
        ("LSTM only",        {"lstm": 1.0, "graph": 0.0, "rag": 0.0}),
        ("Graph only",       {"lstm": 0.0, "graph": 1.0, "rag": 0.0}),
        ("RAG only",         {"lstm": 0.0, "graph": 0.0, "rag": 1.0}),
        ("Equal (1/3 each)", {"lstm": 0.33, "graph": 0.33, "rag": 0.34}),
        ("Old (0.4/0.4/0.2)",{"lstm": 0.4, "graph": 0.4, "rag": 0.2}),
        ("New (0.2/0.1/0.7)",{"lstm": 0.2, "graph": 0.1, "rag": 0.7}),
    ]
    sub_samples = samples[:50]
    for label, w in configs:
        hits = 0
        for uid, ctx, target in sub_samples:
            try:
                resp = requests.get(
                    f"{AI_BASE}/recommend",
                    params={"user_id": uid, "w_lstm": w["lstm"],
                            "w_graph": w["graph"], "w_rag": w["rag"]},
                    timeout=15,
                )
                recs = resp.json().get("recommendations", [])
                if target in [r["product_id"] for r in recs[:top_k]]:
                    hits += 1
            except Exception:
                pass
        rate = hits / len(sub_samples)
        _print_metric(f"  {label:<25} HR@{top_k}", f"{rate:.3f}", f"  {_bar(rate)}")


# ──────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Benchmark ai-service components")
    parser.add_argument("--users", type=int, default=200,
                        help="Max users for evaluation (0 = all)")
    parser.add_argument("--topk",  type=int, default=10,
                        help="Recommendation cutoff K")
    parser.add_argument("--verbose", action="store_true",
                        help="Print per-query details")
    parser.add_argument("--only",
                        help="Run only one component: lstm|graph|rag|hybrid")
    args = parser.parse_args()

    if not BEHAVIOR_CSV.exists():
        sys.exit(f"ERROR: {BEHAVIOR_CSV} not found — run make preprocess first")

    print(f"\nBookStore AI Benchmark")
    print(f"  behavior rows : {sum(1 for _ in open(BEHAVIOR_CSV, encoding='utf-8'))-1:,}")
    print(f"  max users     : {args.users or 'all'}")
    print(f"  top-K cutoff  : {args.topk}")

    behavior = load_behavior()
    corpus   = load_corpus()
    samples  = build_loo_split(behavior, args.users)

    print(f"  test samples  : {len(samples)} (leave-one-out users)")
    print(f"  corpus size   : {len(corpus)} products")

    only = (args.only or "").lower()

    if not only or only == "lstm":
        bench_lstm(samples, args.topk, args.verbose)

    if not only or only == "graph":
        bench_graph(samples, args.topk, args.verbose)

    if not only or only == "rag":
        bench_rag(corpus, args.topk, args.verbose, samples=samples)

    if not only or only == "hybrid":
        bench_hybrid(samples, args.topk, args.verbose)

    print(f"\n{'='*60}")
    print("  Benchmark complete.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
