# Bookstore Microservice

A microservices-based online bookstore built with Django and Django REST Framework. The system is composed of 14 independently deployable services fronted by an Nginx reverse-proxy gateway, communicating via synchronous HTTP and asynchronous messaging (RabbitMQ).

## Architecture

```
                          ┌──────────────────┐
                          │  Nginx Gateway   │ :8080
                          │   /api/* → svcs  │
                          │   /     → UI     │
                          └────────┬─────────┘
                                   │
                          ┌──────────────┐
                          │  API Gateway │ :8000
                          │  (Django UI) │
                          │ JWT + RBAC   │
                          └──────┬───────┘
          ┌──────┬───────┬───────┼───────┬──────┬──────────┐
          ▼      ▼       ▼       ▼       ▼      ▼          ▼
     ┌────────┐┌───────┐┌───────┐┌─────┐┌──────┐┌───────┐┌────────────────┐
     │Customer││ Book  ││ Cart  ││Order││Review││Catalog││Recommender     │
     │Service ││Service││Service││Svc  ││ Svc  ││  Svc  ││  AI Service    │
     │ :8001  ││ :8002 ││ :8003 ││:8007││:8010 ││ :8006 ││   :8011        │
     └────────┘└───────┘└───────┘└─────┘└──────┘└───────┘└────────────────┘
          │                 ▲       │
          │    event        │ event │
          ▼    ~~~>         │ ~~~>  ▼
     ┌────────┐        ┌───┴────┐┌──────┐┌──────┐┌──────┐
     │  Auth  │        │Payment ││ Ship ││Staff ││Mngr  │
     │Service │        │Service ││ Svc  ││ Svc  ││ Svc  │
     │ :8012  │        │ :8008  ││:8009 ││:8004 ││:8005 │
     └───┬────┘        └────────┘└──────┘└──────┘└──────┘
         │                                  ▲       ▲
         │ event: user.created.{role}       │       │
         └──────────────────────────────────┘───────┘
                          │
                    ┌─────┴──────┐
                    │  RabbitMQ  │ :5673
                    │ (bookstore │
                    │  exchange) │
                    └────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| **Nginx Gateway** | 8080 | Public reverse proxy. Routes `/api/<svc>/...` to backend microservices, falls back to Django UI. Rate limit + access logs |
| **API Gateway** | 8000 | Django UI gateway behind Nginx — HTML templates, JWT auth, RBAC |
| **Auth Service** | 8012 | User authentication, JWT token generation, role management |
| **Customer Service** | 8001 | Customer registration and profile management |
| **Book Service** | 8002 | Book catalog CRUD operations |
| **Cart Service** | 8003 | Shopping cart management with book validation |
| **Staff Service** | 8004 | Staff member management |
| **Manager Service** | 8005 | Manager information management |
| **Catalog Service** | 8006 | Product category management |
| **Order Service** | 8007 | Order processing with Saga orchestration |
| **Payment Service** | 8008 | Payment creation and status tracking |
| **Shipping Service** | 8009 | Shipment tracking with auto-generated tracking numbers |
| **Comment-Rate Service** | 8010 | Book reviews and ratings (1-5 scale) |
| **Recommender AI Service** | 8011 | Legacy top-rated recommender (Django) |
| **Auth Service** | 8012 | JWT issuance + verification |
| **Advisory Chat Service** | 8013 | RAG chatbot (pgvector + OpenAI) + RFM behavior |
| **AI Service** | 8014 | Hybrid recommender — LSTM + Neo4j KG + FAISS RAG (FastAPI, thesis Ch.3) |
| **Neo4j** | 7474 / 7687 | Knowledge graph (HTTP browser / Bolt) |
| **RabbitMQ** | 5673 / 15673 | Message broker (AMQP / Management UI) |
| **PostgreSQL** | 5433 | Database for 8 contexts (Product, Cart, Order, Payment, Shipping, Review, Catalog, Advisory) |
| **MySQL** | 3307 | Database for 4 User Context services (auth, customer, staff, manager) |

## Tech Stack

- **Language:** Python 3.11
- **Framework:** Django, Django REST Framework
- **Database:** SQLite (per-service, persisted via Docker volumes)
- **Authentication:** JWT (PyJWT, HS256, 24h expiry)
- **Authorization:** Role-based access control (CUSTOMER, STAFF, MANAGER, ADMIN)
- **Message Broker:** RabbitMQ (topic exchange, pika client)
- **Inter-service Communication:** HTTP (synchronous) + RabbitMQ events (asynchronous)
- **Containerization:** Docker, Docker Compose

## Getting Started

### Prerequisites

- Docker & Docker Compose

### Run All Services

```bash
docker-compose up --build
```

The API Gateway will be available at `http://localhost:8000`.
RabbitMQ Management UI at `http://localhost:15673` (guest/guest).

### Clean Rebuild (reset all data)

```bash
docker-compose down -v
docker-compose up --build
```

### Run a Single Service (Development)

```bash
cd book-service
pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py runserver 0.0.0.0:8002
```

## Authentication & RBAC

Users authenticate via **Auth Service** (JWT tokens). The API Gateway validates tokens and enforces **role-based access control**.

**Roles:** CUSTOMER, STAFF, MANAGER, ADMIN

| Resource | CUSTOMER | STAFF | MANAGER | ADMIN |
|----------|----------|-------|---------|-------|
| Books (read) | Yes | Yes | Yes | Yes |
| Books (create/edit/delete) | - | Yes | Yes | Yes |
| Customers (list/edit) | - | Yes | Yes | Yes |
| Customers (delete) | - | - | Yes | Yes |
| Staff (list) | - | Yes | Yes | Yes |
| Staff (create/edit) | - | - | Yes | Yes |
| Staff (delete) | - | - | - | Yes |
| Managers (list) | - | - | Yes | Yes |
| Managers (create/edit/delete) | - | - | - | Yes |
| Categories (create/edit) | - | Yes | Yes | Yes |
| Categories (delete) | - | - | Yes | Yes |
| Cart / Orders / Reviews | Yes | Yes | Yes | Yes |

## Service Communication

### Synchronous (HTTP)

```
Customer Service  ──POST /carts/──────────────> Cart Service
Cart Service      ──GET /books/{id}/──────────> Book Service
Order Service     ──GET /carts/{customer_id}/─> Cart Service
                  ──GET /books/{id}/──────────> Book Service
                  ──POST /payments/───────────> Payment Service
                  ──POST /shipments/──────────> Shipping Service
Recommender AI    ──GET /reviews/top-rated/───> Comment-Rate Service
                  ──GET /books/{id}/──────────> Book Service
```

### Asynchronous (RabbitMQ Events)

```
Auth Service      ~~user.created.{role}~~~~~~> Customer/Staff/Manager Service
Customer Service  ~~customer.created~~~~~~~~~> Cart Service (auto-create cart)
Payment Service   ~~payment.completed~~~~~~~~> Order Service (status → PAID)
Shipping Service  ~~shipment.shipped~~~~~~~~~> Order Service (status → SHIPPING)
Order Service     ~~order.created~~~~~~~~~~~~> (logged, future use)
                  ~~order.status_changed~~~~~> (logged, future use)
```

**Exchange:** `bookstore` (topic, durable)
**Queue naming:** `{service-name}.{routing-key}`

## Key Workflows

### User Registration
1. User registers via API Gateway → Auth Service creates user + JWT
2. Auth Service publishes `user.created.{role}` event via RabbitMQ
3. Downstream service (Customer/Staff/Manager) consumes event, creates profile
4. If Customer: `customer.created` event triggers Cart auto-creation

### Order Creation (Saga Pattern)
1. Fetch cart items from Cart Service
2. Get book prices from Book Service
3. Calculate total, create order (PENDING)
4. Reserve payment via Payment Service
5. Reserve shipment via Shipping Service
6. Confirm order → publish `order.created` event
7. If any step fails → compensate (cancel payment, cancel order)

**Order status flow:** `PENDING` → `CONFIRMED` → `PAID` → `SHIPPING` → `COMPLETED` / `CANCELLED`

### Async Status Updates
- Payment marked COMPLETED → `payment.completed` event → Order auto-updates to PAID
- Shipment marked SHIPPED → `shipment.shipped` event → Order auto-updates to SHIPPING

### Recommendations
1. Fetch top-rated books from Comment-Rate Service
2. Enrich with book details from Book Service
3. Fill remaining slots with latest books if needed

## API Endpoints

### Auth Service (port 8012)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register/` | Register user (returns JWT) |
| POST | `/auth/login/` | Login (returns JWT) |
| POST | `/auth/verify/` | Verify JWT token |
| GET | `/auth/users/` | List all users |

### Book Service (port 8002)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/books/` | List all books |
| POST | `/books/` | Create a book |
| GET | `/books/<id>/` | Get book details |
| PUT | `/books/<id>/` | Update a book |
| DELETE | `/books/<id>/` | Delete a book |

### Customer Service (port 8001)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/customers/` | List all customers |
| POST | `/customers/` | Register customer (publishes event, auto-creates cart) |
| GET | `/customers/<id>/` | Get customer details |
| PUT | `/customers/<id>/` | Update customer |
| DELETE | `/customers/<id>/` | Delete customer |

### Cart Service (port 8003)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/carts/` | Create a cart |
| GET | `/carts/<customer_id>/` | View cart items |
| POST | `/cart-items/` | Add item to cart |
| PUT | `/cart-items/<id>/` | Update item quantity |
| DELETE | `/cart-items/<id>/` | Remove item |

### Order Service (port 8007)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/orders/?customer_id=<id>` | List orders by customer |
| POST | `/orders/` | Create order from cart (Saga) |
| GET | `/orders/<id>/` | Get order details |
| PUT | `/orders/<id>/` | Update order status |

### Payment Service (port 8008)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/?order_id=<id>` | List payments by order |
| POST | `/payments/` | Create payment |
| GET | `/payments/<id>/` | Get payment details |
| PUT | `/payments/<id>/` | Update payment status (publishes event if COMPLETED) |

### Shipping Service (port 8009)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/shipments/?order_id=<id>` | List shipments by order |
| POST | `/shipments/` | Create shipment |
| GET | `/shipments/<id>/` | Get shipment details |
| PUT | `/shipments/<id>/` | Update shipment status (publishes event if SHIPPED) |

### Comment-Rate Service (port 8010)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/reviews/` | List all reviews |
| POST | `/reviews/` | Create/update a review |
| GET | `/reviews/book/<book_id>/` | Get reviews for a book (with avg rating) |
| GET | `/reviews/top-rated/?limit=10` | Get top-rated book IDs |

### Catalog Service (port 8006)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/categories/` | List all categories |
| POST | `/categories/` | Create a category |
| GET | `/categories/<id>/` | Get category details |
| PUT | `/categories/<id>/` | Update a category |
| DELETE | `/categories/<id>/` | Delete a category |

### Staff Service (port 8004)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/staff/` | List all staff |
| POST | `/staff/` | Create staff member |
| GET | `/staff/<id>/` | Get staff details |
| PUT | `/staff/<id>/` | Update staff |
| DELETE | `/staff/<id>/` | Delete staff |

### Manager Service (port 8005)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/managers/` | List all managers |
| POST | `/managers/` | Create manager |
| GET | `/managers/<id>/` | Get manager details |
| PUT | `/managers/<id>/` | Update manager |
| DELETE | `/managers/<id>/` | Delete manager |

### Recommender AI Service (port 8011)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/recommendations/<customer_id>/?limit=5` | Get book recommendations |

## RabbitMQ Events

| Event (Routing Key) | Publisher | Consumer | Payload |
|---------------------|----------|----------|---------|
| `user.created.customer` | auth-service | customer-service | `{user_id, username, email, role}` |
| `user.created.staff` | auth-service | staff-service | `{user_id, username, email, role}` |
| `user.created.manager` | auth-service | manager-service | `{user_id, username, email, role}` |
| `customer.created` | customer-service | cart-service | `{customer_id}` |
| `order.created` | order-service | — | `{order_id, customer_id, total_amount, payment_id, shipment_id}` |
| `order.status_changed` | order-service | — | `{order_id, status}` |
| `payment.completed` | pay-service | order-service | `{payment_id, order_id}` |
| `shipment.shipped` | ship-service | order-service | `{shipment_id, order_id}` |

## Project Structure

```
Book_store_microservice/
├── api-gateway/            # Centralized UI, routing, JWT auth, RBAC
├── auth-service/           # User authentication & JWT
├── book-service/           # Book catalog
├── cart-service/           # Shopping cart
├── customer-service/       # Customer profiles
├── order-service/          # Order orchestration (Saga)
├── pay-service/            # Payments
├── ship-service/           # Shipping & tracking
├── comment-rate-service/   # Reviews & ratings
├── catalog-service/        # Categories
├── staff-service/          # Staff management
├── manager-service/        # Manager management
├── recommender-ai-service/ # AI recommendations
├── docs/                   # Documentation
└── docker-compose.yml
```

Each service follows a standard layout:

```
<service>/
├── <service_name>/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── app/
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   ├── apps.py           # Consumer startup via AppConfig.ready()
│   ├── messaging.py      # RabbitMQ publish/consume utilities
│   └── consumers.py      # Event handlers
├── data/
│   └── db.sqlite3        # Persisted via Docker volume
├── manage.py
├── requirements.txt
├── Dockerfile
└── .dockerignore
```
