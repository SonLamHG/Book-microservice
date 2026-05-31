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
