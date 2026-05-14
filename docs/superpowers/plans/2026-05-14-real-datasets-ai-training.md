# Real-world Datasets for AI Training — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace synthetic AI training data with Amazon Books Reviews (Kaggle), mirror 500 real books into seed_data.sql so demo end-to-end stays intact, train LSTM offline and commit weights.

**Architecture:** Single dataset (Amazon Books Reviews) → preprocess script → 4 artifacts (product_corpus.jsonl, user_behavior.csv, graph_triples.csv, seed_data_books.sql) + lstm_weights.pt. Container loads pretrained weights at startup, no in-container training. UI keeps Vietnamese, book content becomes English.

**Tech Stack:** Python 3.11, pandas, kagglehub, sentence-transformers, PyTorch (CPU), psycopg2, Django 4.2, Docker Compose.

**Spec:** [docs/superpowers/specs/2026-05-14-real-datasets-ai-training-design.md](../specs/2026-05-14-real-datasets-ai-training-design.md)

**No pytest:** Codebase has no test suite per CLAUDE.md. Verification uses inline Python scripts that load artifacts and check shape/content, plus curl against running services.

---

## File Structure

**New files:**
- `scripts/__init__.py` — empty package marker
- `scripts/category_mapping.py` — Amazon `categories` field → internal category id (1–5)
- `scripts/download_datasets.py` — `kagglehub` pull, cache to `ai-service/data/raw/`
- `scripts/preprocess.py` — entry point; orchestrates subset selection + emit all 4 artifacts
- `scripts/_io.py` — small helpers for CSV/JSONL writing, deterministic random
- `Makefile` — at repo root, 4 targets
- `requirements-dev.txt` — dev-only deps (kagglehub, pandas)
- `ai-service/data/lstm_weights.pt` — build artifact (committed)
- `ai-service/data/user_id_map.json` — build artifact (committed)
- `ai-service/data/seed_data_books.sql` — build artifact (committed)

**Modified files:**
- `ai-service/data/product_corpus.jsonl` — regenerated
- `ai-service/data/user_behavior.csv` — regenerated
- `ai-service/data/graph_triples.csv` — regenerated
- `ai-service/app/config.py` — flip `LSTM_TRAIN_AT_STARTUP` default to false
- `ai-service/app/bootstrap.py` — add load-only weight path
- `ai-service/app/lstm/inference.py` — make load-only mode resilient
- `ai-service/Dockerfile` — COPY data/ into image
- `ai-service/README.md` — document new pipeline
- `ai-service/requirements.txt` — leave runtime deps; move dev deps out
- `data/seed_all.sh` — load `seed_data_books.sql`
- `data/seed_data.sql` — strip product/cart/order/review sections (moved to seed_data_books.sql)
- `.gitignore` — `ai-service/data/raw/`
- `CLAUDE.md` — update AI Service section

**Deleted:**
- `ai-service/data/generate_datasets.py`

---

## Task 1: Scaffolding — scripts package + Makefile + gitignore

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/_io.py`
- Create: `Makefile`
- Create: `requirements-dev.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Create empty package marker**

Create `scripts/__init__.py` with content:

```python
"""Build-time scripts for the bookstore microservices."""
```

- [ ] **Step 2: Create shared I/O helpers**

Create `scripts/_io.py`:

```python
"""Tiny helpers shared by preprocess scripts.

Kept in a private module so download_datasets.py and preprocess.py
don't repeat themselves. Anything reused by 2+ scripts goes here.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List

REPO_ROOT = Path(__file__).resolve().parent.parent
AI_DATA_DIR = REPO_ROOT / "ai-service" / "data"
RAW_DIR = AI_DATA_DIR / "raw"


def stable_int(s: str, lo: int, hi: int) -> int:
    """Deterministic int in [lo, hi] from a string. Used to fabricate
    stable prices/stock from book titles so two preprocess runs produce
    the same output."""
    h = hashlib.md5(s.encode("utf-8")).hexdigest()
    return lo + int(h, 16) % (hi - lo + 1)


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False))
            f.write("\n")
            n += 1
    return n


def write_csv(path: Path, header: List[str], rows: Iterable[Iterable[Any]]) -> int:
    n = 0
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
            n += 1
    return n


def deterministic_rng(seed: int = 42) -> random.Random:
    return random.Random(seed)
```

- [ ] **Step 3: Create Makefile at repo root**

Create `Makefile`:

```makefile
.PHONY: help download-datasets preprocess train-ai data-pipeline clean-raw

help:
	@echo "Targets:"
	@echo "  download-datasets  Pull Amazon Books Reviews from Kaggle into ai-service/data/raw/"
	@echo "  preprocess         Build product_corpus.jsonl / user_behavior.csv / graph_triples.csv / seed_data_books.sql"
	@echo "  train-ai           Train LSTM and write ai-service/data/lstm_weights.pt"
	@echo "  data-pipeline      Run download + preprocess + train-ai end-to-end"
	@echo "  clean-raw          Delete the raw Kaggle download (~1 GB)"

download-datasets:
	python -m scripts.download_datasets

preprocess:
	python -m scripts.preprocess

train-ai:
	cd ai-service && python -m app.lstm.train

data-pipeline: download-datasets preprocess train-ai

clean-raw:
	rm -rf ai-service/data/raw
```

- [ ] **Step 4: Create dev requirements file**

Create `requirements-dev.txt`:

```
# Dev-only deps used by scripts/ — NOT installed in containers.
kagglehub==0.3.1
pandas==2.2.2
```

- [ ] **Step 5: Update .gitignore**

Append to `.gitignore` (create if missing):

```
# Kaggle raw downloads (large, regenerable)
ai-service/data/raw/
```

If `.gitignore` doesn't exist, create with just those lines plus standard Python ignores:

```
__pycache__/
*.pyc
.venv/
.env
ai-service/data/raw/
```

- [ ] **Step 6: Verify scaffolding**

Run:

```powershell
python -c "from scripts._io import stable_int, RAW_DIR; print(stable_int('Truyen Kieu', 50000, 500000)); print(RAW_DIR)"
```

Expected: prints a stable int (same value every run) and the absolute path to `ai-service/data/raw`.

Run:

```powershell
make help
```

Expected: prints the help text from Makefile. (If `make` not installed on Windows, install via `choco install make` or run targets directly: `python scripts/download_datasets.py`.)

- [ ] **Step 7: Commit**

```powershell
git add scripts/__init__.py scripts/_io.py Makefile requirements-dev.txt .gitignore
git commit -m "scaffold: scripts package + Makefile for AI data pipeline"
```

---

## Task 2: Category mapping module

**Files:**
- Create: `scripts/category_mapping.py`

- [ ] **Step 1: Create the mapping module**

Create `scripts/category_mapping.py`:

```python
"""Map Amazon Books `categories` field to internal category_id (1-5).

The internal taxonomy is fixed by data/seed_data.sql:
  1 = Van hoc Viet Nam       (Fiction / literature / poetry)
  2 = Khoa hoc & Cong nghe   (Programming / science / tech)
  3 = Kinh te & Kinh doanh   (Business / economics / finance)
  4 = Thieu nhi              (Juvenile / comics / children's)
  5 = Ky nang song           (Self-help / psychology / philosophy / religion)

Matching strategy: case-insensitive substring search, first hit wins.
Order in BUCKETS matters — most specific first.
"""
from __future__ import annotations

from typing import Iterable, List, Tuple

FALLBACK_CATEGORY_ID = 1

# Each entry: (internal_id, list of keyword substrings to look for)
BUCKETS: List[Tuple[int, List[str]]] = [
    (4, ["juvenile", "comics", "graphic novel", "children",
         "picture book", "young adult"]),
    (2, ["computer", "programming", "software", "technology",
         "science", "mathematics", "engineering", "physics", "biology"]),
    (3, ["business", "economics", "investing", "management",
         "finance", "marketing", "leadership"]),
    (5, ["self-help", "psychology", "personal growth",
         "philosophy", "religion", "spiritual", "health", "mind"]),
    (1, ["fiction", "literary", "literature", "poetry", "drama",
         "novel", "short stor", "classics"]),
]


def categorise(amazon_categories: Iterable[str]) -> int:
    """Return internal category_id for an Amazon book.

    `amazon_categories` is what the `categories` column of books_data.csv
    looks like after JSON-decode: a list of strings, possibly nested as
    `[['Fiction']]` or `['Fiction', 'Literary']`. Flatten and search."""
    flat: List[str] = []
    for c in amazon_categories or []:
        if isinstance(c, list):
            flat.extend(str(x) for x in c)
        else:
            flat.append(str(c))
    haystack = " | ".join(flat).lower()
    if not haystack.strip():
        return FALLBACK_CATEGORY_ID
    for cat_id, keywords in BUCKETS:
        if any(kw in haystack for kw in keywords):
            return cat_id
    return FALLBACK_CATEGORY_ID
```

- [ ] **Step 2: Verify mapping with inline tests**

Run from repo root:

```powershell
python -c "from scripts.category_mapping import categorise; print(categorise(['Fiction', 'Literary'])); print(categorise(['Computers', 'Programming'])); print(categorise(['Juvenile Fiction'])); print(categorise([])); print(categorise(['Sports']))"
```

Expected output (one per line):
```
1
2
4
1
1
```

(Sports falls through to fallback `1`. Juvenile wins over Fiction because juvenile is checked first.)

- [ ] **Step 3: Commit**

```powershell
git add scripts/category_mapping.py
git commit -m "feat(scripts): Amazon-to-internal category mapping"
```

---

## Task 3: Kaggle download script

**Files:**
- Create: `scripts/download_datasets.py`

- [ ] **Step 1: Create the download script**

Create `scripts/download_datasets.py`:

```python
"""Pull Amazon Books Reviews from Kaggle into ai-service/data/raw/.

Uses kagglehub (newer than the `kaggle` CLI, doesn't require ~/.kaggle/
config — reads $KAGGLE_USERNAME and $KAGGLE_KEY).

Idempotent: if the two CSVs already exist under raw/, skip the download.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from scripts._io import RAW_DIR

DATASET_SLUG = "mohamedbakhet/amazon-books-reviews"
EXPECTED_FILES = ("Books_rating.csv", "books_data.csv")


def _missing(target_dir: Path) -> list[str]:
    return [f for f in EXPECTED_FILES if not (target_dir / f).is_file()]


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    missing = _missing(RAW_DIR)
    if not missing:
        print(f"[download] All files present in {RAW_DIR}, skipping.")
        return 0

    if not (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY")):
        print("ERROR: set $KAGGLE_USERNAME and $KAGGLE_KEY env vars first.",
              file=sys.stderr)
        print("  Create an API token at https://www.kaggle.com/settings/account",
              file=sys.stderr)
        return 1

    try:
        import kagglehub
    except ImportError:
        print("ERROR: kagglehub not installed. Run: pip install -r requirements-dev.txt",
              file=sys.stderr)
        return 1

    print(f"[download] Pulling {DATASET_SLUG} (~1 GB) ...")
    cache_path = Path(kagglehub.dataset_download(DATASET_SLUG))
    print(f"[download] Kagglehub cached at: {cache_path}")

    for fname in EXPECTED_FILES:
        src = cache_path / fname
        if not src.exists():
            print(f"ERROR: expected file missing from Kaggle archive: {fname}",
                  file=sys.stderr)
            return 1
        dst = RAW_DIR / fname
        if dst.exists():
            dst.unlink()
        shutil.copy2(src, dst)
        print(f"[download] Copied {fname} -> {dst}")

    print(f"[download] Done. Files in {RAW_DIR}:")
    for f in EXPECTED_FILES:
        size_mb = (RAW_DIR / f).stat().st_size / 1024 / 1024
        print(f"  {f}: {size_mb:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify the script handles missing credentials cleanly**

Without setting credentials, run from repo root:

```powershell
$env:KAGGLE_USERNAME = $null; $env:KAGGLE_KEY = $null
python -m scripts.download_datasets
```

Expected: exits with code 1 and prints the credentials error message.

- [ ] **Step 3: Run the actual download** (one-time, ~5 min depending on bandwidth)

Set credentials, then:

```powershell
$env:KAGGLE_USERNAME = "<your-kaggle-username>"
$env:KAGGLE_KEY = "<your-kaggle-api-key>"
pip install -r requirements-dev.txt
python -m scripts.download_datasets
```

Expected output ends with:
```
[download] Done. Files in <path>/ai-service/data/raw:
  Books_rating.csv: ~900 MB
  books_data.csv: ~50 MB
```

Verify with:

```powershell
Get-ChildItem ai-service/data/raw/
```

- [ ] **Step 4: Commit (download script only — raw files stay gitignored)**

```powershell
git add scripts/download_datasets.py
git status   # confirm raw/ files do NOT appear (gitignored)
git commit -m "feat(scripts): Kaggle download script for Amazon Books Reviews"
```

---

## Task 4: Preprocess — book subset selection (catalogue + seed SQL)

**Files:**
- Create: `scripts/preprocess.py` (skeleton + book subset step only — extended in later tasks)

- [ ] **Step 1: Create the preprocess script skeleton**

Create `scripts/preprocess.py`:

```python
"""Build the 4 training artifacts from Amazon Books Reviews raw CSVs.

Output (under ai-service/data/):
  product_corpus.jsonl   — 500 books, source-of-truth catalogue
  user_behavior.csv      — user_id, product_id, action, timestamp
  graph_triples.csv      — source_type, source_id, edge_type, target_type, target_id, weight
  seed_data_books.sql    — drop-in SQL for product-service tables
  user_id_map.json       — Amazon User_id (str) -> internal int

Subset strategy:
  - 5 internal book categories (id 1-5)
  - 100 books per category (500 total)
  - Each picked book has >= 50 ratings → strong training signal
  - Books ranked within category by ratings_count desc
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from scripts._io import AI_DATA_DIR, RAW_DIR, stable_int, write_jsonl
from scripts.category_mapping import categorise

BOOKS_PER_CATEGORY = 100
MIN_RATINGS_PER_BOOK = 50

OUT_CORPUS  = AI_DATA_DIR / "product_corpus.jsonl"
OUT_SEED_SQL = AI_DATA_DIR / "seed_data_books.sql"


def _parse_categories_cell(cell: object) -> list:
    """books_data.csv `categories` is a string like "['Fiction']".
    Eval it safely with json after replacing single quotes."""
    if not isinstance(cell, str) or not cell.strip():
        return []
    try:
        return json.loads(cell.replace("'", '"'))
    except json.JSONDecodeError:
        return []


def load_books_and_ratings() -> tuple[pd.DataFrame, pd.DataFrame]:
    books = pd.read_csv(
        RAW_DIR / "books_data.csv",
        usecols=["Title", "description", "authors", "categories",
                 "publisher", "publishedDate"],
    )
    books = books.dropna(subset=["Title"]).drop_duplicates(subset=["Title"])
    print(f"[load] books_data: {len(books)} unique titles")

    # Ratings file is large (~900 MB) — read only what we need.
    ratings = pd.read_csv(
        RAW_DIR / "Books_rating.csv",
        usecols=["Title", "User_id", "review/score", "review/time"],
    )
    ratings = ratings.dropna(subset=["Title", "User_id", "review/time"])
    print(f"[load] ratings: {len(ratings):,} rows")
    return books, ratings


def select_subset(books: pd.DataFrame, ratings: pd.DataFrame) -> pd.DataFrame:
    """Return DataFrame with columns: product_id, name, category_id,
    description, authors, publisher, price, stock."""
    # 1. Count ratings per book to use as popularity signal.
    rating_counts = ratings.groupby("Title").size().rename("rating_count")
    books = books.join(rating_counts, on="Title", how="inner")
    books = books[books["rating_count"] >= MIN_RATINGS_PER_BOOK]
    print(f"[subset] {len(books)} books pass min-ratings filter ({MIN_RATINGS_PER_BOOK})")

    # 2. Assign internal category.
    books = books.assign(
        category_id=books["categories"].map(
            lambda c: categorise(_parse_categories_cell(c))
        )
    )

    # 3. Within each category, pick top-N by rating_count.
    picked = (
        books.sort_values("rating_count", ascending=False)
             .groupby("category_id", group_keys=False)
             .head(BOOKS_PER_CATEGORY)
    )
    print(f"[subset] picked per category:")
    print(picked.groupby("category_id").size().to_string())

    # 4. Assign deterministic product_id starting at 1.
    picked = picked.sort_values(["category_id", "rating_count"],
                                ascending=[True, False]).reset_index(drop=True)
    picked["product_id"] = picked.index + 1

    # 5. Fabricate stable price + stock from title hash.
    picked["price"] = picked["Title"].map(lambda t: stable_int(t, 50_000, 500_000))
    picked["stock"] = picked["Title"].map(lambda t: stable_int(t + "_s", 20, 100))

    return picked[[
        "product_id", "Title", "category_id", "description",
        "authors", "publisher", "price", "stock",
    ]].rename(columns={
        "Title": "name",
        "authors": "author_raw",
        "publisher": "publisher_raw",
    })


def emit_corpus(subset: pd.DataFrame) -> None:
    """Write product_corpus.jsonl with the exact shape ai-service expects.
    See ai-service/app/datasets.py load_product_corpus for consumer."""
    CATEGORY_NAMES = {
        1: "Van hoc Viet Nam",
        2: "Khoa hoc & Cong nghe",
        3: "Kinh te & Kinh doanh",
        4: "Thieu nhi",
        5: "Ky nang song",
    }
    rows = []
    for _, r in subset.iterrows():
        authors = str(r["author_raw"]) if pd.notna(r["author_raw"]) else ""
        # authors field looks like "['Author A', 'Author B']" — flatten
        authors_clean = authors.replace("[", "").replace("]", "").replace("'", "").strip()
        desc = str(r["description"]) if pd.notna(r["description"]) else ""
        rows.append({
            "product_id": int(r["product_id"]),
            "name": str(r["name"])[:255],
            "type": "book",
            "category_id": int(r["category_id"]),
            "category": CATEGORY_NAMES[int(r["category_id"])],
            "price": int(r["price"]),
            "brand_or_author": authors_clean.split(",")[0].strip() or "Unknown",
            "description": desc[:2000],
            "keywords": [],
        })
    n = write_jsonl(OUT_CORPUS, rows)
    print(f"[corpus] wrote {n} entries to {OUT_CORPUS}")


def emit_seed_sql(subset: pd.DataFrame) -> None:
    """Emit the product-service section of seed_data.sql.

    Layout (matches spec §10):
      - DELETE from book/electronics/fashion/product
      - INSERT 500 books (id 1-500)
      - INSERT 6 electronics (id 501-506) — copied verbatim from old seed
      - INSERT 6 fashion     (id 507-512) — copied verbatim from old seed
      - re-insert demo cart/order/review pointing at book IDs 1-10
    """
    def _esc(s: str) -> str:
        return s.replace("'", "''")

    lines = [
        "-- Auto-generated by scripts/preprocess.py — do not edit by hand.",
        "-- Re-creates the product-service catalogue using real Amazon books.",
        "",
        "-- Wipe existing rows in dependency order.",
        "DELETE FROM app_review;",
        "DELETE FROM app_orderitem;",
        "DELETE FROM app_cartitem;",
        "DELETE FROM app_book;",
        "DELETE FROM app_electronics;",
        "DELETE FROM app_fashion;",
        "DELETE FROM app_product;",
        "",
        "-- 500 books (id 1-500) -----------------------------------------",
        "INSERT INTO app_product (id, name, price, stock, category_id, description, product_type, created_at) VALUES",
    ]
    book_values = []
    for _, r in subset.iterrows():
        name = _esc(str(r["name"])[:255])
        desc = _esc(str(r["description"])[:1000]) if pd.notna(r["description"]) else ""
        book_values.append(
            f"({int(r['product_id'])}, '{name}', {int(r['price'])}.00, {int(r['stock'])}, "
            f"{int(r['category_id'])}, '{desc}', 'book', NOW())"
        )
    lines.append(",\n".join(book_values) + ";\n")

    # app_book detail rows
    lines.append("INSERT INTO app_book (product_id, author, publisher, isbn) VALUES")
    book_detail = []
    for _, r in subset.iterrows():
        authors = str(r["author_raw"]) if pd.notna(r["author_raw"]) else ""
        author_clean = _esc(
            authors.replace("[", "").replace("]", "").replace("'", "").strip()[:255]
            or "Unknown"
        )
        pub = _esc(str(r["publisher_raw"])[:255]) if pd.notna(r["publisher_raw"]) else ""
        book_detail.append(
            f"({int(r['product_id'])}, '{author_clean}', '{pub}', '')"
        )
    lines.append(",\n".join(book_detail) + ";\n")

    # Electronics + fashion (shifted to 501-512). Copy values from old seed.
    lines.extend([
        "-- 6 electronics (id 501-506) ---------------------------------",
        "INSERT INTO app_product (id, name, price, stock, category_id, description, product_type, created_at) VALUES",
        "(501, 'iPhone 15 Pro',          25000000.00, 15, 6, 'Smartphone Apple cao cap', 'electronics', NOW()),",
        "(502, 'Samsung Galaxy S24',     22000000.00, 20, 6, 'Smartphone Android flagship', 'electronics', NOW()),",
        "(503, 'iPad Air',               18000000.00, 25, 6, 'Tablet Apple 11 inch', 'electronics', NOW()),",
        "(504, 'MacBook Air M3',         32000000.00, 10, 7, 'Laptop Apple Silicon', 'electronics', NOW()),",
        "(505, 'Dell XPS 13',            28000000.00, 12, 7, 'Laptop van phong cao cap', 'electronics', NOW()),",
        "(506, 'Asus ROG Strix',         35000000.00,  8, 7, 'Laptop gaming hieu nang cao', 'electronics', NOW());",
        "",
        "INSERT INTO app_electronics (product_id, brand, warranty_months) VALUES",
        "(501, 'Apple',   12), (502, 'Samsung', 24), (503, 'Apple',   12),",
        "(504, 'Apple',   24), (505, 'Dell',    24), (506, 'Asus',    24);",
        "",
        "-- 6 fashion (id 507-512) -------------------------------------",
        "INSERT INTO app_product (id, name, price, stock, category_id, description, product_type, created_at) VALUES",
        "(507, 'Ao Polo Nam',             450000.00, 50, 8, 'Ao polo nam cotton cao cap',   'fashion', NOW()),",
        "(508, 'Quan Jeans Nam',          650000.00, 40, 8, 'Quan jeans nam slim fit',      'fashion', NOW()),",
        "(509, 'Giay Sneaker Nam',       1200000.00, 30, 8, 'Giay the thao nam',            'fashion', NOW()),",
        "(510, 'Vay Maxi Nu',             750000.00, 35, 9, 'Vay maxi nu thoi trang',       'fashion', NOW()),",
        "(511, 'Ao So Mi Nu',             550000.00, 45, 9, 'Ao so mi nu cong so',          'fashion', NOW()),",
        "(512, 'Tui Xach Nu',            1800000.00, 25, 9, 'Tui xach nu da that',          'fashion', NOW());",
        "",
        "INSERT INTO app_fashion (product_id, size, color, material) VALUES",
        "(507, 'L', 'Den',   'Cotton'),",
        "(508, '32', 'Xanh', 'Denim'),",
        "(509, '42', 'Trang','Vai'),",
        "(510, 'M', 'Do',    'Lua'),",
        "(511, 'M', 'Trang', 'Cotton'),",
        "(512, '-', 'Den',   'Da that');",
        "",
        "-- Reset Postgres sequences so future INSERTs continue from 513.",
        "SELECT setval('app_product_id_seq', 512, true);",
        "",
        "-- Demo cart/order/review rows for first 5 books (id 1-5).",
        "INSERT INTO app_cartitem (id, cart_id, book_id, quantity) VALUES",
        "(1, 1, 1, 2), (2, 1, 2, 1), (3, 2, 3, 1);",
        "SELECT setval('app_cartitem_id_seq', 3, true);",
        "",
        "INSERT INTO app_orderitem (id, order_id, book_id, quantity, price) VALUES",
        "(1, 1, 1, 1, 85000.00), (2, 1, 2, 2, 65000.00), (3, 2, 3, 1, 55000.00);",
        "SELECT setval('app_orderitem_id_seq', 3, true);",
        "",
        "INSERT INTO app_review (id, book_id, customer_id, rating, comment, created_at) VALUES",
        "(1, 1, 1, 5, 'Sach hay, dang doc.',          NOW()),",
        "(2, 2, 1, 4, 'Noi dung phong phu.',          NOW()),",
        "(3, 3, 2, 5, 'Mot tac pham xuat sac.',       NOW());",
        "SELECT setval('app_review_id_seq', 3, true);",
        "",
    ])

    OUT_SEED_SQL.write_text("\n".join(lines), encoding="utf-8")
    print(f"[seed-sql] wrote {OUT_SEED_SQL}")


def main() -> int:
    if not (RAW_DIR / "Books_rating.csv").exists():
        print(f"ERROR: raw data not found in {RAW_DIR}. Run: make download-datasets",
              file=sys.stderr)
        return 1

    books, ratings = load_books_and_ratings()
    subset = select_subset(books, ratings)
    emit_corpus(subset)
    emit_seed_sql(subset)

    # Persist the picked subset for downstream steps (Task 5, 6).
    subset.to_pickle(AI_DATA_DIR / "_subset.pkl")
    ratings.to_pickle(AI_DATA_DIR / "_ratings.pkl")  # filtered later
    print("[done] book subset + corpus + seed SQL written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run preprocess for the book-subset path**

```powershell
python -m scripts.preprocess
```

Expected output (numbers will vary):
```
[load] books_data: ~210000 unique titles
[load] ratings: ~3,000,000 rows
[subset] ~XXXX books pass min-ratings filter (50)
[subset] picked per category:
category_id
1    100
2    100
3    100
4    100
5    100
[corpus] wrote 500 entries to .../product_corpus.jsonl
[seed-sql] wrote .../seed_data_books.sql
[done] book subset + corpus + seed SQL written.
```

If any category has fewer than 100 books, lower `MIN_RATINGS_PER_BOOK` (try 20) and rerun.

- [ ] **Step 3: Sanity-check the corpus**

```powershell
python -c "import json; lines=[json.loads(l) for l in open('ai-service/data/product_corpus.jsonl', encoding='utf-8')]; print('count:', len(lines)); print('cats:', sorted(set(l['category_id'] for l in lines))); print('first:', lines[0])"
```

Expected:
```
count: 500
cats: [1, 2, 3, 4, 5]
first: {'product_id': 1, 'name': '...', 'type': 'book', 'category_id': 1, ...}
```

- [ ] **Step 4: Sanity-check the SQL file**

```powershell
Get-Content ai-service/data/seed_data_books.sql -TotalCount 25
```

Expected: header comments + DELETE statements + INSERT INTO app_product with values.

```powershell
(Get-Content ai-service/data/seed_data_books.sql | Measure-Object -Line).Lines
```

Expected: 1000+ lines.

- [ ] **Step 5: Commit (artifacts + script)**

```powershell
git add scripts/preprocess.py ai-service/data/product_corpus.jsonl ai-service/data/seed_data_books.sql
git status   # _subset.pkl / _ratings.pkl should appear untracked (we won't commit them — they're intermediate)
git commit -m "feat(scripts): preprocess subset selection + emit catalogue artifacts"
```

---

## Task 5: Preprocess — user behaviour + user_id_map

**Files:**
- Modify: `scripts/preprocess.py` (extend with `emit_behavior`)

- [ ] **Step 1: Add behavior export to preprocess.py**

In `scripts/preprocess.py`, add these constants near the top (after the existing OUT_* constants):

```python
OUT_BEHAVIOR = AI_DATA_DIR / "user_behavior.csv"
OUT_USER_MAP = AI_DATA_DIR / "user_id_map.json"

MIN_EVENTS_PER_USER = 5
```

Add this function just above `def main()`:

```python
def emit_behavior(subset: pd.DataFrame, ratings: pd.DataFrame) -> None:
    """Filter ratings to subset titles, map Amazon User_id -> int,
    derive synthetic action funnel from review/score, write CSV + JSON map.

    Action funnel rule (the LSTM only really cares about ordered product
    sequence, but downstream graph_triples wants action types):
      review/score >= 4 : 'purchase'
      review/score == 3 : 'add_to_cart'
      review/score <  3 : 'view'
    """
    title_to_pid = dict(zip(subset["name"], subset["product_id"]))
    r = ratings[ratings["Title"].isin(title_to_pid)].copy()
    r["product_id"] = r["Title"].map(title_to_pid).astype(int)
    print(f"[behavior] ratings on subset: {len(r):,}")

    # Drop users with too few events.
    user_counts = r.groupby("User_id").size()
    keep_users = user_counts[user_counts >= MIN_EVENTS_PER_USER].index
    r = r[r["User_id"].isin(keep_users)]
    print(f"[behavior] users with >= {MIN_EVENTS_PER_USER} events: {len(keep_users):,}")

    # Stable int mapping (sorted for reproducibility).
    sorted_uids = sorted(r["User_id"].unique())
    user_map = {uid: i + 1 for i, uid in enumerate(sorted_uids)}
    OUT_USER_MAP.write_text(json.dumps(user_map, indent=2), encoding="utf-8")
    print(f"[behavior] user_id_map: {len(user_map):,} entries -> {OUT_USER_MAP}")

    r["user_id_int"] = r["User_id"].map(user_map).astype(int)
    r["timestamp"] = pd.to_datetime(r["review/time"], unit="s", errors="coerce")
    r = r.dropna(subset=["timestamp"])

    def _action(s: float) -> str:
        if s >= 4: return "purchase"
        if s >= 3: return "add_to_cart"
        return "view"

    r["action"] = r["review/score"].astype(float).map(_action)

    out = r[["user_id_int", "product_id", "action", "timestamp"]]\
        .rename(columns={"user_id_int": "user_id"})\
        .sort_values(["user_id", "timestamp"])

    out.to_csv(OUT_BEHAVIOR, index=False, date_format="%Y-%m-%dT%H:%M:%S")
    print(f"[behavior] wrote {len(out):,} rows to {OUT_BEHAVIOR}")
```

Update `main()` — add this line after `emit_seed_sql(subset)`:

```python
    emit_behavior(subset, ratings)
```

- [ ] **Step 2: Run preprocess again**

```powershell
python -m scripts.preprocess
```

Expected new output lines:
```
[behavior] ratings on subset: ~500,000
[behavior] users with >= 5 events: ~10,000
[behavior] user_id_map: ~10,000 entries -> .../user_id_map.json
[behavior] wrote ~500,000 rows to .../user_behavior.csv
```

- [ ] **Step 3: Sanity-check the behaviour file**

```powershell
python -c "import csv; rows=list(csv.DictReader(open('ai-service/data/user_behavior.csv', encoding='utf-8'))); print('rows:', len(rows)); print('users:', len(set(r['user_id'] for r in rows))); print('products:', len(set(r['product_id'] for r in rows))); print('actions:', set(r['action'] for r in rows)); print('first:', rows[0])"
```

Expected:
```
rows: ~500000  (varies)
users: ~10000  (varies)
products: 500
actions: {'view', 'add_to_cart', 'purchase'}
first: {'user_id': '1', 'product_id': '...', 'action': '...', 'timestamp': '20...'}
```

- [ ] **Step 4: Commit**

```powershell
git add scripts/preprocess.py ai-service/data/user_behavior.csv ai-service/data/user_id_map.json
git commit -m "feat(scripts): emit user_behavior.csv + user_id_map from real ratings"
```

---

## Task 6: Preprocess — graph triples

**Files:**
- Modify: `scripts/preprocess.py` (extend with `emit_graph`)

- [ ] **Step 1: Add graph triples export**

In `scripts/preprocess.py`, add constant near other OUT_* lines:

```python
OUT_GRAPH = AI_DATA_DIR / "graph_triples.csv"
```

Add function above `def main()`:

```python
def emit_graph(subset: pd.DataFrame) -> None:
    """Derive Neo4j edges from user_behavior.csv (already written).

    Edges:
      IN_CATEGORY : Product -> Category (1 per product)
      BOUGHT      : User -> Product (count = #purchase events)
      VIEWED      : User -> Product (count = #view events)
      SIMILAR     : Product -> Product (co-purchase + same-category)
    """
    from collections import defaultdict
    from scripts._io import write_csv

    triples: list[tuple] = []

    # 1) IN_CATEGORY
    for _, r in subset.iterrows():
        triples.append((
            "Product", int(r["product_id"]), "IN_CATEGORY",
            "Category", int(r["category_id"]), 1.0,
        ))

    # 2) BOUGHT + VIEWED from behavior file
    import csv
    bought = defaultdict(int)
    viewed = defaultdict(int)
    user_purchases = defaultdict(set)
    with OUT_BEHAVIOR.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            uid, pid, act = int(row["user_id"]), int(row["product_id"]), row["action"]
            if act == "purchase":
                bought[(uid, pid)] += 1
                user_purchases[uid].add(pid)
            elif act in ("view", "add_to_cart"):
                viewed[(uid, pid)] += 1

    for (uid, pid), cnt in bought.items():
        triples.append(("User", uid, "BOUGHT", "Product", pid, float(cnt)))
    for (uid, pid), cnt in viewed.items():
        triples.append(("User", uid, "VIEWED", "Product", pid, float(cnt)))

    # 3) SIMILAR (co-purchase). Cap to keep file size sane.
    co = defaultdict(float)
    for pids in user_purchases.values():
        for a in pids:
            for b in pids:
                if a < b:
                    co[(a, b)] += 1.0
    # Only keep co-purchase pairs with weight >= 2 (noise floor).
    for (a, b), w in co.items():
        if w >= 2:
            triples.append(("Product", a, "SIMILAR", "Product", b, w))

    # 4) SIMILAR (same category) — lighter weight, for cold-start.
    by_cat = defaultdict(list)
    for _, r in subset.iterrows():
        by_cat[int(r["category_id"])].append(int(r["product_id"]))
    seen_pairs = {(a, b) for a, b in co}
    for pids in by_cat.values():
        for a in pids:
            for b in pids:
                if a < b and (a, b) not in seen_pairs:
                    triples.append(("Product", a, "SIMILAR", "Product", b, 0.3))

    n = write_csv(
        OUT_GRAPH,
        ["source_type", "source_id", "edge_type", "target_type", "target_id", "weight"],
        triples,
    )
    print(f"[graph] wrote {n:,} triples to {OUT_GRAPH}")
```

Update `main()` — add this line after `emit_behavior(subset, ratings)`:

```python
    emit_graph(subset)
```

- [ ] **Step 2: Run preprocess**

```powershell
python -m scripts.preprocess
```

Expected additional lines:
```
[graph] wrote ~XXX,XXX triples to .../graph_triples.csv
```

- [ ] **Step 3: Sanity-check**

```powershell
python -c "import csv; rows=list(csv.DictReader(open('ai-service/data/graph_triples.csv', encoding='utf-8'))); print('total:', len(rows)); print('edge types:', sorted(set(r['edge_type'] for r in rows)))"
```

Expected:
```
total: ~XXX,XXX
edge types: ['BOUGHT', 'IN_CATEGORY', 'SIMILAR', 'VIEWED']
```

- [ ] **Step 4: Verify file size is sane**

```powershell
(Get-Item ai-service/data/graph_triples.csv).Length / 1MB
```

Expected: under 20 MB. If much larger, raise the co-purchase noise floor from 2 to 3.

- [ ] **Step 5: Commit**

```powershell
git add scripts/preprocess.py ai-service/data/graph_triples.csv
git commit -m "feat(scripts): emit graph_triples.csv from behaviour log"
```

---

## Task 7: ai-service config + bootstrap — load weights, no startup training

**Files:**
- Modify: `ai-service/app/config.py` (line 27)
- Modify: `ai-service/app/bootstrap.py`
- Modify: `ai-service/app/lstm/inference.py` (verify load path)

- [ ] **Step 1: Flip the LSTM_TRAIN_AT_STARTUP default**

Edit `ai-service/app/config.py:27`. Change:

```python
LSTM_TRAIN_AT_STARTUP = os.environ.get("LSTM_TRAIN_AT_STARTUP", "true").lower() == "true"
```

to:

```python
LSTM_TRAIN_AT_STARTUP = os.environ.get("LSTM_TRAIN_AT_STARTUP", "false").lower() == "true"
```

- [ ] **Step 2: Inspect bootstrap.py and main.py to find the startup hook**

```powershell
Get-Content ai-service/app/bootstrap.py
Get-Content ai-service/main.py
```

Identify where LSTM is currently trained at startup (it's in `main.py` — the FastAPI lifespan/`@app.on_event("startup")` block).

- [ ] **Step 3: Read main.py and update the startup logic**

Open `ai-service/main.py`. Find the section that calls `lstm.train.train(...)`. Wrap it so that:
- if `config.LSTM_TRAIN_AT_STARTUP` is True → train as before
- if False → call `lstm_inference.load_weights()` instead, log if missing

Example expected change pattern (adapt to actual structure):

```python
# OLD
from app.lstm import train as lstm_train
...
products = fetch_products()
orders = fetch_orders()
lstm_train.train(products, orders)

# NEW
from app.lstm import train as lstm_train
from app.lstm.inference import lstm_inference
...
products = fetch_products()
if config.LSTM_TRAIN_AT_STARTUP:
    orders = fetch_orders()
    lstm_train.train(products, orders)
else:
    if not lstm_inference.load_weights():
        log.warning("LSTM weights missing at %s — hybrid will skip LSTM component",
                    config.LSTM_WEIGHTS_PATH)
```

- [ ] **Step 4: Verify lstm_inference.load_weights() exists**

```powershell
Get-Content ai-service/app/lstm/inference.py
```

Confirm there's a `load_weights()` method on the singleton. If it doesn't return a bool, modify it to return `True` on success and `False` if the weight file is missing — and log gracefully without raising.

If the method doesn't exist at all, add it:

```python
def load_weights(self) -> bool:
    """Load weights from LSTM_WEIGHTS_PATH. Returns False if missing
    so callers can degrade gracefully."""
    import torch
    if not config.LSTM_WEIGHTS_PATH.exists():
        log.warning("LSTM weights not found at %s", config.LSTM_WEIGHTS_PATH)
        return False
    checkpoint = torch.load(config.LSTM_WEIGHTS_PATH, map_location="cpu")
    self.model = LSTMModel(
        num_products=checkpoint["num_products"],
        hidden_dim=checkpoint["hidden_dim"],
    )
    self.model.load_state_dict(checkpoint["state_dict"])
    self.model.eval()
    self.prod_id_to_idx = checkpoint["prod_id_to_idx"]
    self.idx_to_prod_id = checkpoint["idx_to_prod_id"]
    self.seq_length = checkpoint["seq_length"]
    log.info("Loaded LSTM weights from %s (vocab=%d)",
             config.LSTM_WEIGHTS_PATH, checkpoint["num_products"])
    return True
```

- [ ] **Step 5: Run train-ai locally so the weights file exists**

```powershell
cd ai-service
pip install -r requirements.txt
python -m app.lstm.train
cd ..
```

Expected output: ~30 epoch lines showing decreasing loss, ending with `Saved LSTM weights to .../lstm_weights.pt`.

Verify:

```powershell
Get-Item ai-service/data/lstm_weights.pt | Select-Object Name, Length
```

Expected size: 5–50 MB depending on vocab.

- [ ] **Step 6: Commit weights + code changes**

```powershell
git add ai-service/app/config.py ai-service/app/bootstrap.py ai-service/main.py ai-service/app/lstm/inference.py ai-service/data/lstm_weights.pt
git commit -m "feat(ai-service): load LSTM weights at startup instead of training"
```

---

## Task 8: Dockerfile — ensure weights are baked into the image

**Files:**
- Modify: `ai-service/Dockerfile`

- [ ] **Step 1: Inspect current Dockerfile**

```powershell
Get-Content ai-service/Dockerfile
```

Look for the `COPY` statements. If there's already a `COPY . .` covering the entire ai-service dir, the weights file is already included — only need to verify. If only specific subdirs are copied, add a line for the data dir.

- [ ] **Step 2: Add (or verify) the data COPY**

Edit `ai-service/Dockerfile`. Ensure these lines exist (add near the existing COPY block):

```dockerfile
COPY data/ /app/data/
```

Or if the project uses a different working dir, copy to the matching path. The goal: `/app/data/lstm_weights.pt` (or wherever `config.LSTM_WEIGHTS_PATH` resolves to inside the container) must exist after `docker build`.

- [ ] **Step 3: Rebuild and verify**

```powershell
docker-compose build ai-service
docker-compose run --rm --no-deps ai-service ls -la /app/data/
```

Expected: output lists `lstm_weights.pt`, `product_corpus.jsonl`, `user_behavior.csv`, `graph_triples.csv`, `user_id_map.json`.

- [ ] **Step 4: Commit**

```powershell
git add ai-service/Dockerfile
git commit -m "build(ai-service): bake training artefacts into image"
```

---

## Task 9: seed_all.sh + seed_data.sql split

**Files:**
- Modify: `data/seed_all.sh`
- Modify: `data/seed_data.sql` (remove product-service section)

- [ ] **Step 1: Inspect seed_all.sh and seed_data.sql**

```powershell
Get-Content data/seed_all.sh
Get-Content data/seed_data.sql -TotalCount 200
```

Find the section in `seed_data.sql` marked `-- ========== product-service ==========`. Note line numbers for the product/book/electronics/fashion/cartitem/orderitem/review blocks.

- [ ] **Step 2: Strip the obsolete product-service section from seed_data.sql**

Edit `data/seed_data.sql`. Delete every line from `-- ========== product-service ==========` through the end of the `INSERT INTO app_review ... ON CONFLICT ... DO NOTHING;` block (everything that touches product/book/electronics/fashion/cart/order/review tables — all of this is now in `seed_data_books.sql`).

Keep:
- Top `-- ========== catalog-service ==========` block (categories) — id 1–9
- Any sections for other services (auth/customer/staff/manager are in seed_data_mysql.sql, not here)
- comment-rate / payment / shipping sections if they exist

In place of the deleted block, add a comment pointer:

```sql
-- ========== product-service ==========
-- See ai-service/data/seed_data_books.sql — generated by scripts/preprocess.py
```

- [ ] **Step 3: Wire seed_data_books.sql into seed_all.sh**

Edit `data/seed_all.sh`. Find the line that runs `seed_data.sql` against the `product_db` (something like `PGPASSWORD=... psql ... -f /seed/seed_data.sql`). After that command, add:

```bash
echo "[seed] Loading book catalogue from seed_data_books.sql ..."
PGPASSWORD=postgres psql -h localhost -p 5433 -U postgres -d product_db \
    -f ai-service/data/seed_data_books.sql
```

Adjust host/port/user/password to match whatever pattern the existing seed commands use (they may use a different host like `postgres` when run inside Docker network).

- [ ] **Step 4: Reseed and verify**

```powershell
docker-compose down -v
docker-compose up -d postgres mysql
# wait ~10s for DBs to initialise
docker-compose up -d --build product-service catalog-service cart-service order-service pay-service ship-service comment-rate-service advisory-chat-service
# wait ~30s for migrations
bash data/seed_all.sh
```

Expected: seed script completes without SQL errors. Should log `[seed] Loading book catalogue from seed_data_books.sql ...` near the end.

Verify product count:

```powershell
docker-compose exec postgres psql -U postgres -d product_db -c "SELECT product_type, count(*) FROM app_product GROUP BY product_type;"
```

Expected:
```
 product_type | count
--------------+-------
 book         |   500
 electronics  |     6
 fashion      |     6
```

- [ ] **Step 5: Commit**

```powershell
git add data/seed_all.sh data/seed_data.sql
git commit -m "feat(seed): swap product-service section to use seed_data_books.sql"
```

---

## Task 10: End-to-end smoke test

No files modified — pure verification.

- [ ] **Step 1: Bring up the full stack**

```powershell
docker-compose down
docker-compose up -d --build
```

Wait ~60s for everything to settle.

- [ ] **Step 2: Verify ai-service started without training**

```powershell
docker-compose logs ai-service | Select-String -Pattern "LSTM|weights|FAISS|Graph"
```

Expected: lines like `Loaded LSTM weights from .../lstm_weights.pt (vocab=501)`, NO lines like `LSTM epoch 01/30`.

- [ ] **Step 3: Hit the /recommend endpoint**

```powershell
curl http://localhost:8014/recommend?user_id=1
```

Expected: JSON array of 10 items, each with `product_id` in `[1, 500]`, plus `name`, `score`, and `components` sub-object.

- [ ] **Step 4: Hit the catalogue through the gateway**

```powershell
curl http://localhost:8080/api/product/products/ | python -c "import json,sys; d=json.load(sys.stdin); print('count:', len(d)); print('first:', d[0]['name'])"
```

Expected: count is 512 (500 books + 6 electronics + 6 fashion).

- [ ] **Step 5: Open UI and visually verify**

In a browser, navigate to <http://localhost:8000> and confirm:
- Catalogue page renders 500+ books with English titles
- Clicking a book shows its description
- Login as `nguyenvana / customer123`, add a book to cart, place an order → should succeed

- [ ] **Step 6: If anything fails**

Pause and debug. Do NOT commit. Common issues:
- ai-service can't find `lstm_weights.pt` → check Dockerfile COPY path
- product-service errors on duplicate IDs → seed didn't run cleanly, run `docker-compose down -v` and retry
- /recommend returns empty → check Neo4j seed completed (`docker-compose logs ai-service | Select-String Neo4j`)

- [ ] **Step 7: Tag the working state**

```powershell
git tag -a real-datasets-smoke-ok -m "End-to-end smoke test passed with real Amazon book data"
```

---

## Task 11: Advisory chat KB refresh

No files modified — operational step.

- [ ] **Step 1: Reload the knowledge base inside the running container**

```powershell
docker-compose exec advisory-chat-service python manage.py load_kb --clear
```

Expected output ends with `KB loading complete. Total documents: ~520+` (500 books + ~20 from markdown).

- [ ] **Step 2: Sanity-check via the chat endpoint**

```powershell
curl -X POST http://localhost:8013/api/chat/ -H "Content-Type: application/json" -d '{"customer_id": 1, "message": "Goi y cho toi sach lap trinh"}'
```

Expected: JSON response with a `reply` field containing recommendations referencing Amazon book titles in the "Khoa hoc & Cong nghe" category. If no `OPENAI_API_KEY` is set, the response will be a templated fallback — still valid.

---

## Task 12: Cleanup — delete obsolete synthetic generator + docs

**Files:**
- Delete: `ai-service/data/generate_datasets.py`
- Modify: `ai-service/README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Delete the synthetic generator**

```powershell
Remove-Item ai-service/data/generate_datasets.py
```

- [ ] **Step 2: Update ai-service/README.md**

Open `ai-service/README.md`. Replace the section that describes the synthetic data pipeline with:

```markdown
## Training data pipeline

The AI service trains on **Amazon Books Reviews** (Kaggle dataset
`mohamedbakhet/amazon-books-reviews`). The pipeline is offline; the
container only loads pretrained weights at startup.

### One-time setup (developer machine)

```bash
# 1. Install dev dependencies
pip install -r requirements-dev.txt

# 2. Set Kaggle credentials (https://www.kaggle.com/settings/account)
export KAGGLE_USERNAME=...
export KAGGLE_KEY=...

# 3. Run the full pipeline
make data-pipeline
```

This produces:
- `ai-service/data/product_corpus.jsonl` — 500 books, source-of-truth catalogue
- `ai-service/data/user_behavior.csv` — sequential events for LSTM
- `ai-service/data/graph_triples.csv` — Neo4j seed
- `ai-service/data/lstm_weights.pt` — trained weights (committed to git)
- `ai-service/data/seed_data_books.sql` — drop-in SQL for product-service

### Runtime behaviour

- `LSTM_TRAIN_AT_STARTUP=false` (default) — load `lstm_weights.pt`
- `SEED_GRAPH_AT_STARTUP=true` (default) — seed Neo4j from `graph_triples.csv`
- `BUILD_FAISS_AT_STARTUP=true` (default) — embed `product_corpus.jsonl`

To retrain (e.g. after refreshing the dataset):

```bash
make train-ai
git add ai-service/data/lstm_weights.pt
git commit -m "chore: retrain LSTM"
```

### Known trade-offs

- Book content is English (from Amazon); UI labels stay Vietnamese.
- Mapping Amazon `categories` -> 5 internal categories is heuristic; ~20%
  of books fall into the "Van hoc Viet Nam" fallback bucket.
```

- [ ] **Step 3: Update CLAUDE.md AI Service section**

Open `CLAUDE.md`. Find the section starting `### AI Service (Hybrid Recommender — thesis Ch.3 spec)`. Update the second paragraph to describe the real-data pipeline:

Replace:

> Trained at startup on synthetic sequences derived from real seed orders + product categories.

With:

> Trained offline (`make train-ai`) on the Amazon Books Reviews dataset
> (Kaggle), 500-book subset. Weights `ai-service/data/lstm_weights.pt`
> are committed and loaded at startup — the container does NOT train.

Also add a new line after the bullets:

> **Training data:** see `ai-service/README.md` "Training data pipeline" for
> the offline pipeline (download → preprocess → train).

- [ ] **Step 4: Commit**

```powershell
git rm ai-service/data/generate_datasets.py
git add ai-service/README.md CLAUDE.md
git commit -m "docs: remove synthetic generator, document real-data pipeline"
```

---

## Task 13: Clean up intermediate pickle files

**Files:**
- Modify: `scripts/preprocess.py` (delete intermediate `_subset.pkl`, `_ratings.pkl`)
- Modify: `.gitignore`

- [ ] **Step 1: Delete intermediates at the end of preprocess.py main()**

In `scripts/preprocess.py`, modify `main()` to clean up after itself. Replace the last two lines before `return 0`:

```python
    subset.to_pickle(AI_DATA_DIR / "_subset.pkl")
    ratings.to_pickle(AI_DATA_DIR / "_ratings.pkl")
```

with:

```python
    # No pickle handoff: each emit_* function takes its inputs as args.
    # Keeping the script self-contained means a single run produces all artefacts.
```

Then audit the function calls in `main()` — they should already pass `subset` / `ratings` directly without needing the pickle files. If `emit_graph` re-reads behavior.csv, that's fine; if it expects the pickle, fix the call to pass subset directly (it already does in Task 6).

- [ ] **Step 2: Add a guard in .gitignore for the no-longer-written pickles**

Append to `.gitignore`:

```
# Removed intermediates — guard against accidental re-introduction
ai-service/data/_*.pkl
```

- [ ] **Step 3: Verify run is still clean**

```powershell
Remove-Item ai-service/data/_subset.pkl, ai-service/data/_ratings.pkl -ErrorAction SilentlyContinue
python -m scripts.preprocess
Get-ChildItem ai-service/data/_*.pkl -ErrorAction SilentlyContinue
```

Expected: preprocess completes, no `_*.pkl` files remain.

- [ ] **Step 4: Commit**

```powershell
git add scripts/preprocess.py .gitignore
git commit -m "chore(scripts): drop unused pickle intermediates"
```

---

## Final verification

After all tasks complete:

- [ ] `make data-pipeline` runs clean on a freshly cloned repo (after `pip install -r requirements-dev.txt` + Kaggle creds)
- [ ] `docker-compose down -v && docker-compose up --build` brings up the full stack without training-related logs in ai-service
- [ ] `curl http://localhost:8014/recommend?user_id=1` returns 10 products with `product_id ∈ [1, 500]`
- [ ] `bash data/seed_all.sh` succeeds and Postgres has 500 books + 6 electronics + 6 fashion
- [ ] Browsing <http://localhost:8000>, a customer can browse, add to cart, and place an order against the new catalogue
- [ ] Advisory chat (port 8013) returns recommendations from the new catalogue
- [ ] Repo size after all commits hasn't grown more than 100 MB (`git count-objects -vH` to check)
