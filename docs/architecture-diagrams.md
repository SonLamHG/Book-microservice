# Architecture Diagrams

## 1. System Overview

```
                    ┌─────────────────────────────────┐
                    │       API Gateway (:8000)        │
                    │  Django (HTML Templates + Proxy) │
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
                          ┌──────────┐┌─────────┐┌─────────┐
                          │ Payment  ││  Ship   ││ Catalog │
                          │ Service  ││ Service ││ Service │
                          │  :8008   ││  :8009  ││  :8006  │
                          └──────────┘└─────────┘└─────────┘

                          ┌──────────┐┌─────────┐
                          │  Staff   ││ Manager │
                          │ Service  ││ Service │
                          │  :8004   ││  :8005  │
                          └──────────┘└─────────┘
```

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
│                           ▼           └──────┬──────┘│
│                    ┌──────────────┐          │       │
│                    │serializers.py│          ▼       │
│                    │              │    ┌───────────┐ │
│                    │CustomerSer.  │    │  SQLite   │ │
│                    └──────────────┘    └───────────┘ │
│                                                        │
│  External Call:                                        │
│  POST cart-service:8000/carts/ (on create)             │
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
│  GET book-service:8000/books/{id}/ (on add)            │
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
│                           ▼           └──────┬───────┘│
│                    ┌──────────────┐          ▼        │
│                    │serializers.py│    ┌───────────┐   │
│                    └──────────────┘    │  SQLite   │   │
│  No external calls                     └───────────┘   │
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
│                           ▼           └──────┬───────┘│
│                    ┌──────────────┐          ▼        │
│                    │serializers.py│    ┌───────────┐   │
│                    └──────────────┘    │  SQLite   │   │
│  No external calls                     └───────────┘   │
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
│             (Web Interface + Service Proxy)             │
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
│                           ├─> book-service     :8002   │
│                           ├─> cart-service     :8003   │
│                           ├─> staff-service    :8004   │
│                           ├─> manager-service  :8005   │
│                           ├─> catalog-service  :8006   │
│                           ├─> order-service    :8007   │
│                           ├─> pay-service      :8008   │
│                           ├─> ship-service     :8009   │
│                           ├─> comment-rate     :8010   │
│                           └─> recommender-ai   :8011   │
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
│  │ customer-service │  │ catalog-service  │  │  cart-service    │  │
│  │ staff-service    │  │ book-service     │  │  order-service   │  │
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
│  Startup Order (depends_on):                           │
│  book-service -> cart-service -> customer-service      │
│  pay-service, ship-service -> order-service            │
│  comment-rate-service -> recommender-ai-service        │
│  all services -> api-gateway                           │
└───────────────────────────────────────────────────────┘
```
