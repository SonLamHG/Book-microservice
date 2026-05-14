# Real-world Datasets for AI Model Training

**Date:** 2026-05-14
**Status:** Draft — pending user review
**Owner:** AI/Recommender pipeline

## 1. Problem

Tất cả training data của `ai-service` hiện tại là synthetic, deterministic (seed=42), 5 personas, 27 sản phẩm hand-curated. Cụ thể:

- [ai-service/data/product_corpus.jsonl](../../../ai-service/data/product_corpus.jsonl) — 27 sản phẩm viết tay
- [ai-service/data/user_behavior.csv](../../../ai-service/data/user_behavior.csv) — sinh từ [generate_datasets.py](../../../ai-service/data/generate_datasets.py)
- [ai-service/data/graph_triples.csv](../../../ai-service/data/graph_triples.csv) — derive từ behavior synthetic

Không phản ánh được phân phối hành vi thật, vocabulary quá nhỏ để LSTM học được pattern có ý nghĩa, không có giá trị thuyết phục cho thesis.

## 2. Goals

1. Train 3 thành phần AI (LSTM, Neo4j Graph, FAISS RAG) trên dataset thật từ Kaggle.
2. Giữ cho hệ thống end-to-end (cart → order → payment) vẫn demo được — gợi ý từ AI phải trả về `product_id` tồn tại trong `seed_data.sql`.
3. Pipeline tái lập được (download → preprocess → train) bằng một lệnh duy nhất.
4. Không phình DB chính: `seed_data.sql` giữ ở quy mô demo (~500 sản phẩm), không nhồi 10k sách.

## 3. Decisions (đã chốt với user)

| Quyết định | Lựa chọn |
|---|---|
| Hướng catalogue | **B — Mirror subset.** Sinh lại `seed_data.sql` với 500 sách thật. AI train trên dataset gốc đầy đủ rồi project về subset khi infer. |
| Advisory KB tiếng Việt | Giữ markdown viết tay + auto-import metadata sách từ catalogue mới. Không dịch dataset tiếng Anh sang tiếng Việt. |
| Training pipeline | Offline: `make train-ai` chạy local, ghi `lstm_weights.pt`, **commit** vào git. Container chỉ load weight, không train ở startup. |

## 4. Dataset

**Nguồn duy nhất: [Amazon Books Reviews](https://www.kaggle.com/datasets/mohamedbakhet/amazon-books-reviews)** (Kaggle, ~1 GB)

Lý do chọn 1 dataset duy nhất thay vì kết hợp Goodbooks-10k + Retailrocket:
- Có **timestamp** trên từng review → trực tiếp build sequence cho LSTM.
- Có **2 file**: `Books_rating.csv` (User_id, Title, review/score, review/time) và `books_data.csv` (Title, description, authors, categories, image, publishedDate, publisher) — đủ cho cả LSTM, RAG, Graph.
- Items đều là sách → khớp domain. Retailrocket items là e-commerce chung chung, không map được sang sách.
- Goodbooks-10k thiếu timestamp ratings.

Các field sẽ dùng:
- `Books_rating.csv`: `User_id`, `Title`, `review/score`, `review/time` (Unix epoch).
- `books_data.csv`: `Title`, `description`, `authors`, `categories`, `image`, `publishedDate`, `publisher`.

## 5. Architecture

```
                 ┌──────────────────────────────────┐
Kaggle ────────► │ scripts/download_datasets.py     │
(amazon-books-   │  (uses kagglehub, caches in      │
 reviews)        │  ai-service/data/raw/)           │
                 └────────────┬─────────────────────┘
                              │
                              ▼
                 ┌──────────────────────────────────┐
                 │ scripts/preprocess.py            │
                 │  1. pick top-N books (by review  │
                 │     count, balanced across       │
                 │     categories)                  │
                 │  2. emit:                        │
                 │     - product_corpus.jsonl       │
                 │     - user_behavior.csv          │
                 │     - graph_triples.csv          │
                 │     - seed_data_books.sql        │
                 └────────────┬─────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
     ┌─────────────────┐             ┌──────────────────┐
     │ make train-ai   │             │ data/seed_all.sh │
     │  → lstm_weights │             │  ingests new     │
     │    .pt (commit) │             │  seed_data.sql   │
     └─────────────────┘             └──────────────────┘
              │
              ▼
     ┌─────────────────────────────────────────────────┐
     │ ai-service container startup                    │
     │   - LSTM_TRAIN_AT_STARTUP=false (default)       │
     │   - load lstm_weights.pt                        │
     │   - seed Neo4j from graph_triples.csv           │
     │   - build FAISS from product_corpus.jsonl       │
     └─────────────────────────────────────────────────┘
```

Dataset gốc (~1 GB) **không** commit. Output preprocessed (~5–10 MB) và `lstm_weights.pt` (~5–50 MB tùy vocab) **có** commit.

## 6. Subset selection — Mirror strategy

Mục tiêu: chọn **500 sách** từ dataset gốc (~212k sách trong Amazon Books) sao cho:
- Phân bổ đều qua **5 category sách** hiện có trong [data/seed_data.sql](../../../data/seed_data.sql) (id 1–5). Các category 6–9 là electronics/fashion — không đụng tới.
- Mỗi sách có ≥ 50 reviews → đủ tín hiệu training.
- Mỗi category có ~100 sách (5 cat × 100 sách = 500).

**Category mapping (Amazon `categories` → internal id):**

| Amazon keyword (case-insensitive, match đầu tiên thắng) | → internal id | VN name (giữ nguyên từ seed) |
|---|---|---|
| Fiction, Literary, Literature, Poetry, Drama | 1 | Van hoc Viet Nam |
| Computers, Programming, Technology, Science, Mathematics, Engineering | 2 | Khoa hoc & Cong nghe |
| Business, Economics, Investing, Management, Finance | 3 | Kinh te & Kinh doanh |
| Juvenile, Comics, Graphic Novels, Children, Picture Books | 4 | Thieu nhi |
| Self-Help, Psychology, Personal Growth, Philosophy, Religion, Health | 5 | Ky nang song |
| (fallback nếu không match) | 1 | Van hoc Viet Nam (default bucket) |

Mapping hard-code trong `scripts/category_mapping.py`. Sách rơi vào fallback bucket được flag để dễ inspect; nếu fallback > 30% → preprocess in cảnh báo và đề xuất bổ sung keyword.

**Lưu ý:** Tên category vẫn là tiếng Việt từ seed cũ (Van hoc Viet Nam, etc.) nhưng nội dung sách bên trong là tiếng Anh từ Amazon — chấp nhận được vì thesis demo nhấn vào AI quality, không vào i18n. Document rõ trade-off này trong README.

## 7. Schema mapping — Amazon → product-service

| Amazon field | → Django model field | Notes |
|---|---|---|
| `Title` | `Product.name` (truncate 255) + `Book` 1:1 | |
| `description` | `Product.description` | Fallback empty string |
| `authors` (list, tách bằng `;`) | `Book.author` (joined comma) | |
| `publisher` | `Book.publisher` | |
| `categories[0]` → mapping ở §6 | `Product.category_id` | |
| `Title` derived ISBN qua hash hoặc bỏ | `Book.isbn` | Amazon không có ISBN sạch — để empty |
| (sinh) | `Product.price` | Random VND 50k–500k seeded từ hash(title) để stable |
| (sinh) | `Product.stock` | Random 20–100 |
| `product_id` | autoincrement từ 1 | `seed_data.sql` reset bảng |

User_id của Amazon (~ chuỗi A1B2C3) sẽ map sang `customer_id` integer 1..N qua một dict `user_id_map.json`. Chỉ giữ những user có ≥ 5 reviews trên 500 sách subset (để LSTM có sequence dùng được).

## 8. Output artifacts (sau preprocess)

```
ai-service/data/
├── raw/                              # gitignored, ~1 GB Kaggle download
│   ├── Books_rating.csv
│   └── books_data.csv
├── product_corpus.jsonl              # NEW: 500 sách thật (từ Amazon)
├── user_behavior.csv                 # NEW: ~50k–200k events từ Amazon ratings
├── graph_triples.csv                 # NEW: derived
├── lstm_weights.pt                   # NEW: trained weights (commit)
├── user_id_map.json                  # NEW: Amazon User_id → internal int (commit)
└── seed_data_books.sql               # NEW: drop-in cho data/seed_data.sql section "product-service"
```

`generate_datasets.py` cũ → **xóa** (synthetic generator không còn dùng).

## 9. Training pipeline

**File mới:** `scripts/download_datasets.py` — dùng `kagglehub` để pull `mohamedbakhet/amazon-books-reviews`. Cache tại `ai-service/data/raw/`. Idempotent (skip nếu đã có).

**File mới:** `scripts/preprocess.py` — đọc `data/raw/`, sinh 4 artifact ở §8.

**File mới:** `Makefile` (root) với targets:
```makefile
download-datasets:    # Pull Amazon Books Reviews từ Kaggle
preprocess:           # Sinh corpus + behavior + graph + seed_books.sql
train-ai:             # Run ai-service/app/lstm/train.py với data đã preprocess
data-pipeline:        # = download + preprocess + train (one-shot)
```

**File sửa:** [ai-service/app/config.py](../../../ai-service/app/config.py)
- Default `LSTM_TRAIN_AT_STARTUP = false` (đảo lại từ true).
- Default `SEED_GRAPH_AT_STARTUP = true` (giữ — graph nhẹ, seed từ CSV nhanh).

**File sửa:** [ai-service/app/bootstrap.py](../../../ai-service/app/bootstrap.py)
- Khi `LSTM_TRAIN_AT_STARTUP=false`: chỉ load weight từ `lstm_weights.pt`. Nếu thiếu weight → log warning + LSTM contribute 0 vào hybrid.

**File sửa:** [ai-service/Dockerfile](../../../ai-service/Dockerfile)
- COPY `data/lstm_weights.pt` vào image (đã commit nên có sẵn).

## 10. Seed integration với hệ thống chính

`seed_data_books.sql` là output của preprocess, KHÔNG ghi đè trực tiếp `data/seed_data.sql` để tránh conflict với các section khác (cart, order, review, electronics, fashion).

**ID layout sau khi reseed:**
- Books: id **1–500** (Amazon)
- Electronics: id **501–506** (shift từ 16–21 cũ)
- Fashion: id **507–512** (shift từ 22–27 cũ)

Phải shift electronics/fashion để tránh collision với 500 sách mới chiếm id 1–500. Section cart/order/review trong `seed_data.sql` cần update `book_id` references theo ID mới (chọn vài sách Amazon đầu tiên làm demo cart/order).

**Workflow:**
1. `scripts/preprocess.py` ghi `seed_data_books.sql` chứa: TRUNCATE `app_book, app_electronics, app_fashion, app_product` → INSERT 500 books (id 1–500) + 6 electronics (id 501–506) + 6 fashion (id 507–512).
2. Cùng file cũng emit lại section cart/orderitem/review với `book_id` trỏ vào 5–10 sách Amazon đầu tiên (id 1–10) để demo end-to-end vẫn có dữ liệu.
3. Sửa [data/seed_all.sh](../../../data/seed_all.sh): chạy `seed_data_books.sql` THAY VÌ section product/cart/order/review của `seed_data.sql` cũ (giữ section catalog category + customer/staff/manager).
4. Tách `data/seed_data.sql` thành 2 file: `seed_categories.sql` (giữ) + phần product cũ (xóa).
5. Nội dung sách là tiếng Anh — chấp nhận được cho thesis demo nhấn vào AI quality.

**Customer mapping:** không sinh user thật từ Amazon vào `customer-service` (giữ 5 customer hiện có cho login demo). `user_behavior.csv` dùng internal customer_id 1..N riêng, chỉ tồn tại trong AI data — **không** insert vào MySQL `customer_db`. Document rõ trong `ai-service/README.md`.

## 11. Advisory Chat KB

Giữ nguyên 3 markdown ở [advisory-chat-service/kb_data/](../../../advisory-chat-service/kb_data/) (policies, FAQ, genre guide — tiếng Việt, viết tay).

Sửa [advisory-chat-service/app/management/commands/load_kb.py](../../../advisory-chat-service/app/management/commands/load_kb.py):
- `_load_book_catalog()` đã fetch từ `product-service/books/` — sau khi reseed 500 sách Amazon, command này tự động re-embed catalog mới. Không cần sửa code, chỉ cần chạy lại `python manage.py load_kb --clear` sau seed.

## 12. Files to add / modify / delete

**Add:**
- `scripts/__init__.py`, `scripts/download_datasets.py`, `scripts/preprocess.py`
- `scripts/category_mapping.py` — dict mapping Amazon → internal category_id
- `Makefile`
- `ai-service/data/lstm_weights.pt` (build artifact, commit)
- `ai-service/data/user_id_map.json` (build artifact, commit)
- `ai-service/data/seed_data_books.sql` (build artifact, commit)

**Modify:**
- `ai-service/data/product_corpus.jsonl` — replaced với output preprocess
- `ai-service/data/user_behavior.csv` — replaced
- `ai-service/data/graph_triples.csv` — replaced
- `ai-service/app/config.py` — đảo default `LSTM_TRAIN_AT_STARTUP`
- `ai-service/app/bootstrap.py` — load-only path
- `ai-service/Dockerfile` — copy weights
- `ai-service/README.md` — document pipeline mới
- `ai-service/requirements.txt` — thêm `kagglehub` (chỉ cho dev/preprocess; không cần ở runtime container — dời vào `requirements-dev.txt`)
- `data/seed_all.sh` — gọi thêm `seed_data_books.sql`
- `.gitignore` — ignore `ai-service/data/raw/`
- `CLAUDE.md` — update section AI Service mô tả pipeline mới

**Delete:**
- `ai-service/data/generate_datasets.py` — synthetic generator không còn dùng

## 13. Acceptance criteria

1. `make data-pipeline` chạy từ máy mới (sau khi cấu hình Kaggle credentials) thành công, sinh đủ 4 artifact ở §8.
2. `docker-compose up --build` từ clone mới: ai-service start được, KHÔNG train lại, hybrid `GET /recommend?user_id=1` trả về top 10 sản phẩm với `product_id ∈ [1, 500]`.
3. UI gateway (port 8000) hiển thị 500 sách mới (id 1–500), 6 electronics (501–506), 6 fashion (507–512). Cart/order demo data vẫn click-through được.
4. `docker-compose exec advisory-chat-service python manage.py load_kb --clear` re-embed thành công 500 sách + 3 markdown KB.
5. LSTM training log thể hiện loss giảm ổn định qua 30 epoch.
6. Repo size tăng không quá 100 MB sau commit (weights + seed SQL + preprocessed CSVs cộng lại).
7. Không có service nào (cart, order, payment, comment-rate) bị broken sau reseed — đặt 1 order test thành công thông qua UI.

## 14. Out of scope

- Train embedding model riêng (vẫn dùng `all-MiniLM-L6-v2` pretrained).
- Sinh customer thật từ Amazon vào MySQL.
- Vietnamese translation cho mô tả sách Amazon.
- A/B test giữa hybrid weights khác nhau (giữ default 0.4/0.4/0.2).
- Migration cho `recommender-ai-service` legacy (port 8011) — service này chỉ là top-rated aggregator, không cần training.
- Multi-language support cho FAISS embedding (model `all-MiniLM-L6-v2` đã multilingual ở mức cơ bản).

## 15. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Kaggle dataset bị xóa/đổi schema | Pin version trong download script; document fallback dataset thay thế (Goodbooks-10k) |
| `lstm_weights.pt` quá to khi commit (vocab=500 → ~10 MB OK; vocab=10k → ~150 MB) | Cap vocab ở 500 (= subset size). Nếu vẫn lớn → dùng git-lfs |
| Description tiếng Anh + UI tiếng Việt = trải nghiệm xen kẽ | Document rõ trong README; thesis demo nhấn vào AI quality, không vào UX i18n |
| Preprocess chậm trên máy yếu (1 GB CSV) | Dùng `pandas` với `chunksize`; document RAM tối thiểu 4 GB |
| User chạy `docker-compose up` mà chưa có `lstm_weights.pt` | Bootstrap log rõ warning + fallback "LSTM contributes 0"; hybrid vẫn chạy với Graph + RAG |
