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
# sequences derived from book-service + order-service data.

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
| `BOOK_SERVICE_URL` | `http://book-service:8000` | Source of products at startup |
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

## What is honest vs aspirational

**Honest:**
- LSTM architecture matches thesis Ch.3.4.2 sample line-for-line.
- LSTM trains on **synthetic** sequences derived from real seed orders + product categories — there is no event-tracking pipeline yet.
- FAISS index is rebuilt at every startup (small catalogue: ~30 products).
- Neo4j is wiped + reseeded at every startup (idempotent).
- Hybrid score is the exact weighted sum from the thesis (`w1·lstm + w2·graph + w3·rag`).

**Aspirational (out of scope for the v01 thesis demo):**
- No real-time user behaviour ingestion (would need Kafka or RabbitMQ topic for `view`/`click` events).
- LSTM is not benchmarked on a holdout set (no test data).
- Graph SIMILAR edges are heuristic, not learned.

These limitations are documented so the thesis review can score the demo
on what's actually built, not on what the script implies.
