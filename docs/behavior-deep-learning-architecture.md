# Behavior AI Deep Learning Architecture (ASCII Diagram Version)

Tai lieu nay mo ta ro kien truc va luong hoat dong cua chuc nang xay dung behavior profile
dua tren deep learning trong he thong bookstore microservice.

---

## 1) Hinh kien truc chuc nang trong toan he thong

```text
                               +----------------------+
                               |      API Gateway     |
User/Web UI  ----------------> |        (:8000)       |
                               +----------+-----------+
                                          |
                                          v
                               +----------------------+
                               | recommender-ai-svc   |
                               |        (:8011)       |
                               | Advisor + Response   |
                               +----------+-----------+
                                          |
                                          v
                               +----------------------+
                               |  behavior-ai-service |
                               |        (:8013)       |
                               | Behavior Engine+MLP  |
                               +----------+-----------+
                                          |
             +----------------------------+----------------------------+
             |            |               |              |             |
             v            v               v              v             v
     +--------------+ +--------------+ +-------------+ +-------------+ +--------------+
     | customer-svc | | order-svc    | | cart-svc    | | book-svc    | | catalog-svc  |
     |   (:8001)    | |   (:8007)    | |   (:8003)   | |   (:8002)   | |   (:8006)    |
     +--------------+ +--------------+ +-------------+ +-------------+ +--------------+
                                          |
                                          v
                                  +------------------+
                                  | comment-rate-svc |
                                  |      (:8010)     |
                                  +------------------+
```

Y nghia:
- `behavior-ai-service` la tang hoc hanh vi.
- `recommender-ai-service` dung output behavior de tao recommendation/advisor text.

---

## 2) Hinh cau truc ben trong behavior-ai-service

```text
+----------------------------------------------------------------------------------+
|                              behavior-ai-service (:8013)                         |
+----------------------------------------------------------------------------------+
|                                                                                  |
|  +-------------------+        +-----------------------------------------------+  |
|  | app/urls.py       | -----> | app/views.py                                  |  |
|  +-------------------+        | - POST /behavior/train/                        |  |
|                               | - POST /behavior/profile/                      |  |
|                               | - GET  /behavior/status/                       |  |
|                               +----------------------+------------------------+  |
|                                                      |                           |
|                                                      v                           |
|                               +-----------------------------------------------+  |
|                               | app/engine.py                                  |  |
|                               | BehaviorEngine                                 |  |
|                               | - fetch_reference_data()                       |  |
|                               | - _customer_context()                          |  |
|                               | - _build_training_samples()                    |  |
|                               | - train_model() / build_profile()              |  |
|                               +----------------------+------------------------+  |
|                                                      |                           |
|                         +----------------------------+------------------------+  |
|                         |                                                     |  |
|                         v                                                     v  |
|       +--------------------------------------+             +---------------------+|
|       | BehaviorMLPModel                     |             | Heuristic Scoring   ||
|       | - embeddings (user/book/category)    |             | - category affinity ||
|       | - hidden1=24, hidden2=12             |             | - recency           ||
|       | - manual backprop + SGD              |             | - price band        ||
|       +-------------------+------------------+             | - review signal     ||
|                           |                                +----------+----------+|
|                           v                                           |           |
|                +-----------------------------+                        |           |
|                | /app/data/behavior_model    | <----------------------+           |
|                | .json (model artifact)      |                                    |
|                +-----------------------------+                                    |
+----------------------------------------------------------------------------------+
```

---

## 3) Hinh pipeline deep learning (train + infer)

```text
TRAIN PIPELINE
--------------
[Fetch cross-service data]
        |
        v
[Feature engineering per customer]
        |
        v
[Build supervised samples]
  - Positive: purchased/reviewed/in-cart books (label=1)
  - Negative: non-interacted books (label=0)
        |
        v
[Initialize MLP]
  embeddings + dense layers
        |
        v
[Manual training]
  forward -> loss gradient -> backprop -> SGD update
        |
        v
[Save artifact]
  /app/data/behavior_model.json


INFERENCE PIPELINE
------------------
[POST /behavior/profile/]
        |
        v
[Load artifact?]
  yes -> use model
  no  -> lazy train
        |
        v
[Score each candidate book]
  model_score + heuristic_score
        |
        v
[Final score]
  final = 0.75*model + 0.25*heuristic
        |
        v
[Top-N candidate_books + reason_codes]
```

---

## 4) Data source va feature engineering

`BehaviorEngine.fetch_reference_data()` lay du lieu tu:
- `book-service`: danh sach sach + thong tin sach
- `catalog-service`: danh muc/category
- `comment-rate-service`: review/rating
- `customer-service`: danh sach khach hang
- `order-service`: lich su don hang
- `cart-service`: gio hang hien tai theo customer

Feature chinh trong `_customer_context()`:
- Tong don, don 30 ngay, tong chi tieu, gia tri trung binh don
- Muc gia sach trung binh, days since last order
- So item trong cart, so review, rating trung binh da cho
- Muc do tap trung vao category yeu thich, ti le tech/programming
- Recent books / recent categories

---

## 5) Cau truc model deep learning tu viet

`BehaviorMLPModel`:
- Embedding user: 8
- Embedding book: 12
- Embedding category: 6
- Dense hidden 1: 24 (ReLU)
- Dense hidden 2: 12 (ReLU)
- Output: 1 node sigmoid (score 0..1)

Diem quan trong:
- Khong dung TensorFlow/PyTorch/sklearn.
- Toan bo train/infer duoc implement thu cong trong Python.

---

## 6) Output cua behavior profile

`POST /behavior/profile/` tra ve:
- `customer_id`
- `preferred_categories`
- `price_band`
- `signals_summary`
- `candidate_books` (`book_id`, `score`, `reason_codes`)
- `fallback_used`
- `model_version` (`behavior-mlp-v1`)

---

## 7) Tom tat 1 dong (de dua vao slide)

`behavior-ai-service` = tang hoc hanh vi (embedding + MLP tu viet) de bien du lieu mua/review/cart thanh profile ca nhan va danh sach candidate books co diem so cho recommender layer.

