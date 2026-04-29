# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A microservices-based online bookstore: 14 Django services communicating via synchronous HTTP and asynchronous RabbitMQ events. All services run in Docker containers with a shared PostgreSQL instance (separate databases per service).

## Build & Run Commands

```bash
# Start all services
docker-compose up --build

# Clean rebuild (resets all data)
docker-compose down -v && docker-compose up --build

# Run a single service locally (example: book-service on port 8002)
cd book-service
pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py runserver 0.0.0.0:8002

# Seed all test data (run after containers are up)
bash data/seed_all.sh

# Load advisory-chat knowledge base
docker-compose exec advisory-chat-service python manage.py load_kb --clear
```

**No test suite exists.** There are no test files in any service.

## Service Port Map

| Service | Host Port | Internal |
|---------|-----------|----------|
| Nginx Gateway | 8080 | 80 |
| API Gateway (Django UI) | 8000 | 8000 |
| Customer | 8001 | 8000 |
| Book | 8002 | 8000 |
| Cart | 8003 | 8000 |
| Staff | 8004 | 8000 |
| Manager | 8005 | 8000 |
| Catalog | 8006 | 8000 |
| Order | 8007 | 8000 |
| Payment | 8008 | 8000 |
| Shipping | 8009 | 8000 |
| Comment-Rate | 8010 | 8000 |
| Recommender AI (legacy, top-rated) | 8011 | 8000 |
| Auth | 8012 | 8000 |
| Advisory Chat (RAG/pgvector) | 8013 | 8000 |
| AI Service (LSTM + Neo4j + FAISS) | 8014 | 8000 |
| Neo4j Bolt | 7687 | 7687 |
| Neo4j Browser | 7474 | 7474 |
| RabbitMQ AMQP | 5673 | 5672 |
| RabbitMQ UI | 15673 | 15672 |
| PostgreSQL | 5433 | 5432 |
| Redis | 6380 | 6379 |

## Architecture Patterns

### Service Structure

Every service follows the same layout: `<service>/<django_project>/settings.py` + `<service>/app/` containing `models.py`, `views.py`, `serializers.py`, `urls.py`, `messaging.py`, `consumers.py`. The `apps.py` `ready()` hook starts RabbitMQ consumer threads (guarded by `RUN_MAIN == 'true'` to avoid double-spawning in dev).

### Database

All services use PostgreSQL via `psycopg2-binary`. Each service gets its own database (created by `data/init-databases.sql`). The API Gateway is the exception: it uses in-memory SQLite (no models, just proxying). The `pgvector/pgvector:pg16` image is used to support vector embeddings in advisory-chat-service.

### Inter-Service HTTP

Services call each other via `requests` library with 5-second timeout. Service URLs are **hardcoded as module-level constants** in views.py using Docker Compose service names (e.g., `http://book-service:8000`). When running locally outside Docker, these URLs won't resolve.

### RabbitMQ Event Bus

- **Exchange:** `bookstore` (topic, durable)
- **Queue naming:** `{service-name}.{routing-key}`
- `messaging.py` in each service provides `publish_event(event_type, data)` and `start_consumer(service_name, bindings)`
- `consumers.py` defines `BINDINGS = [(routing_key, callback_fn), ...]`
- Consumer threads use exponential backoff retry for RabbitMQ connection, heartbeat=600s, prefetch_count=1
- Failed messages are nack'ed with `requeue=False`

### API Gateway (two layers)

The gateway is a **two-layer setup**:

1. **Nginx reverse proxy** (`nginx:1.27-alpine`, host port 8080, config at `gateway/nginx.conf`) — single public entry point. Routes `/api/<service>/...` directly to the corresponding backend microservice (strips the `/api/` prefix). Anything else falls through to the Django UI gateway. Cross-cutting: rate limit (60 req/min/IP on `/api/*`), access log with upstream timing, gzip, forwarded headers.
2. **`api-gateway` Django service** (port 8000) — server-rendered HTML UI. Renders templates, makes internal HTTP calls to backend services, manages sessions. Middleware chain: LoggingMiddleware → RateLimitMiddleware (Redis-backed, 60 req/min/IP) → JWTAuthMiddleware (verifies via auth-service, caches in Redis for 5min).

For thesis demonstration: external clients (Postman, mobile, frontend SPA) should hit Nginx on `:8080/api/...`. Browsers hitting `:8080/` get the Django UI through Nginx; direct access to `:8000` is preserved for debugging.

### Authentication & RBAC

JWT tokens issued by auth-service (PyJWT, HS256, 24h expiry). The gateway's JWTAuthMiddleware verifies tokens by calling auth-service `/auth/verify/` and caches results in Redis. RBAC is enforced in the gateway via a `ROLE_PERMISSIONS` dict mapping `(resource, action)` tuples to allowed roles. Roles: CUSTOMER, STAFF, MANAGER, ADMIN.

### Order Saga

order-service implements a Saga pattern: fetch cart -> get book prices -> create order (PENDING) -> create payment -> create shipment -> confirm. On failure, compensating actions cancel payment/order. Status updates are event-driven: `payment.completed` -> PAID, `shipment.shipped` -> SHIPPING.

### Advisory Chat (RAG Pipeline)

Uses pgvector for semantic search over a knowledge base. Embeddings via `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions). Customer behavior analysis (RFM segmentation) built from order/review data fetched via HTTP. LLM calls use OpenAI `gpt-4o-mini`. System prompt is in Vietnamese. Requires `OPENAI_API_KEY` env var (set in `.env` at project root).

### AI Service (Hybrid Recommender — thesis Ch.3 spec)

**FastAPI** service at port 8014. Three components blended into a hybrid score `final = w1·LSTM + w2·Graph + w3·RAG`:
- **LSTM (PyTorch):** `nn.LSTM(input_dim=N, hidden_dim=64) → nn.Linear(N)` predicts next product from a sequence of one-hot encoded interactions. Trained at startup on synthetic sequences derived from real seed orders + product categories.
- **Knowledge Graph (Neo4j 5):** nodes `(:User)`, `(:Product)`, `(:Category)`; edges `BOUGHT`, `VIEWED`, `SIMILAR` (co-purchase + same-category), `IN_CATEGORY`. Cypher recommendation query at `app/graph/queries.py`.
- **RAG (FAISS `IndexFlatIP`):** embeddings via `sentence-transformers/all-MiniLM-L6-v2`, normalised vectors → cosine similarity over product descriptions.

Endpoints: `GET /recommend?user_id=` (hybrid list), `POST /chatbot` (FAISS retrieve + optional GPT-4o-mini if `OPENAI_API_KEY` set, else templated response). Browse Neo4j at <http://localhost:7474> (`neo4j` / `bookstore-secret`).

The legacy `recommender-ai-service` (port 8011, top-rated only, Django) is preserved separately for backward compatibility — `ai-service` is the thesis-spec implementation.

## Test Accounts (after seeding)

See `data/accounts.md` for full list. Key accounts: `admin/admin123` (ADMIN), `manager1/manager123` (MANAGER), `staff1/staff123` (STAFF), `nguyenvana/customer123` (CUSTOMER).

## Key Dependencies

- **All services:** Django 4.2, djangorestframework, psycopg2-binary
- **Event-driven services:** pika (RabbitMQ client)
- **API Gateway:** django-redis (caching, rate limiting, session token cache)
- **Advisory Chat:** openai, sentence-transformers, pgvector
- **AI Service (FastAPI):** fastapi, torch (CPU), neo4j, faiss-cpu, sentence-transformers, openai
- **Cart Service:** Redis (via `REDIS_URL` env var)
