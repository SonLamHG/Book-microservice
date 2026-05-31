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
