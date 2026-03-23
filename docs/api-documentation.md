# API Documentation

## Overview

All backend services use Django REST Framework and communicate via JSON over HTTP and RabbitMQ events.
Each service runs on port 8000 internally; external ports are mapped via Docker Compose.
Authentication is handled by Auth Service (JWT). The API Gateway enforces role-based access control (RBAC).

**Base URLs (Docker):**

| Service                | Internal URL                          | External Port |
|------------------------|---------------------------------------|---------------|
| customer-service       | `http://customer-service:8000`        | 8001          |
| book-service           | `http://book-service:8000`            | 8002          |
| cart-service           | `http://cart-service:8000`            | 8003          |
| staff-service          | `http://staff-service:8000`           | 8004          |
| manager-service        | `http://manager-service:8000`         | 8005          |
| catalog-service        | `http://catalog-service:8000`         | 8006          |
| order-service          | `http://order-service:8000`           | 8007          |
| pay-service            | `http://pay-service:8000`             | 8008          |
| ship-service           | `http://ship-service:8000`            | 8009          |
| comment-rate-service   | `http://comment-rate-service:8000`    | 8010          |
| recommender-ai-service | `http://recommender-ai-service:8000`  | 8011          |
| auth-service           | `http://auth-service:8000`            | 8012          |

---

## 1. Customer Service (port 8001)

### GET /customers/
List all customers.

**Response** `200 OK`
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "0123456789",
    "address": "123 Main St",
    "auth_user_id": 1,
    "created_at": "2026-03-10T12:00:00Z"
  }
]
```

### POST /customers/
Register a new customer. Automatically creates a cart via cart-service.

**Request Body**
```json
{
  "name": "John Doe",          // required, max 255 chars
  "email": "john@example.com", // required, unique
  "phone": "0123456789",       // optional, max 20 chars
  "address": "123 Main St"     // optional
}
```

**Response** `201 Created` — Customer object
**Error** `400 Bad Request` — Validation errors

**Side Effects:**
- `POST cart-service:8000/carts/` with `{"customer_id": <id>}` (HTTP fallback)
- Publishes `customer.created` event via RabbitMQ (async cart creation)

### GET /customers/{id}/
Get customer by ID.

**Response** `200 OK` — Customer object
**Error** `404 Not Found`

### PUT /customers/{id}/
Update customer (partial update supported).

**Request Body** — Any subset of customer fields
**Response** `200 OK` — Updated customer
**Error** `400 Bad Request` | `404 Not Found`

### DELETE /customers/{id}/
Delete customer.

**Response** `204 No Content`
**Error** `404 Not Found`

---

## 2. Book Service (port 8002)

### GET /books/
List all books.

**Response** `200 OK`
```json
[
  {
    "id": 1,
    "title": "Django for Beginners",
    "author": "William Vincent",
    "price": "29.99",
    "stock": 50,
    "category_id": 1,
    "isbn": "9781735467221",
    "description": "A beginner guide to Django",
    "created_at": "2026-03-10T12:00:00Z"
  }
]
```

### POST /books/
Create a new book.

**Request Body**
```json
{
  "title": "Django for Beginners",    // required, max 255 chars
  "author": "William Vincent",        // required, max 255 chars
  "price": "29.99",                   // required, decimal, >= 0
  "stock": 50,                        // optional, default 0, >= 0
  "category_id": 1,                   // optional, nullable
  "isbn": "9781735467221",            // optional, max 13 chars
  "description": "A beginner guide"   // optional
}
```

**Response** `201 Created` — Book object
**Error** `400 Bad Request`

### GET /books/{id}/
Get book by ID.

**Response** `200 OK` — Book object
**Error** `404 Not Found`

### PUT /books/{id}/
Update book (partial update supported).

**Request Body** — Any subset of book fields
**Response** `200 OK` — Updated book
**Error** `400 Bad Request` | `404 Not Found`

### DELETE /books/{id}/
Delete book.

**Response** `204 No Content`
**Error** `404 Not Found`

---

## 3. Cart Service (port 8003)

### POST /carts/
Create a cart for a customer.

**Request Body**
```json
{
  "customer_id": 1  // required, unique per customer
}
```

**Response** `201 Created`
```json
{
  "id": 1,
  "customer_id": 1,
  "created_at": "2026-03-10T12:00:00Z",
  "items": []
}
```

**Error** `400 Bad Request`

### GET /carts/{customer_id}/
Get all items in customer's cart.

**Response** `200 OK`
```json
[
  {
    "id": 1,
    "cart": 1,
    "book_id": 1,
    "quantity": 2
  }
]
```

**Error** `404 Not Found` — Cart not found

### POST /cart-items/
Add an item to cart. If item already exists, increments quantity.

**Request Body**
```json
{
  "customer_id": 1,  // required
  "book_id": 1,      // required
  "quantity": 2       // optional, default 1, >= 1
}
```

**Response** `201 Created` — CartItem object
**Error** `404 Not Found` — Book or cart not found
**Error** `503 Service Unavailable` — Book service unreachable

**Side Effect:** Verifies book exists via `GET book-service:8000/books/{book_id}/`

### PUT /cart-items/{id}/
Update cart item quantity.

**Request Body**
```json
{
  "quantity": 3  // >= 1
}
```

**Response** `200 OK` — Updated CartItem
**Error** `404 Not Found`

### DELETE /cart-items/{id}/
Remove item from cart.

**Response** `204 No Content`
**Error** `404 Not Found`

### DELETE /carts/{customer_id}/clear/
Clear all items from customer's cart.

**Response** `204 No Content`
**Error** `404 Not Found`

---

## 4. Order Service (port 8007)

### GET /orders/
List orders. Optionally filter by customer.

**Query Parameters**
- `customer_id` (optional) — Filter by customer ID

**Response** `200 OK`
```json
[
  {
    "id": 1,
    "customer_id": 1,
    "total_amount": "59.98",
    "status": "PENDING",
    "shipping_address": "123 Main St",
    "payment_method": "COD",
    "shipping_method": "STANDARD",
    "created_at": "2026-03-10T12:00:00Z",
    "items": [
      {
        "id": 1,
        "order": 1,
        "book_id": 1,
        "quantity": 2,
        "price": "29.99"
      }
    ]
  }
]
```

### POST /orders/
Create order from customer's cart.

**Request Body**
```json
{
  "customer_id": 1,                    // required
  "shipping_address": "123 Main St",   // optional
  "payment_method": "COD",             // optional, default "COD"
  "shipping_method": "STANDARD"        // optional, default "STANDARD"
}
```

**Response** `201 Created` — Order object with items
**Error** `400 Bad Request` — Cart empty or book not found
**Error** `404 Not Found` — Cart not found
**Error** `503 Service Unavailable` — Cart/Book service unreachable

**Order Creation Flow:**
1. Fetches cart items from `GET cart-service:8000/carts/{customer_id}/`
2. Fetches book price for each item from `GET book-service:8000/books/{book_id}/`
3. Creates Order + OrderItems, calculates total
4. Triggers payment via `POST pay-service:8000/payments/`
5. Triggers shipping via `POST ship-service:8000/shipments/`
6. Clears cart via `DELETE cart-service:8000/carts/{customer_id}/clear/`

**Status Values:** `PENDING` | `PAID` | `SHIPPING` | `COMPLETED` | `CANCELLED`

### GET /orders/{id}/
Get order by ID (includes items).

**Response** `200 OK` — Order object with items
**Error** `404 Not Found`

### PUT /orders/{id}/
Update order status.

**Request Body**
```json
{
  "status": "PAID"
}
```

**Response** `200 OK` — Updated order
**Error** `404 Not Found`

---

## 5. Payment Service (port 8008)

### GET /payments/
List payments. Optionally filter by order.

**Query Parameters**
- `order_id` (optional) — Filter by order ID

**Response** `200 OK`
```json
[
  {
    "id": 1,
    "order_id": 1,
    "amount": "59.98",
    "method": "COD",
    "status": "PENDING",
    "created_at": "2026-03-10T12:00:00Z"
  }
]
```

**Method Values:** `CREDIT_CARD` | `PAYPAL` | `COD`
**Status Values:** `PENDING` | `COMPLETED` | `FAILED`

### POST /payments/
Create a payment record.

**Request Body**
```json
{
  "order_id": 1,       // required
  "amount": "59.98",   // required, decimal
  "method": "COD"      // optional, default "COD"
}
```

**Response** `201 Created` — Payment object
**Error** `400 Bad Request`

### GET /payments/{id}/
Get payment by ID.

**Response** `200 OK` — Payment object
**Error** `404 Not Found`

### PUT /payments/{id}/
Update payment status.

**Request Body**
```json
{
  "status": "COMPLETED"
}
```

**Response** `200 OK` — Updated payment
**Error** `404 Not Found`

---

## 6. Shipping Service (port 8009)

### GET /shipments/
List shipments. Optionally filter by order.

**Query Parameters**
- `order_id` (optional) — Filter by order ID

**Response** `200 OK`
```json
[
  {
    "id": 1,
    "order_id": 1,
    "address": "123 Main St",
    "method": "STANDARD",
    "status": "PENDING",
    "tracking_number": "TRK-a1b2c3d4",
    "created_at": "2026-03-10T12:00:00Z"
  }
]
```

**Method Values:** `STANDARD` | `EXPRESS`
**Status Values:** `PENDING` | `SHIPPED` | `DELIVERED`

### POST /shipments/
Create a shipment. Tracking number auto-generated.

**Request Body**
```json
{
  "order_id": 1,              // required
  "address": "123 Main St",   // required
  "method": "STANDARD"        // optional, default "STANDARD"
}
```

**Response** `201 Created` — Shipment object (includes auto-generated tracking_number)
**Error** `400 Bad Request`

### GET /shipments/{id}/
Get shipment by ID.

**Response** `200 OK` — Shipment object
**Error** `404 Not Found`

### PUT /shipments/{id}/
Update shipment status.

**Request Body**
```json
{
  "status": "SHIPPED"
}
```

**Response** `200 OK` — Updated shipment
**Error** `404 Not Found`

---

## 7. Comment-Rate Service (port 8010)

### GET /reviews/
List all reviews.

**Response** `200 OK`
```json
[
  {
    "id": 1,
    "book_id": 1,
    "customer_id": 1,
    "rating": 5,
    "comment": "Great book!",
    "created_at": "2026-03-10T12:00:00Z"
  }
]
```

### POST /reviews/
Create a review. One review per (book, customer) pair.

**Request Body**
```json
{
  "book_id": 1,         // required
  "customer_id": 1,     // required
  "rating": 5,          // required, 1-5
  "comment": "Great!"   // optional
}
```

**Response** `201 Created` — Review object
**Error** `400 Bad Request` — Validation or duplicate

### GET /reviews/book/{book_id}/
Get reviews for a specific book with aggregated stats.

**Response** `200 OK`
```json
{
  "book_id": 1,
  "average_rating": 4.5,
  "total_reviews": 10,
  "reviews": [
    {
      "id": 1,
      "book_id": 1,
      "customer_id": 1,
      "rating": 5,
      "comment": "Great book!",
      "created_at": "2026-03-10T12:00:00Z"
    }
  ]
}
```

### GET /reviews/top-rated/
Get top-rated book IDs sorted by average rating.

**Query Parameters**
- `limit` (optional, default 10) — Number of results

**Response** `200 OK`
```json
[
  {
    "book_id": 1,
    "avg_rating": 4.8
  },
  {
    "book_id": 3,
    "avg_rating": 4.5
  }
]
```

---

## 8. Catalog Service (port 8006)

### GET /categories/
List all categories.

**Response** `200 OK`
```json
[
  {
    "id": 1,
    "name": "Fiction",
    "description": "Fiction books",
    "created_at": "2026-03-10T12:00:00Z"
  }
]
```

### POST /categories/
Create a category.

**Request Body**
```json
{
  "name": "Fiction",              // required, unique, max 255 chars
  "description": "Fiction books"  // optional
}
```

**Response** `201 Created` — Category object
**Error** `400 Bad Request`

### GET /categories/{id}/
Get category by ID.

**Response** `200 OK` — Category object
**Error** `404 Not Found`

### PUT /categories/{id}/
Update category (partial update supported).

**Request Body** — Any subset of category fields
**Response** `200 OK` — Updated category
**Error** `400 Bad Request` | `404 Not Found`

### DELETE /categories/{id}/
Delete category.

**Response** `204 No Content`
**Error** `404 Not Found`

---

## 9. Staff Service (port 8004)

### GET /staff/
List all staff members.

**Response** `200 OK`
```json
[
  {
    "id": 1,
    "name": "Alice",
    "email": "alice@store.com",
    "role": "staff",
    "auth_user_id": 2,
    "created_at": "2026-03-10T12:00:00Z"
  }
]
```

### POST /staff/
Create a staff member.

**Request Body**
```json
{
  "name": "Alice",             // required, max 255 chars
  "email": "alice@store.com",  // required, unique
  "role": "staff"              // optional, default "staff", max 50 chars
}
```

**Response** `201 Created` — Staff object
**Error** `400 Bad Request`

### GET /staff/{id}/
Get staff by ID.

**Response** `200 OK` — Staff object
**Error** `404 Not Found`

### PUT /staff/{id}/
Update staff (partial update supported).

**Request Body** — Any subset of staff fields
**Response** `200 OK` — Updated staff
**Error** `400 Bad Request` | `404 Not Found`

### DELETE /staff/{id}/
Delete staff member.

**Response** `204 No Content`
**Error** `404 Not Found`

---

## 10. Manager Service (port 8005)

### GET /managers/
List all managers.

**Response** `200 OK`
```json
[
  {
    "id": 1,
    "name": "Bob",
    "email": "bob@store.com",
    "department": "Sales",
    "auth_user_id": 3,
    "created_at": "2026-03-10T12:00:00Z"
  }
]
```

### POST /managers/
Create a manager.

**Request Body**
```json
{
  "name": "Bob",              // required, max 255 chars
  "email": "bob@store.com",   // required, unique
  "department": "Sales"       // optional, max 100 chars
}
```

**Response** `201 Created` — Manager object
**Error** `400 Bad Request`

### GET /managers/{id}/
Get manager by ID.

**Response** `200 OK` — Manager object
**Error** `404 Not Found`

### PUT /managers/{id}/
Update manager (partial update supported).

**Request Body** — Any subset of manager fields
**Response** `200 OK` — Updated manager
**Error** `400 Bad Request` | `404 Not Found`

### DELETE /managers/{id}/
Delete manager.

**Response** `204 No Content`
**Error** `404 Not Found`

---

## 11. Recommender AI Service (port 8011)

### GET /recommendations/{customer_id}/
Get personalized book recommendations.

**Query Parameters**
- `limit` (optional, default 5) — Max recommendations to return

**Response** `200 OK`
```json
{
  "customer_id": 1,
  "recommendations": [
    {
      "id": 1,
      "title": "Django for Beginners",
      "author": "William Vincent",
      "price": "29.99",
      "stock": 50,
      "category_id": 1,
      "isbn": "9781735467221",
      "description": "A beginner guide",
      "created_at": "2026-03-10T12:00:00Z",
      "avg_rating": 4.8
    }
  ]
}
```

**Algorithm:**
1. Fetch top-rated books from `GET comment-rate-service:8000/reviews/top-rated/?limit={limit}`
2. Enrich each book with details from `GET book-service:8000/books/{book_id}/`
3. If fewer than `limit` results, fill with latest books from `GET book-service:8000/books/`

---

## 12. API Gateway (port 8000)

The API Gateway provides a web UI (HTML templates) that proxies to backend services.

| Method   | Path                             | Backend Call                                              | Description         |
|----------|----------------------------------|-----------------------------------------------------------|---------------------|
| GET      | `/`                              | —                                                         | Home page           |
| GET      | `/books/`                        | `GET book:8000/books/`                                    | List books          |
| GET/POST | `/books/create/`                 | `POST book:8000/books/`                                   | Create book         |
| GET      | `/customers/`                    | `GET customer:8000/customers/`                            | List customers      |
| GET/POST | `/customers/register/`           | `POST customer:8000/customers/`                           | Register customer   |
| GET      | `/cart/{customer_id}/`           | `GET cart:8000/carts/{id}/` + `GET book:8000/books/{id}/` | View cart (enriched) |
| POST     | `/cart/add/`                     | `POST cart:8000/cart-items/`                               | Add to cart         |
| GET      | `/orders/{customer_id}/`         | `GET order:8000/orders/?customer_id={id}`                 | List orders         |
| POST     | `/orders/create/`                | `POST order:8000/orders/`                                 | Create order        |
| GET      | `/reviews/book/{book_id}/`       | `GET review:8000/reviews/book/{id}/`                      | Book reviews        |
| POST     | `/reviews/add/`                  | `POST review:8000/reviews/`                               | Add review          |
| GET      | `/recommendations/{customer_id}/`| `GET recommender:8000/recommendations/{id}/`              | Recommendations     |
| GET      | `/staff/`                        | `GET staff:8000/staff/`                                   | List staff          |
| GET/POST | `/staff/create/`                 | `POST staff:8000/staff/`                                  | Create staff        |
| GET      | `/managers/`                     | `GET manager:8000/managers/`                               | List managers       |
| GET/POST | `/managers/create/`              | `POST manager:8000/managers/`                             | Create manager      |
| GET      | `/categories/`                   | `GET catalog:8000/categories/`                            | List categories     |
| GET/POST | `/categories/create/`            | `POST catalog:8000/categories/`                           | Create category     |

---

## Error Response Format

All error responses follow this format:
```json
{
  "error": "Error message description"
}
```

Common HTTP status codes:
- `200 OK` — Successful GET/PUT
- `201 Created` — Successful POST
- `204 No Content` — Successful DELETE
- `400 Bad Request` — Validation error
- `404 Not Found` — Resource not found
- `503 Service Unavailable` — Dependent service unreachable
- `403 Forbidden` — Insufficient role permissions (RBAC)

---

## 13. Auth Service (port 8012)

### POST /auth/register/
Register a new user and receive JWT token.

**Request Body**
```json
{
  "username": "johndoe",       // required, unique, max 150 chars
  "email": "john@example.com", // required, unique
  "password": "securepass",    // required
  "role": "CUSTOMER"           // optional, default "CUSTOMER"
}
```

**Role Values:** `CUSTOMER` | `STAFF` | `MANAGER` | `ADMIN`

**Response** `201 Created`
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "role": "CUSTOMER",
    "created_at": "2026-03-10T12:00:00Z"
  }
}
```

**Error** `400 Bad Request` — Missing fields, duplicate username/email

**Side Effect:** Publishes `user.created.{role}` event via RabbitMQ (e.g., `user.created.customer`)

### POST /auth/login/
Authenticate user and receive JWT token.

**Request Body**
```json
{
  "username": "johndoe",
  "password": "securepass"
}
```

**Response** `200 OK` — Same format as register response
**Error** `401 Unauthorized` — Invalid credentials

### POST /auth/verify/
Verify a JWT token.

**Request Body**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

Or via `Authorization: Bearer <token>` header.

**Response** `200 OK`
```json
{
  "valid": true,
  "user": {
    "user_id": 1,
    "username": "johndoe",
    "role": "CUSTOMER"
  }
}
```

**Error** `401 Unauthorized` — Invalid or expired token

### GET /auth/users/
List all users (internal use).

**Response** `200 OK` — Array of user objects (without password)

---

## 14. RabbitMQ Events

**Exchange:** `bookstore` (type: topic, durable)
**Queue Naming:** `{service-name}.{routing-key}`

| Routing Key | Publisher | Consumer | Payload |
|-------------|----------|----------|---------|
| `user.created.customer` | auth-service | customer-service | `{"user_id": 1, "username": "john", "email": "john@example.com", "role": "CUSTOMER"}` |
| `user.created.staff` | auth-service | staff-service | `{"user_id": 2, "username": "alice", "email": "alice@store.com", "role": "STAFF"}` |
| `user.created.manager` | auth-service | manager-service | `{"user_id": 3, "username": "bob", "email": "bob@store.com", "role": "MANAGER"}` |
| `customer.created` | customer-service | cart-service | `{"customer_id": 1}` |
| `order.created` | order-service | — | `{"order_id": 1, "customer_id": 1, "total_amount": "59.98", "payment_id": 1, "shipment_id": 1}` |
| `order.status_changed` | order-service | — | `{"order_id": 1, "status": "PAID"}` |
| `payment.completed` | pay-service | order-service | `{"payment_id": 1, "order_id": 1}` |
| `shipment.shipped` | ship-service | order-service | `{"shipment_id": 1, "order_id": 1}` |

---

## 15. RBAC Permission Matrix

Access control enforced at API Gateway level based on JWT role.

| Resource | CUSTOMER | STAFF | MANAGER | ADMIN |
|----------|----------|-------|---------|-------|
| Books (read) | Yes | Yes | Yes | Yes |
| Books (create/edit/delete) | No | Yes | Yes | Yes |
| Customers (list/edit) | No | Yes | Yes | Yes |
| Customers (delete) | No | No | Yes | Yes |
| Staff (list) | No | Yes | Yes | Yes |
| Staff (create/edit) | No | No | Yes | Yes |
| Staff (delete) | No | No | No | Yes |
| Managers (list) | No | No | Yes | Yes |
| Managers (create/edit/delete) | No | No | No | Yes |
| Categories (create/edit) | No | Yes | Yes | Yes |
| Categories (delete) | No | No | Yes | Yes |
| Cart / Orders / Reviews / Recommendations | Yes | Yes | Yes | Yes |
