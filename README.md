# Bookstore Microservice

A microservices-based online bookstore built with Django and Django REST Framework. The system is composed of 12 independently deployable services communicating via synchronous HTTP.

## Architecture

```
                          ┌──────────────┐
                          │  API Gateway │ :8000
                          │   (Django)   │
                          └──────┬───────┘
          ┌──────┬───────┬───────┼───────┬──────┬──────────┐
          ▼      ▼       ▼       ▼       ▼      ▼          ▼
     ┌────────┐┌───────┐┌───────┐┌─────┐┌──────┐┌───────┐┌────────────────┐
     │Customer││ Book  ││ Cart  ││Order││Review││Catalog││Recommender     │
     │Service ││Service││Service││Svc  ││ Svc  ││  Svc  ││  AI Service    │
     │ :8001  ││ :8002 ││ :8003 ││:8007││:8010 ││ :8006 ││   :8011        │
     └────────┘└───────┘└───────┘└─────┘└──────┘└───────┘└────────────────┘
                                  │
                          ┌───────┼───────┐
                          ▼       ▼       ▼
                     ┌────────┐┌──────┐┌──────┐
                     │Payment ││ Ship ││Staff/│
                     │Service ││ Svc  ││Mgr   │
                     │ :8008  ││:8009 ││:8004 │
                     └────────┘└──────┘│:8005 │
                                       └──────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| **API Gateway** | 8000 | Centralized entry point with HTML UI, routes requests to backend services |
| **Customer Service** | 8001 | Customer registration and profile management |
| **Book Service** | 8002 | Book catalog CRUD operations |
| **Cart Service** | 8003 | Shopping cart management with book validation |
| **Staff Service** | 8004 | Staff member management |
| **Manager Service** | 8005 | Manager information management |
| **Catalog Service** | 8006 | Product category management |
| **Order Service** | 8007 | Order processing orchestration (cart, payment, shipping) |
| **Payment Service** | 8008 | Payment creation and status tracking |
| **Shipping Service** | 8009 | Shipment tracking with auto-generated tracking numbers |
| **Comment-Rate Service** | 8010 | Book reviews and ratings (1-5 scale) |
| **Recommender AI Service** | 8011 | Book recommendations based on top-rated reviews |

## Tech Stack

- **Language:** Python 3.11
- **Framework:** Django, Django REST Framework
- **Database:** SQLite (per-service)
- **Inter-service Communication:** HTTP (Python `requests`)
- **Containerization:** Docker, Docker Compose

## Getting Started

### Prerequisites

- Docker & Docker Compose

### Run All Services

```bash
docker-compose up --build
```

The API Gateway will be available at `http://localhost:8000`.

### Run a Single Service (Development)

```bash
cd book-service
pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py runserver 0.0.0.0:8002
```

## Service Communication

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

## Key Workflows

### Customer Registration
1. Customer created in Customer Service
2. Cart auto-created via Cart Service

### Order Creation
1. Fetch cart items from Cart Service
2. Get book prices from Book Service
3. Calculate total, create order
4. Initiate payment via Payment Service
5. Initiate shipment via Shipping Service

**Order status flow:** `PENDING` → `PAID` → `SHIPPING` → `COMPLETED` / `CANCELLED`

### Recommendations
1. Fetch top-rated books from Comment-Rate Service
2. Enrich with book details from Book Service
3. Fill remaining slots with latest books if needed

## API Endpoints

### Book Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/books/` | List all books |
| POST | `/books/` | Create a book |
| GET | `/books/<id>/` | Get book details |
| PUT | `/books/<id>/` | Update a book |
| DELETE | `/books/<id>/` | Delete a book |

### Customer Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/customers/` | List all customers |
| POST | `/customers/` | Register customer (auto-creates cart) |
| GET | `/customers/<id>/` | Get customer details |
| PUT | `/customers/<id>/` | Update customer |
| DELETE | `/customers/<id>/` | Delete customer |

### Cart Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/carts/` | Create a cart |
| GET | `/carts/<customer_id>/` | View cart items |
| POST | `/cart-items/` | Add item to cart |
| PUT | `/cart-items/<id>/` | Update item quantity |
| DELETE | `/cart-items/<id>/` | Remove item |

### Order Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/orders/?customer_id=<id>` | List orders by customer |
| POST | `/orders/` | Create order from cart |
| GET | `/orders/<id>/` | Get order details |
| PUT | `/orders/<id>/` | Update order status |

### Payment Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/?order_id=<id>` | List payments by order |
| POST | `/payments/` | Create payment |
| GET | `/payments/<id>/` | Get payment details |
| PUT | `/payments/<id>/` | Update payment status |

### Shipping Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/shipments/?order_id=<id>` | List shipments by order |
| POST | `/shipments/` | Create shipment |
| GET | `/shipments/<id>/` | Get shipment details |
| PUT | `/shipments/<id>/` | Update shipment status |

### Comment-Rate Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/reviews/` | List all reviews |
| POST | `/reviews/` | Create/update a review |
| GET | `/reviews/book/<book_id>/` | Get reviews for a book (with avg rating) |
| GET | `/reviews/top-rated/?limit=10` | Get top-rated book IDs |

### Catalog Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/categories/` | List all categories |
| POST | `/categories/` | Create a category |
| GET | `/categories/<id>/` | Get category details |
| PUT | `/categories/<id>/` | Update a category |
| DELETE | `/categories/<id>/` | Delete a category |

### Recommender AI Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/recommendations/<customer_id>/?limit=5` | Get book recommendations |

## Project Structure

```
Book_store_microservice/
├── api-gateway/            # Centralized UI & routing
├── book-service/           # Book catalog
├── cart-service/           # Shopping cart
├── customer-service/       # Customer profiles
├── order-service/          # Order orchestration
├── pay-service/            # Payments
├── ship-service/           # Shipping & tracking
├── comment-rate-service/   # Reviews & ratings
├── catalog-service/        # Categories
├── staff-service/          # Staff management
├── manager-service/        # Manager management
├── recommender-ai-service/ # AI recommendations
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
│   └── urls.py
├── manage.py
├── requirements.txt
├── Dockerfile
└── .dockerignore
```
