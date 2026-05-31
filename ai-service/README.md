# ai-service

FastAPI service implementing the **hybrid recommender** required by the
SoAD thesis Ch.3:

> `final_score = w1·LSTM + w2·Graph + w3·RAG`

| Component | Tech | Source |
|---|---|---|
| **LSTM** | PyTorch (`nn.LSTM(input_dim=N, hidden_dim=64) → nn.Linear`) | `app/lstm/` |
| **Knowledge Graph** | Neo4j 5 + Bolt driver | `app/graph/` |
| **RAG** | FAISS `IndexFlatIP` + `sentence-transformers/all-MiniLM-L6-v2` (384d) | `app/rag/` |
| **Hybrid scoring** | min-max normalised, weighted sum | `app/hybrid.py` |
| **API** | FastAPI 0.115 + uvicorn | `main.py`, `app/routes/` |

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET`  | `/health` | Service + model status |
| `GET`  | `/recommend?user_id=&query=&top_k=` | Hybrid recommendation list |
| `POST` | `/chatbot` `{ "query": "...", "top_k": 5 }` | RAG chatbot — retrieve + (optional LLM) generate |

## Quickstart (via the existing docker-compose)

```bash
# Build everything
docker-compose up --build -d

# Wait ~60s on first run — sentence-transformers downloads the embedding
# model (~80 MB) on the first request, and the LSTM trains on synthetic
# sequences derived from product-service + order-service data.

# Sanity check
curl http://localhost:8014/health
curl "http://localhost:8014/recommend?user_id=1&top_k=5"
curl -X POST http://localhost:8014/chatbot \
  -H "Content-Type: application/json" \
  -d '{"query": "tôi cần laptop gaming dưới 40 triệu", "top_k": 5}'

# Through the Nginx gateway (single entry point)
curl "http://localhost:8080/api/ai/recommend?user_id=1"
curl -X POST http://localhost:8080/api/ai/chatbot \
  -H "Content-Type: application/json" \
  -d '{"query":"sách lập trình Python","top_k":3}'
```

## Configuration (env vars)

| Var | Default | What it does |
|---|---|---|
| `PRODUCT_SERVICE_URL` | `http://product-service:8000` | Source of products at startup |
| `ORDER_SERVICE_URL` | `http://order-service:8000` | Source of co-purchase signal |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | `bolt://neo4j:7687` / `neo4j` / `bookstore-secret` | Knowledge Graph |
| `LSTM_HIDDEN_DIM` | `64` | LSTM hidden state size |
| `LSTM_SEQ_LENGTH` | `5` | Window of recent interactions fed to the LSTM |
| `LSTM_EPOCHS` | `30` | Synthetic-data training epochs |
| `LSTM_TRAIN_AT_STARTUP` | `true` | Set `false` in prod once weights are persisted |
| `EMBED_MODEL_NAME` | `sentence-transformers/all-MiniLM-L6-v2` | Embedder for FAISS |
| `W_LSTM` / `W_GRAPH` / `W_RAG` | `0.4` / `0.4` / `0.2` | Hybrid scoring weights |
| `OPENAI_API_KEY` | *(unset)* | If set, chatbot uses GPT-4o-mini; else templated answer |

## Knowledge-graph topology

After the seed step the graph contains:

```
(:User {id})
  -[:BOUGHT  {first_order_id, count}]→ (:Product)
  -[:VIEWED]→                          (:Product)

(:Product {id, name, price, product_type, category_id})
  -[:IN_CATEGORY]→ (:Category {id})
  -[:SIMILAR {weight, source}]→ (:Product)
        # source = "co_purchase"  (weight ≥ 1.0, accumulates per pair)
        # source = "category"     (weight 0.3, intra-category edges)
```

Recommendation Cypher (see `app/graph/queries.py`):

```cypher
MATCH (u:User {id: $user_id})-[b:BOUGHT]->(p:Product)-[s:SIMILAR]->(rec:Product)
WHERE NOT (u)-[:BOUGHT]->(rec)
WITH rec, sum(coalesce(b.count,1) * coalesce(s.weight,1.0)) AS score
RETURN rec.id, rec.name, score ORDER BY score DESC LIMIT $top_k
```

You can browse the graph at <http://localhost:7474> (login: `neo4j` / `bookstore-secret`).

## Training datasets (committed to repo)

Three real on-disk datasets feed the three AI components. They live in
`ai-service/data/` and are committed to git so the training pipeline
is fully reproducible:

| File | Schema | Rows | Consumed by |
|---|---|---|---|
| `product_corpus.jsonl` | one JSON per line: `{product_id, name, type, category, price, brand_or_author, description, keywords[]}` | 27 | FAISS (embedding + metadata source-of-truth) |
| `user_behavior.csv` | `user_id, product_id, action, timestamp` (action ∈ view/click/add_to_cart/purchase) | 237 | LSTM (sliding-window sequences) |
| `graph_triples.csv` | `source_type, source_id, edge_type, target_type, target_id, weight` (edge ∈ IN_CATEGORY/BOUGHT/VIEWED/SIMILAR) | 134 | Neo4j seed |

The behaviour log and graph triples are produced deterministically by
`data/generate_datasets.py` (seed=42); the product corpus is hand-curated.

To regenerate:
```bash
cd ai-service/data
python generate_datasets.py
```

### What "real" means here

- The 27-product catalogue mirrors the real seed data in `data/seed_data.sql`.
- The behaviour log is **realistic** rather than collected from production —
  it's anchored to 5 user personas (literature lover, programmer,
  business, lifestyle, gadget enthusiast) and includes the 3 actual
  seed orders as `purchase` events so the dataset is consistent with
  the rest of the system.
- Graph triples are derived from the behaviour log + category structure;
  they're explicit and auditable on disk rather than computed at runtime.

## What is honest vs aspirational

**Honest:**
- LSTM architecture matches thesis Ch.3.4.2 sample line-for-line.
- LSTM trains on the on-disk `user_behavior.csv` (237 events across 5 users).
- FAISS index is rebuilt at every startup from `product_corpus.jsonl`.
- Neo4j is wiped + reseeded from `graph_triples.csv` at every startup.
- Hybrid score is the exact weighted sum from the thesis (`w1·lstm + w2·graph + w3·rag`).

**Aspirational (out of scope for the v01 thesis demo):**
- No real-time user behaviour ingestion (would need Kafka or RabbitMQ topic).
- LSTM is not benchmarked on a holdout set.
- Graph SIMILAR edges are heuristic, not learned.
