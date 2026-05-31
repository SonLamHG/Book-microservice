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
OUT_BEHAVIOR = AI_DATA_DIR / "user_behavior.csv"
OUT_USER_MAP = AI_DATA_DIR / "user_id_map.json"

MIN_EVENTS_PER_USER = 5


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

    Layout (matches spec):
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


def main() -> int:
    if not (RAW_DIR / "Books_rating.csv").exists():
        print(f"ERROR: raw data not found in {RAW_DIR}. Run: make download-datasets",
              file=sys.stderr)
        return 1

    books, ratings = load_books_and_ratings()
    subset = select_subset(books, ratings)
    emit_corpus(subset)
    emit_seed_sql(subset)
    emit_behavior(subset, ratings)

    # Persist the picked subset for downstream steps (Task 5, 6).
    subset.to_pickle(AI_DATA_DIR / "_subset.pkl")
    ratings.to_pickle(AI_DATA_DIR / "_ratings.pkl")  # filtered later
    print("[done] book subset + corpus + seed SQL written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
