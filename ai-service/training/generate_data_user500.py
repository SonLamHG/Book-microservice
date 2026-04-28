import argparse
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


def generate_rows(user_count: int, events_per_user: int, product_min: int, product_max: int):
    actions = ["view", "click", "add_to_cart"]
    now = datetime.now(timezone.utc)

    rows = []
    for user_id in range(1, user_count + 1):
        t = now - timedelta(days=random.randint(15, 120))
        for _ in range(events_per_user):
            t += timedelta(minutes=random.randint(1, 240))
            rows.append(
                {
                    "user_id": user_id,
                    "product_id": random.randint(product_min, product_max),
                    "action": random.choices(actions, weights=[0.6, 0.3, 0.1], k=1)[0],
                    "timestamp": t.isoformat(),
                }
            )

    rows.sort(key=lambda r: r["timestamp"])
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate user behavior dataset for AI training")
    parser.add_argument("--user-count", type=int, default=500)
    parser.add_argument("--events-per-user", type=int, default=8)
    parser.add_argument("--product-min", type=int, default=1)
    parser.add_argument("--product-max", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "data_user500.csv",
    )
    args = parser.parse_args()

    random.seed(args.seed)
    rows = generate_rows(
        user_count=args.user_count,
        events_per_user=args.events_per_user,
        product_min=args.product_min,
        product_max=args.product_max,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["user_id", "product_id", "action", "timestamp"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows")


if __name__ == "__main__":
    main()


