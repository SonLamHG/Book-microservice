# Architecture Diagrams

> **Companion files in this folder**
> - [`class-diagram.puml`](./class-diagram.puml) — full UML class diagram (8 bounded contexts, 21 classes, inheritance + composition)
> - [`er-diagram.puml`](./er-diagram.puml) — per-service ERD (12 databases, 21 entities)
> - [`sequence-diagrams.puml`](./sequence-diagrams.puml) — sequence flows
> - [`visual-paradigm-guide.md`](./visual-paradigm-guide.md) — how to render and import these into Visual Paradigm for the thesis

## 1. System Overview

```
                    ┌─────────────────────────────────┐
                    │      Nginx Gateway (:8080)       │
                    │   /api/<svc>/ → microservices    │
                    │   /            → Django UI       │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────┴──────────────────┐
                    │      API Gateway (:8000)        │
                    │  Django (HTML Templates + Proxy)│
                    │  JWT Auth + RBAC Middleware     │
                    └──────────────┬──────────────────┘
                                   │
        ┌──────────┬──────────┬────┴────┬──────────┬──────────┐
        ▼          ▼          ▼         ▼          ▼          ▼
  ┌──────────┐┌──────────┐┌─────────┐┌─────────┐┌──────────┐┌─────────────┐
  │ Customer ││   Book   ││  Cart   ││  Order  ││  Review  ││ Recommender │
  │ Service  ││ Service  ││ Service ││ Service ││ Service  ││ AI Service  │
  │  :8001   ││  :8002   ││  :8003  ││  :8007  ││  :8010   ││   :8011     │
  └──────────┘└──────────┘└─────────┘└────┬────┘└──────────┘└─────────────┘
                                          │
                                ┌─────────┼─────────┐
                                ▼         ▼         ▼
  ┌──────────┐            ┌──────────┐┌─────────┐┌─────────┐
  │   Auth   │            │ Payment  ││  Ship   ││ Catalog │
  │ Service  │            │ Service  ││ Service ││ Service │
  │  :8012   │            │  :8008   ││  :8009  ││  :8006  │
  └────┬─────┘            └──────────┘└─────────┘└─────────┘
       │
       │ events              ┌──────────┐┌─────────┐
       └──────────────┐      │  Staff   ││ Manager │
                      ▼      │ Service  ││ Service │
               ┌────────────┐│  :8004   ││  :8005  │
               │  RabbitMQ  │└──────────┘└─────────┘
               │  :5673     │
               │ (bookstore │
               │  exchange) │
               └────────────┘
```

---

## 1.1 Nginx Gateway — Routing Convention

The Nginx layer is the single public entry point. It does not contain any
business logic; it only forwards requests based on URL prefix.

| Request path | Routed to | Container |
|---|---|---|
| `/api/auth/...` | auth-service | `auth-service:8000/auth/...` |
| `/api/customers/...` | customer-service | `customer-service:8000/customers/...` |
| `/api/staff/...` | staff-service | `staff-service:8000/staff/...` |
| `/api/managers/...` | manager-service | `manager-service:8000/managers/...` |
| `/api/categories/...` | catalog-service | `catalog-service:8000/categories/...` |
| `/api/books/...` | product-service | `product-service:8000/books/...` |
| `/api/products/...` | product-service | `product-service:8000/products/...` |
| `/api/electronics/...` | product-service | `product-service:8000/electronics/...` |
| `/api/fashion/...` | product-service | `product-service:8000/fashion/...` |
| `/api/carts/...` | cart-service | `cart-service:8000/carts/...` |
| `/api/cart-items/...` | cart-service | `cart-service:8000/cart-items/...` |
| `/api/orders/...` | order-service | `order-service:8000/orders/...` |
| `/api/payments/...` | pay-service | `pay-service:8000/payments/...` |
| `/api/shipments/...` | ship-service | `ship-service:8000/shipments/...` |
| `/api/reviews/...` | comment-rate-service | `comment-rate-service:8000/reviews/...` |
| `/api/recommendations/...` | recommender-ai-service (legacy) | `recommender-ai-service:8000/recommendations/...` |
| `/api/chat/...` `/api/behavior/...` `/api/kb/...` | advisory-chat-service | `advisory-chat-service:8000/...` |
| `/api/ai/recommend?...` `/api/ai/chatbot` `/api/ai/health` | ai-service (LSTM + Neo4j + FAISS hybrid) | `ai-service:8000/...` |
| anything else (`/`, `/login/`, `/books/`, `/cart/`, `/admin-products/`, …) | api-gateway (Django UI) | `api-gateway:8000/...` |

Cross-cutting concerns enforced at the Nginx layer:
- **Rate limiting** — 60 req/min/IP on `/api/*` routes (`limit_req_zone api_limit`).
- **Logging** — combined access log + per-upstream timing (`upstream=$upstream_addr rt=$request_time`).
- **gzip** — compresses JSON / HTML over 1 KB.
- **Forwarded headers** — `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`, `Host` for downstream services.

---

## 1.3 Observability — ELK + Prometheus + Grafana (skeleton)

Per thesis Ch.4 §4.9. Skeleton-grade deployment (Option A): containers up,
api-gateway wired, others on a documented migration path.

```
                   ┌──────────────────┐    ┌─────────────────┐
   /metrics ──▶    │   Prometheus     │◀──▶│    Grafana      │
   scrape          │   :9090          │    │    :3000        │
                   └────────┬─────────┘    └────────┬────────┘
                            │ scrape every 15s      │ datasource auto-provisioned
                            ▼                       │
                   ┌──────────────────┐             │
                   │  api-gateway     │   ←─────────┘
                   │  (django-prom)   │
                   │  /metrics        │
                   └──────────────────┘

   docker logs ──▶ (no shipper yet) ──▶ ┌────────────┐    ┌────────┐
                                         │ Elasticsearch│◀──▶│ Kibana │
                                         │ :9200       │    │ :5601  │
                                         └────────────┘    └────────┘
```

| Container | Image | Host port | Status |
|---|---|---|---|
| elasticsearch | `docker.elastic.co/elasticsearch/elasticsearch:8.16.1` | 9200 | up; single-node; security off |
| kibana | `docker.elastic.co/kibana/kibana:8.16.1` | 5601 | up; empty indices (no log shipper) |
| prometheus | `prom/prometheus:v3.0.1` | 9090 | up; scrapes api-gateway (UP) + 14 other services (DOWN) |
| grafana | `grafana/grafana:11.4.0` | 3000 | up; admin/admin; auto-loaded "API Gateway" dashboard |

**Wired:** api-gateway only. To bring more services in, follow the
migration steps in `monitoring/README.md`.

---

## 1.2 Polyglot Persistence — MySQL vs PostgreSQL

Per SoAD thesis Ch.2.10.4, the platform deliberately uses two different
RDBMS engines aligned with bounded contexts:

| Engine | Host port | Services / databases | Reason |
|---|---|---|---|
| **MySQL 8.4** | 3307 | auth-service / `auth_db`<br>customer-service / `customer_db`<br>staff-service / `staff_db`<br>manager-service / `manager_db` | User Context — simple relational schema (single flat table per service). Thesis sample explicitly puts User Service on MySQL ("phổ biến, phù hợp authentication"). |
| **PostgreSQL 16 (pgvector)** | 5433 | catalog / `catalog_db`<br>product / `product_db`<br>cart / `cart_db`<br>order / `order_db`<br>pay / `payment_db`<br>ship / `shipping_db`<br>comment-rate / `comment_db`<br>advisory-chat / `advisory_db` | Mixed needs: pgvector for RAG embeddings (advisory_db), `SearchVector`/`SearchRank` full-text search (product_db), `jsonb` columns (advisory behavior summary), complex inheritance (Product/Book/Electronics/Fashion). |

Wiring details:
- MySQL services use **PyMySQL** as a `MySQLdb` shim (`pymysql.install_as_MySQLdb()` at top of `settings.py`); pure-Python, no native libs.
- PostgreSQL services keep **psycopg2-binary**.
- DB bootstrap split into two files: `data/init-databases.sql` (PG) and `data/init-mysql.sql` (MySQL).
- Seed data forked: `seed_data.sql` (PG, `ON CONFLICT … DO NOTHING`) + `seed_data_mysql.sql` (MySQL, `INSERT IGNORE`).

---

## 2. Inter-Service Communication

```
┌──────────────┐  POST /carts/   ┌──────────────┐  GET /books/{id}/  ┌──────────────┐
│   Customer   │ ──────────────> │     Cart     │ ────────────────> │     Book     │
│   Service    │                 │   Service    │                   │   Service    │
└──────────────┘                 └──────────────┘                   └──────────────┘
                                        ▲                                  ▲
                                        │ GET /carts/{id}/                 │
                                        │                                  │
                                 ┌──────┴───────┐  GET /books/{id}/        │
                                 │    Order     │ ─────────────────────────┘
                                 │   Service    │
                                 └──┬───────┬───┘
                  POST /payments/   │       │  POST /shipments/
                     ┌──────────────┘       └──────────────┐
                     ▼                                      ▼
              ┌──────────────┐                      ┌──────────────┐
              │   Payment    │                      │   Shipping   │
              │   Service    │                      │   Service    │
              └──────────────┘                      └──────────────┘

┌──────────────┐ GET /reviews/top-rated/ ┌──────────────┐
│ Recommender  │ ──────────────────────> │   Review     │
│  AI Service  │                         │   Service    │
└──────┬───────┘                         └──────────────┘
       │ GET /books/{id}/
       └──────────────────────────────> Book Service
```

### Event-Driven Communication (via RabbitMQ)

```
┌──────────────┐  user.created.{role}   ┌─────────────────┐
│     Auth     │ ~~~~~~~~~~~~~~~~~~~~~~>│ RabbitMQ        │
│   Service    │                        │ Exchange:       │
└──────────────┘                        │ bookstore       │
                                        │ (topic, durable)│
                                        └───┬───┬───┬─────┘
                  user.created.customer     │   │   │
              ┌─────────────────────────────┘   │   │
              ▼                                 │   │
       ┌──────────────┐                         │   │
       │   Customer   │                         │   │
       │   Service    │  customer.created       │   │
       │  (consume +  │ ~~~~~~~~~~~~~~~~~~>     │   │
       │   publish)   │                    │    │   │
       └──────────────┘                    │    │   │
                                           ▼    │   │
                                    ┌────────── │── │──┐
                                    │   Cart   ││   │  │
                                    │  Service ││   │  │
                                    │(consume) ││   │  │
                                    └──────────┘│   │  │
                  user.created.staff            │   │
              ┌─────────────────────────────────┘   │
              ▼                                     │
       ┌──────────────┐                             │
       │    Staff     │                             │
       │   Service    │   user.created.manager      │
       │  (consume)   │ ┌──────────────────────────┘
       └──────────────┘ ▼
                 ┌──────────────┐
                 │   Manager    │
                 │   Service    │
                 │  (consume)   │
                 └──────────────┘

┌──────────────┐ payment.completed  ┌──────────────┐
│   Payment    │ ~~~~~~~~~~~~~~~~~~>│    Order     │
│   Service    │                    │   Service    │
└──────────────┘                    │  (consume)   │
                                    │ status→PAID  │
┌──────────────┐ shipment.shipped   │              │
│   Shipping   │ ~~~~~~~~~~~~~~~~~~>│ status→      │
│   Service    │                    │  SHIPPING    │
└──────────────┘                    └──────────────┘

Legend: ──> HTTP (sync)   ~~~> RabbitMQ event (async)
```

---

## 3. Individual Service Architectures

### 3.1 Customer Service (:8001)

```
┌───────────────────────────────────────────────────────┐
│                   Customer Service                     │
│                                                        │
│  ┌─────────────┐  ┌────────────────┐  ┌─────────────┐│
│  │   urls.py   │─>│    views.py    │─>│  models.py  ││
│  │             │  │                │  │             ││
│  │ /customers/ │  │ CustomerList   │  │ Customer    ││
│  │ /customers/ │  │ CustomerDetail │  │ - name      ││
│  │   <pk>/     │  │                │  │ - email     ││
│  └─────────────┘  └───────┬────────┘  │ - phone     ││
│                           │           │ - address   ││
│                           ▼           │-auth_user_id││
│                    ┌──────────────┐   └──────┬──────┘│
│                    │serializers.py│          ▼       │
│                    │              │    ┌───────────┐ │
│                    │CustomerSer.  │    │  SQLite   │ │
│                    └──────────────┘    └───────────┘ │
│                                                        │
│  HTTP: POST cart-service:8000/carts/ (on create)       │
│  Publish: customer.created (RabbitMQ)                  │
│  Consume: user.created.customer (creates profile)      │
└───────────────────────────────────────────────────────┘
```

### 3.2 Book Service (:8002)

```
┌───────────────────────────────────────────────────────┐
│                     Book Service                       │
│                                                        │
│  ┌─────────────┐  ┌────────────────┐  ┌─────────────┐│
│  │   urls.py   │─>│    views.py    │─>│  models.py  ││
│  │             │  │                │  │             ││
│  │ /books/     │  │ BookListCreate │  │ Book        ││
│  │ /books/     │  │ BookDetail     │  │ - title     ││
│  │   <pk>/     │  │                │  │ - author    ││
│  └─────────────┘  └───────┬────────┘  │ - price     ││
│                           │           │ - stock     ││
│                           ▼           │ - isbn      ││
│                    ┌──────────────┐   │ - desc      ││
│                    │serializers.py│   │ - category  ││
│                    │BookSerializer│   └──────┬──────┘│
│                    └──────────────┘          ▼       │
│                                        ┌───────────┐ │
│  No external calls                     │  SQLite   │ │
│  (read-only data source)               └───────────┘ │
└───────────────────────────────────────────────────────┘
```

### 3.3 Cart Service (:8003)

```
┌───────────────────────────────────────────────────────┐
│                     Cart Service                       │
│                                                        │
│  ┌───────────────┐ ┌────────────────┐ ┌──────────────┐│
│  │    urls.py    │>│    views.py    │>│  models.py   ││
│  │               │ │                │ │              ││
│  │ /carts/       │ │ CartCreate     │ │ Cart         ││
│  │ /carts/<id>/  │ │ ViewCart       │ │ - customer_id││
│  │ /carts/<id>/  │ │ ClearCart      │ │              ││
│  │   clear/      │ │ AddCartItem    │ │ CartItem     ││
│  │ /cart-items/  │ │ UpdateCartItem │ │ - cart(FK)   ││
│  │ /cart-items/  │ │                │ │ - book_id    ││
│  │   <pk>/       │ └───────┬────────┘ │ - quantity   ││
│  └───────────────┘         │          └──────┬───────┘│
│                            ▼                 ▼        │
│                     ┌──────────────┐   ┌───────────┐  │
│                     │serializers.py│   │  SQLite   │  │
│                     └──────────────┘   └───────────┘  │
│                                                        │
│  External Call:                                        │
│  GET product-service:8000/books/{id}/ (on add)            │
└───────────────────────────────────────────────────────┘
```

### 3.4 Order Service (:8007)

```
┌───────────────────────────────────────────────────────┐
│                    Order Service                       │
│                                                        │
│  ┌─────────────┐  ┌────────────────┐  ┌──────────────┐│
│  │   urls.py   │─>│    views.py    │─>│  models.py   ││
│  │             │  │                │  │              ││
│  │ /orders/    │  │ OrderListCreate│  │ Order        ││
│  │ /orders/    │  │ OrderDetail    │  │ - customer_id││
│  │   <pk>/     │  │                │  │ - total      ││
│  └─────────────┘  └───────┬────────┘  │ - status     ││
│                           │           │ - address    ││
│                           ▼           │ - pay_method ││
│                    ┌──────────────┐   │ - ship_method││
│                    │serializers.py│   │              ││
│                    └──────────────┘   │ OrderItem    ││
│                                       │ - order(FK)  ││
│  External Calls (on POST /orders/):   │ - book_id    ││
│  1. GET  cart:8000/carts/{id}/        │ - quantity   ││
│  2. GET  book:8000/books/{id}/        │ - price      ││
│  3. POST pay:8000/payments/           └──────┬───────┘│
│  4. POST ship:8000/shipments/                ▼        │
│  5. DEL  cart:8000/carts/{id}/clear/   ┌───────────┐  │
│                                        │  SQLite   │  │
│                                        └───────────┘  │
└───────────────────────────────────────────────────────┘
```

### 3.5 Payment Service (:8008)

```
┌───────────────────────────────────────────────────────┐
│                   Payment Service                      │
│                                                        │
│  ┌─────────────┐  ┌────────────────┐  ┌──────────────┐│
│  │   urls.py   │─>│    views.py    │─>│  models.py   ││
│  │             │  │                │  │              ││
│  │ /payments/  │  │ PaymentList    │  │ Payment      ││
│  │ /payments/  │  │ PaymentDetail  │  │ - order_id   ││
│  │   <pk>/     │  │                │  │ - amount     ││
│  └─────────────┘  └───────┬────────┘  │ - method     ││
│                           │           │ - status     ││
│                           ▼           └──────┬───────┘│
│                    ┌──────────────┐          ▼        │
│                    │serializers.py│    ┌───────────┐   │
│                    └──────────────┘    │  SQLite   │   │
│                                        └───────────┘   │
│  No external calls                                     │
│  Query: ?order_id= filter                              │
└───────────────────────────────────────────────────────┘
```

### 3.6 Shipping Service (:8009)

```
┌───────────────────────────────────────────────────────┐
│                   Shipping Service                     │
│                                                        │
│  ┌─────────────┐  ┌────────────────┐  ┌──────────────┐│
│  │   urls.py   │─>│    views.py    │─>│  models.py   ││
│  │             │  │                │  │              ││
│  │ /shipments/ │  │ ShipmentList   │  │ Shipment     ││
│  │ /shipments/ │  │ ShipmentDetail │  │ - order_id   ││
│  │   <pk>/     │  │                │  │ - address    ││
│  └─────────────┘  └───────┬────────┘  │ - method     ││
│                           │           │ - status     ││
│                           ▼           │ - tracking   ││
│                    ┌──────────────┐   └──────┬───────┘│
│                    │serializers.py│          ▼        │
│                    └──────────────┘    ┌───────────┐   │
│                                        │  SQLite   │   │
│  No external calls                     └───────────┘   │
│  Auto-generates tracking_number (TRK-{uuid})           │
│  Query: ?order_id= filter                              │
└───────────────────────────────────────────────────────┘
```

### 3.7 Comment-Rate Service (:8010)

```
┌───────────────────────────────────────────────────────┐
│                Comment-Rate Service                    │
│                                                        │
│  ┌───────────────┐ ┌────────────────┐ ┌──────────────┐│
│  │    urls.py    │>│    views.py    │>│  models.py   ││
│  │               │ │                │ │              ││
│  │ /reviews/     │ │ ReviewList     │ │ Review       ││
│  │ /reviews/     │ │ BookReviews    │ │ - book_id    ││
│  │   book/<id>/  │ │ TopRated       │ │ - customer_id││
│  │ /reviews/     │ │                │ │ - rating     ││
│  │   top-rated/  │ │                │ │   (1-5)      ││
│  └───────────────┘ └───────┬────────┘ │ - comment    ││
│                            │          └──────┬───────┘│
│                            ▼                 ▼        │
│                     ┌──────────────┐   ┌───────────┐  │
│                     │serializers.py│   │  SQLite   │  │
│                     └──────────────┘   └───────────┘  │
│                                                        │
│  No external calls                                     │
│  Unique constraint: (book_id, customer_id)             │
│  Aggregation: avg_rating, total_reviews                │
│  Query: ?limit= for top-rated                          │
└───────────────────────────────────────────────────────┘
```

### 3.8 Catalog Service (:8006)

```
┌───────────────────────────────────────────────────────┐
│                   Catalog Service                      │
│                                                        │
│  ┌─────────────┐  ┌────────────────┐  ┌──────────────┐│
│  │   urls.py   │─>│    views.py    │─>│  models.py   ││
│  │             │  │                │  │              ││
│  │ /categories/│  │ CategoryList   │  │ Category     ││
│  │ /categories/│  │ CategoryDetail │  │ - name       ││
│  │   <pk>/     │  │                │  │ - desc       ││
│  └─────────────┘  └───────┬────────┘  └──────┬───────┘│
│                           ▼                  ▼        │
│                    ┌──────────────┐    ┌───────────┐   │
│                    │serializers.py│    │  SQLite   │   │
│                    └──────────────┘    └───────────┘   │
│  No external calls                                     │
└───────────────────────────────────────────────────────┘
```

### 3.9 Staff Service (:8004)

```
┌───────────────────────────────────────────────────────┐
│                    Staff Service                       │
│                                                        │
│  ┌─────────────┐  ┌────────────────┐  ┌──────────────┐│
│  │   urls.py   │─>│    views.py    │─>│  models.py   ││
│  │             │  │                │  │              ││
│  │ /staff/     │  │ StaffList      │  │ Staff        ││
│  │ /staff/     │  │ StaffDetail    │  │ - name       ││
│  │   <pk>/     │  │                │  │ - email      ││
│  └─────────────┘  └───────┬────────┘  │ - role       ││
│                           ▼           │-auth_user_id ││
│                    ┌──────────────┐   └──────┬───────┘│
│                    │serializers.py│          ▼        │
│                    └──────────────┘    ┌───────────┐   │
│  Consume: user.created.staff           └───────────┘   │
└───────────────────────────────────────────────────────┘
```

### 3.10 Manager Service (:8005)

```
┌───────────────────────────────────────────────────────┐
│                   Manager Service                      │
│                                                        │
│  ┌─────────────┐  ┌────────────────┐  ┌──────────────┐│
│  │   urls.py   │─>│    views.py    │─>│  models.py   ││
│  │             │  │                │  │              ││
│  │ /managers/  │  │ ManagerList    │  │ Manager      ││
│  │ /managers/  │  │ ManagerDetail  │  │ - name       ││
│  │   <pk>/     │  │                │  │ - email      ││
│  └─────────────┘  └───────┬────────┘  │ - department ││
│                           ▼           │-auth_user_id ││
│                    ┌──────────────┐   └──────┬───────┘│
│                    │serializers.py│          ▼        │
│                    └──────────────┘    ┌───────────┐   │
│  Consume: user.created.manager         └───────────┘   │
└───────────────────────────────────────────────────────┘
```

### 3.11 Recommender AI Service (:8011)

```
┌───────────────────────────────────────────────────────┐
│               Recommender AI Service                   │
│                                                        │
│  ┌─────────────────┐  ┌────────────────────────────┐  │
│  │     urls.py     │─>│         views.py           │  │
│  │                 │  │                            │  │
│  │ /recommendations│  │  Recommendations           │  │
│  │  /<customer_id>/│  │                            │  │
│  └─────────────────┘  │  Algorithm:                │  │
│                        │  1. Get top-rated books    │  │
│                        │  2. Enrich with details    │  │
│                        │  3. Fill with latest       │  │
│                        └────────────────────────────┘  │
│                                                        │
│  No local database                                     │
│  No models                                             │
│                                                        │
│  External Calls:                                       │
│  GET review:8000/reviews/top-rated/                    │
│  GET book:8000/books/{id}/                             │
│  GET book:8000/books/                                  │
└───────────────────────────────────────────────────────┘
```

### 3.12 API Gateway (:8000)

```
┌───────────────────────────────────────────────────────┐
│                      API Gateway                       │
│     (Web Interface + Service Proxy + JWT + RBAC)       │
│                                                        │
│  ┌─────────────┐  ┌────────────────┐  ┌──────────────┐│
│  │   urls.py   │─>│    views.py    │─>│  templates/  ││
│  │             │  │                │  │              ││
│  │  23 routes  │  │ 12 view funcs  │  │ 12 HTML files││
│  └─────────────┘  └───────┬────────┘  └──────────────┘│
│                           │                            │
│  No local database        │  HTTP Proxy to:            │
│  No models                │                            │
│                           ├─> customer-service :8001   │
│                           ├─> product-service     :8002   │
│                           ├─> cart-service     :8003   │
│                           ├─> staff-service    :8004   │
│                           ├─> manager-service  :8005   │
│                           ├─> catalog-service  :8006   │
│                           ├─> order-service    :8007   │
│                           ├─> pay-service      :8008   │
│                           ├─> ship-service     :8009   │
│                           ├─> comment-rate     :8010   │
│                           ├─> recommender-ai   :8011   │
│                           └─> auth-service     :8012   │
│                                                        │
│  Middleware Chain:                                      │
│  1. LoggingMiddleware (request logging)                 │
│  2. RateLimitMiddleware (60 req/min/IP)                 │
│  3. SessionMiddleware                                   │
│  4. CsrfViewMiddleware                                  │
│  5. JWTAuthMiddleware (token verify + RBAC)             │
└───────────────────────────────────────────────────────┘
```

---

## 4. Order Creation Flow (Sequence Diagram)

```
Customer    API Gateway    Order Service    Cart Service    Book Service    Pay Service    Ship Service
   │            │               │               │               │              │              │
   │─ POST ────>│               │               │               │              │              │
   │ /orders/   │── POST ──────>│               │               │              │              │
   │ create/    │  /orders/     │── GET ────────>│               │              │              │
   │            │               │  /carts/{id}/ │               │              │              │
   │            │               │<── cart items──│               │              │              │
   │            │               │                               │              │              │
   │            │               │── GET (per item) ────────────>│              │              │
   │            │               │  /books/{id}/                 │              │              │
   │            │               │<── book price ────────────────│              │              │
   │            │               │                                              │              │
   │            │               │── POST ─────────────────────────────────────>│              │
   │            │               │  /payments/                                  │              │
   │            │               │                                                             │
   │            │               │── POST ────────────────────────────────────────────────────>│
   │            │               │  /shipments/                                                │
   │            │               │                                                             │
   │            │               │── DELETE ─────>│                                            │
   │            │               │ /carts/{id}/   │                                            │
   │            │               │  clear/        │                                            │
   │            │               │                                                             │
   │            │<── 201 ───────│                                                             │
   │<── redirect│               │                                                             │
```

---

## 5. DDD Bounded Context Mapping

```
┌─────────────────────────────────────────────────────────────────────┐
│                          BookStore Domain                            │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │     Identity     │  │     Catalog      │  │     Ordering     │  │
│  │                  │  │                  │  │                  │  │
│  │ auth-service     │  │ catalog-service  │  │  cart-service    │  │
│  │ customer-service │  │ product-service     │  │  order-service   │  │
│  │ staff-service    │  │                  │  │                  │  │
│  │ manager-service  │  │                  │  │                  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │     Payment      │  │     Shipping     │  │      Review      │  │
│  │                  │  │                  │  │                  │  │
│  │  pay-service     │  │  ship-service    │  │ comment-rate-    │  │
│  │                  │  │                  │  │ service          │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                      │
│  ┌──────────────────┐                                                │
│  │  Recommendation  │                                                │
│  │                  │                                                │
│  │ recommender-ai-  │                                                │
│  │ service          │                                                │
│  └──────────────────┘                                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Docker Compose Deployment

```
┌───────────────────────────────────────────────────────┐
│                    Docker Network                      │
│                                                        │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐│
│  │ customer-     │ │ book-         │ │ cart-          ││
│  │ service       │ │ service       │ │ service        ││
│  │ 8001:8000     │ │ 8002:8000     │ │ 8003:8000     ││
│  └───────────────┘ └───────────────┘ └───────────────┘│
│                                                        │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐│
│  │ staff-        │ │ manager-      │ │ catalog-       ││
│  │ service       │ │ service       │ │ service        ││
│  │ 8004:8000     │ │ 8005:8000     │ │ 8006:8000     ││
│  └───────────────┘ └───────────────┘ └───────────────┘│
│                                                        │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐│
│  │ order-        │ │ pay-          │ │ ship-          ││
│  │ service       │ │ service       │ │ service        ││
│  │ 8007:8000     │ │ 8008:8000     │ │ 8009:8000     ││
│  └───────────────┘ └───────────────┘ └───────────────┘│
│                                                        │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐│
│  │ comment-      │ │ recommender-  │ │ api-           ││
│  │ rate-service  │ │ ai-service    │ │ gateway        ││
│  │ 8010:8000     │ │ 8011:8000     │ │ 8000:8000     ││
│  └───────────────┘ └───────────────┘ └───────────────┘│
│                                                        │
│  ┌───────────────┐ ┌───────────────┐                    │
│  │ auth-         │ │ rabbitmq      │                    │
│  │ service       │ │ (broker)      │                    │
│  │ 8012:8000     │ │ 5673:5672     │                    │
│  └───────────────┘ │ 15673:15672   │                    │
│                     └───────────────┘                    │
│                                                        │
│  Data Persistence (Docker Volumes):                    │
│  Each service: {service}_data:/app/data (SQLite)       │
│  RabbitMQ: rabbitmq_data:/var/lib/rabbitmq             │
│                                                        │
│  Startup Order (depends_on):                           │
│  rabbitmq -> auth, customer, staff, manager, cart,     │
│              order, pay, ship services                  │
│  product-service -> cart-service -> customer-service      │
│  pay-service, ship-service -> order-service            │
│  comment-rate-service -> recommender-ai-service        │
│  all services -> api-gateway                           │
└───────────────────────────────────────────────────────┘
```
