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

# Run a single service locally (example: product-service on port 8002)
cd product-service
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
| Product | 8002 | 8000 |
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
| MySQL (User Context) | 3307 | 3306 |
| Elasticsearch HTTP | 9200 | 9200 |
| Kibana | 5601 | 5601 |
| Prometheus | 9090 | 9090 |
| Grafana | 3000 | 3000 |
| RabbitMQ AMQP | 5673 | 5672 |
| RabbitMQ UI | 15673 | 15672 |
| PostgreSQL | 5433 | 5432 |
| Redis | 6380 | 6379 |

## Architecture Patterns

### Service Structure

Every service follows the same layout: `<service>/<django_project>/settings.py` + `<service>/app/` containing `models.py`, `views.py`, `serializers.py`, `urls.py`, `messaging.py`, `consumers.py`. The `apps.py` `ready()` hook starts RabbitMQ consumer threads (guarded by `RUN_MAIN == 'true'` to avoid double-spawning in dev).

### Database (polyglot persistence)

**Two RDBMS** following the SoAD thesis Ch.2.10.4 split:

| Engine | Image | Services / DBs | Why |
|---|---|---|---|
| **MySQL 8.4** | `mysql:8.4` (host port 3307) | auth-service (auth_db), customer-service (customer_db), staff-service (staff_db), manager-service (manager_db) | User Context — simple relational schema; thesis sample explicitly uses MySQL for User Service |
| **PostgreSQL 16** | `pgvector/pgvector:pg16` (host port 5433) | catalog (catalog_db), product (product_db), cart (cart_db), order (order_db), pay (payment_db), ship (shipping_db), comment-rate (comment_db), advisory-chat (advisory_db) | Product/Order/Advisory contexts — JSON fields, full-text search (`SearchVector`/`SearchQuery`), pgvector embeddings, complex inheritance |

Driver wiring:
- The 4 MySQL services use **PyMySQL** as a `MySQLdb` shim (pure Python, no native libs needed). Top of `settings.py` calls `pymysql.install_as_MySQLdb()` with a version stub.
- The 8 PostgreSQL services keep **psycopg2-binary**.

DB bootstrap:
- `data/init-databases.sql` is mounted into `postgres` and creates the 8 PG databases.
- `data/init-mysql.sql` is mounted into `mysql` and creates the 4 MySQL databases (utf8mb4 / unicode_ci).

Seeding:
- `data/seed_data.sql` — sections for the 8 PG-hosted services (`ON CONFLICT … DO NOTHING`).
- `data/seed_data_mysql.sql` — sections for the 3 MySQL-hosted services (`INSERT IGNORE`). Auth users are created through Django's password hasher in `seed_all.sh`, not raw SQL.

The API Gateway service is the exception: it uses in-memory SQLite (no models, just session proxying).

### Inter-Service HTTP

Services call each other via `requests` library with 5-second timeout. Service URLs are **hardcoded as module-level constants** in views.py using Docker Compose service names (e.g., `http://product-service:8000`). When running locally outside Docker, these URLs won't resolve.

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

### Observability (ELK + Prometheus + Grafana — skeleton)

Implements thesis Ch.4 §4.9 at skeleton level. Four containers up: `elasticsearch` (single-node, security off, `-Xmx512m`), `kibana`, `prometheus` (config `monitoring/prometheus.yml`), `grafana` (auto-provisioned Prometheus datasource + "API Gateway" dashboard). Only `api-gateway` is wired with `django-prometheus` — other services appear DOWN at <http://localhost:9090/targets>. No log shipper yet (Kibana opens with empty indices). Migration steps for full monitoring documented at `monitoring/README.md`.

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

- **PostgreSQL services (8):** Django 4.2, djangorestframework, psycopg2-binary
- **MySQL services (4 — User Context: auth, customer, staff, manager):** Django 4.2, djangorestframework, PyMySQL, cryptography
- **Event-driven services:** pika (RabbitMQ client)
- **API Gateway:** django-redis (caching, rate limiting, session token cache)
- **Advisory Chat:** openai, sentence-transformers, pgvector
- **AI Service (FastAPI):** fastapi, torch (CPU), neo4j, faiss-cpu, sentence-transformers, openai
- **Cart Service:** Redis (via `REDIS_URL` env var)
