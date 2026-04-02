import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from django.conf import settings

CUSTOMER_SERVICE_URL = "http://customer-service:8000"
BOOK_SERVICE_URL = "http://book-service:8000"
CATALOG_SERVICE_URL = "http://catalog-service:8000"
CART_SERVICE_URL = "http://cart-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
COMMENT_RATE_SERVICE_URL = "http://comment-rate-service:8000"

MODEL_VERSION = "behavior-mlp-v1"
MODEL_ARTIFACT_PATH = Path(settings.BASE_DIR) / "data" / "behavior_model.json"
MAX_RECENT_BOOKS = 5
MAX_RECENT_CATEGORIES = 5


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def mean(values):
    return sum(values) / len(values) if values else 0.0


def stdev(values):
    if not values:
        return 1.0
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / len(values)
    return math.sqrt(variance) or 1.0


def parse_dt(value):
    if not value:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def price_band_from_value(value):
    if value <= 0:
        return "medium"
    if value < 160000:
        return "low"
    if value < 300000:
        return "medium"
    return "high"


def dot(left, right):
    return sum(a * b for a, b in zip(left, right))


def relu(values):
    return [value if value > 0 else 0.0 for value in values]


def sigmoid(value):
    if value <= -40:
        return 0.0
    if value >= 40:
        return 1.0
    return 1.0 / (1.0 + math.exp(-value))


class ServiceClient:
    def get_json(self, url, params=None, timeout=5, default=None):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException:
            pass
        return [] if default is None else default


class BehaviorMLPModel:
    def __init__(self, artifact):
        self.artifact = artifact
        self.customer_to_index = artifact["customer_to_index"]
        self.book_to_index = artifact["book_to_index"]
        self.category_to_index = artifact["category_to_index"]
        self.customer_embeddings = artifact["customer_embeddings"]
        self.book_embeddings = artifact["book_embeddings"]
        self.category_embeddings = artifact["category_embeddings"]
        self.w1 = artifact["w1"]
        self.b1 = artifact["b1"]
        self.w2 = artifact["w2"]
        self.b2 = artifact["b2"]
        self.w3 = artifact["w3"]
        self.b3 = artifact["b3"]
        self.feature_means = artifact["feature_means"]
        self.feature_stds = [value or 1.0 for value in artifact["feature_stds"]]
        self.dims = artifact["dims"]

    @classmethod
    def initialize(cls, customer_ids, book_ids, category_ids, feature_size, seed=17):
        rng = random.Random(seed)
        dims = {"customer": 8, "book": 12, "category": 6, "hidden1": 24, "hidden2": 12}
        input_size = dims["customer"] + dims["book"] + dims["book"] + dims["category"] + feature_size
        artifact = {
            "model_version": MODEL_VERSION,
            "trained_at": None,
            "seed": seed,
            "customer_to_index": {str(value): index + 1 for index, value in enumerate(sorted(set(customer_ids)))},
            "book_to_index": {str(value): index + 1 for index, value in enumerate(sorted(set(book_ids)))},
            "category_to_index": {str(value): index + 1 for index, value in enumerate(sorted(set(category_ids)))},
            "customer_embeddings": cls._random_matrix(len(set(customer_ids)) + 1, dims["customer"], rng),
            "book_embeddings": cls._random_matrix(len(set(book_ids)) + 1, dims["book"], rng),
            "category_embeddings": cls._random_matrix(len(set(category_ids)) + 1, dims["category"], rng),
            "w1": cls._random_matrix(dims["hidden1"], input_size, rng),
            "b1": [0.0 for _ in range(dims["hidden1"])],
            "w2": cls._random_matrix(dims["hidden2"], dims["hidden1"], rng),
            "b2": [0.0 for _ in range(dims["hidden2"])],
            "w3": [rng.uniform(-0.1, 0.1) for _ in range(dims["hidden2"])],
            "b3": 0.0,
            "feature_means": [0.0 for _ in range(feature_size)],
            "feature_stds": [1.0 for _ in range(feature_size)],
            "dims": dims,
            "dataset_stats": {"samples": 0, "positives": 0, "negatives": 0},
        }
        return cls(artifact)

    @staticmethod
    def _random_matrix(rows, cols, rng):
        return [[rng.uniform(-0.1, 0.1) for _ in range(cols)] for _ in range(rows)]

    def _lookup(self, mapping, value):
        return mapping.get(str(value), 0)

    def _avg_embedding(self, matrix, indices, size):
        rows = [matrix[index] for index in indices if index > 0]
        if not rows:
            return [0.0 for _ in range(size)]
        return [sum(values) / len(rows) for values in zip(*rows)]

    def _normalize(self, features):
        return [
            (value - self.feature_means[index]) / (self.feature_stds[index] or 1.0)
            for index, value in enumerate(features)
        ]

    def forward(self, sample):
        customer_index = self._lookup(self.customer_to_index, sample["customer_id"])
        book_index = self._lookup(self.book_to_index, sample["candidate_book_id"])
        recent_book_indices = [self._lookup(self.book_to_index, value) for value in sample["recent_book_ids"][:MAX_RECENT_BOOKS]]
        recent_category_indices = [self._lookup(self.category_to_index, value) for value in sample["recent_category_ids"][:MAX_RECENT_CATEGORIES]]

        x = (
            self.customer_embeddings[customer_index]
            + self.book_embeddings[book_index]
            + self._avg_embedding(self.book_embeddings, recent_book_indices, self.dims["book"])
            + self._avg_embedding(self.category_embeddings, recent_category_indices, self.dims["category"])
            + self._normalize(sample["numerical_features"])
        )
        z1 = [dot(row, x) + bias for row, bias in zip(self.w1, self.b1)]
        a1 = relu(z1)
        z2 = [dot(row, a1) + bias for row, bias in zip(self.w2, self.b2)]
        a2 = relu(z2)
        logit = dot(self.w3, a2) + self.b3
        score = sigmoid(logit)
        return score, {
            "customer_index": customer_index,
            "book_index": book_index,
            "recent_book_indices": [index for index in recent_book_indices if index > 0],
            "recent_category_indices": [index for index in recent_category_indices if index > 0],
            "x": x,
            "z1": z1,
            "a1": a1,
            "z2": z2,
            "a2": a2,
        }

    def train(self, samples, epochs=25, learning_rate=0.02):
        if not samples:
            return
        feature_size = len(samples[0]["numerical_features"])
        columns = [[sample["numerical_features"][index] for sample in samples] for index in range(feature_size)]
        self.feature_means = [mean(column) for column in columns]
        self.feature_stds = [stdev(column) for column in columns]
        self.artifact["feature_means"] = self.feature_means
        self.artifact["feature_stds"] = self.feature_stds

        rng = random.Random(self.artifact.get("seed", 17))
        for _ in range(epochs):
            rng.shuffle(samples)
            for sample in samples:
                label = sample["label"]
                score, cache = self.forward(sample)
                delta3 = score - label

                old_w3 = list(self.w3)
                old_w2 = [list(row) for row in self.w2]
                old_w1 = [list(row) for row in self.w1]

                for index, value in enumerate(cache["a2"]):
                    self.w3[index] -= learning_rate * delta3 * value
                self.b3 -= learning_rate * delta3

                da2 = [old_w3[index] * delta3 for index in range(len(old_w3))]
                dz2 = [value if cache["z2"][index] > 0 else 0.0 for index, value in enumerate(da2)]
                for row_index, row in enumerate(self.w2):
                    for col_index in range(len(row)):
                        row[col_index] -= learning_rate * dz2[row_index] * cache["a1"][col_index]
                    self.b2[row_index] -= learning_rate * dz2[row_index]

                da1 = [
                    sum(old_w2[row_index][col_index] * dz2[row_index] for row_index in range(len(old_w2)))
                    for col_index in range(len(cache["a1"]))
                ]
                dz1 = [value if cache["z1"][index] > 0 else 0.0 for index, value in enumerate(da1)]
                for row_index, row in enumerate(self.w1):
                    for col_index in range(len(row)):
                        row[col_index] -= learning_rate * dz1[row_index] * cache["x"][col_index]
                    self.b1[row_index] -= learning_rate * dz1[row_index]

                dx = [
                    sum(old_w1[row_index][col_index] * dz1[row_index] for row_index in range(len(old_w1)))
                    for col_index in range(len(cache["x"]))
                ]
                cursor = 0
                cust_grad = dx[cursor:cursor + self.dims["customer"]]
                cursor += self.dims["customer"]
                book_grad = dx[cursor:cursor + self.dims["book"]]
                cursor += self.dims["book"]
                recent_book_grad = dx[cursor:cursor + self.dims["book"]]
                cursor += self.dims["book"]
                recent_category_grad = dx[cursor:cursor + self.dims["category"]]

                if cache["customer_index"] > 0:
                    for index, gradient in enumerate(cust_grad):
                        self.customer_embeddings[cache["customer_index"]][index] -= learning_rate * gradient
                if cache["book_index"] > 0:
                    for index, gradient in enumerate(book_grad):
                        self.book_embeddings[cache["book_index"]][index] -= learning_rate * gradient
                if cache["recent_book_indices"]:
                    share = 1.0 / len(cache["recent_book_indices"])
                    for vector_index in cache["recent_book_indices"]:
                        for index, gradient in enumerate(recent_book_grad):
                            self.book_embeddings[vector_index][index] -= learning_rate * gradient * share
                if cache["recent_category_indices"]:
                    share = 1.0 / len(cache["recent_category_indices"])
                    for vector_index in cache["recent_category_indices"]:
                        for index, gradient in enumerate(recent_category_grad):
                            self.category_embeddings[vector_index][index] -= learning_rate * gradient * share

        self.artifact["trained_at"] = datetime.now(timezone.utc).isoformat()

    def predict(self, sample):
        score, _ = self.forward(sample)
        return score


class BehaviorEngine:
    def __init__(self):
        self.client = ServiceClient()

    def _load_model(self):
        if not MODEL_ARTIFACT_PATH.exists():
            return None
        try:
            with MODEL_ARTIFACT_PATH.open("r", encoding="utf-8") as handle:
                return BehaviorMLPModel(json.load(handle))
        except (OSError, json.JSONDecodeError, KeyError):
            return None

    def _save_model(self, model):
        MODEL_ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with MODEL_ARTIFACT_PATH.open("w", encoding="utf-8") as handle:
            json.dump(model.artifact, handle, indent=2)

    def fetch_reference_data(self):
        books = self.client.get_json(f"{BOOK_SERVICE_URL}/books/")
        categories = self.client.get_json(f"{CATALOG_SERVICE_URL}/categories/")
        reviews = self.client.get_json(f"{COMMENT_RATE_SERVICE_URL}/reviews/")
        customers = self.client.get_json(f"{CUSTOMER_SERVICE_URL}/customers/")
        orders = self.client.get_json(f"{ORDER_SERVICE_URL}/orders/")

        books_by_id = {book["id"]: book for book in books if isinstance(book, dict)}
        categories_by_id = {category["id"]: category for category in categories if isinstance(category, dict)}
        reviews_by_book = defaultdict(list)
        reviews_by_customer = defaultdict(list)
        for review in reviews:
            reviews_by_book[review.get("book_id")].append(review)
            reviews_by_customer[review.get("customer_id")].append(review)
        orders_by_customer = defaultdict(list)
        for order in orders:
            orders_by_customer[order.get("customer_id")].append(order)
        for customer_orders in orders_by_customer.values():
            customer_orders.sort(key=lambda order: parse_dt(order.get("created_at")), reverse=True)

        return {
            "books": books,
            "books_by_id": books_by_id,
            "categories": categories,
            "categories_by_id": categories_by_id,
            "reviews_by_book": reviews_by_book,
            "reviews_by_customer": reviews_by_customer,
            "customers": customers,
            "orders_by_customer": orders_by_customer,
        }

    def _fetch_cart_items(self, customer_id):
        data = self.client.get_json(f"{CART_SERVICE_URL}/carts/{customer_id}/", default=[])
        return data if isinstance(data, list) else []

    def _book_review_stats(self, book_id, reference_data):
        reviews = reference_data["reviews_by_book"].get(book_id, [])
        avg_rating = mean([safe_float(review.get("rating"), 0) for review in reviews])
        return {"average_rating": round(avg_rating, 2) if reviews else 0.0, "total_reviews": len(reviews)}

    def _customer_context(self, customer_id, reference_data):
        books_by_id = reference_data["books_by_id"]
        orders = reference_data["orders_by_customer"].get(customer_id, [])
        reviews = reference_data["reviews_by_customer"].get(customer_id, [])
        cart_items = self._fetch_cart_items(customer_id)
        category_scores = defaultdict(float)
        purchased_book_ids = []
        purchased_prices = []
        recent_order_book_ids = []
        total_spent = 0.0

        for order in orders:
            for item in order.get("items", []) or []:
                book = books_by_id.get(item.get("book_id"))
                if not book:
                    continue
                quantity = max(1, safe_int(item.get("quantity"), 1))
                category_id = book.get("category_id")
                if category_id:
                    category_scores[category_id] += 3.0 * quantity
                price = safe_float(item.get("price"), safe_float(book.get("price"), 0))
                purchased_book_ids.append(book["id"])
                purchased_prices.extend([price] * quantity)
                total_spent += price * quantity
                recent_order_book_ids.append(book["id"])

        for review in reviews:
            book = books_by_id.get(review.get("book_id"))
            if not book:
                continue
            category_id = book.get("category_id")
            if category_id:
                category_scores[category_id] += 2.0 * max(1.0, safe_float(review.get("rating"), 0) / 2.0)

        for item in cart_items:
            book = books_by_id.get(item.get("book_id"))
            if not book:
                continue
            category_id = book.get("category_id")
            if category_id:
                category_scores[category_id] += 1.5 * max(1, safe_int(item.get("quantity"), 1))

        interacted_book_ids = list(dict.fromkeys(
            purchased_book_ids + [review.get("book_id") for review in reviews] + [item.get("book_id") for item in cart_items]
        ))
        recent_book_ids = list(dict.fromkeys(([item.get("book_id") for item in cart_items] + list(reversed(recent_order_book_ids)))))[-MAX_RECENT_BOOKS:]
        recent_book_ids = [book_id for book_id in recent_book_ids if book_id in books_by_id]
        recent_category_ids = []
        for book_id in recent_book_ids:
            category_id = books_by_id[book_id].get("category_id")
            if category_id and category_id not in recent_category_ids:
                recent_category_ids.append(category_id)
        recent_category_ids = recent_category_ids[-MAX_RECENT_CATEGORIES:]

        favorite_category_id = None
        if category_scores:
            favorite_category_id = max(category_scores.items(), key=lambda item: item[1])[0]
        total_category_score = sum(category_scores.values()) or 1.0
        top_categories = [{
            "category_id": category_id,
            "category_name": reference_data["categories_by_id"].get(category_id, {}).get("name", f"Category #{category_id}"),
            "score": round(score / total_category_score, 2),
        } for category_id, score in sorted(category_scores.items(), key=lambda item: item[1], reverse=True)[:3]]

        avg_order_value = total_spent / len(orders) if orders else 0.0
        avg_book_price = mean(purchased_prices) if purchased_prices else 0.0
        last_order_at = parse_dt(orders[0].get("created_at")) if orders else None
        days_since_last_order = (datetime.now(timezone.utc) - last_order_at).days if last_order_at else 999
        order_count_30d = sum(1 for order in orders if (datetime.now(timezone.utc) - parse_dt(order.get("created_at"))).days <= 30)
        avg_rating_given = mean([safe_float(review.get("rating"), 0) for review in reviews]) if reviews else 0.0

        category_counter = Counter()
        for book_id in purchased_book_ids:
            category_id = books_by_id.get(book_id, {}).get("category_id")
            if category_id:
                category_counter[category_id] += 1
        favorite_category_ratio = (category_counter.get(favorite_category_id, 0) / len(purchased_book_ids)) if purchased_book_ids and favorite_category_id else 0.0
        technology_category_ids = {
            category["id"]
            for category in reference_data["categories"]
            if "tech" in category.get("name", "").lower() or "program" in category.get("name", "").lower()
        }
        technology_ratio = 0.0
        if purchased_book_ids and technology_category_ids:
            technology_ratio = sum(
                1 for book_id in purchased_book_ids
                if books_by_id.get(book_id, {}).get("category_id") in technology_category_ids
            ) / len(purchased_book_ids)

        if avg_book_price:
            price_band = price_band_from_value(avg_book_price)
        elif cart_items:
            price_band = price_band_from_value(mean([
                safe_float(books_by_id.get(item.get("book_id"), {}).get("price"), 0)
                for item in cart_items
            ]))
        else:
            price_band = "medium"

        return {
            "customer_id": customer_id,
            "top_categories": top_categories,
            "price_band": price_band,
            "signals_summary": {
                "order_count_total": len(orders),
                "review_count": len(reviews),
                "days_since_last_order": days_since_last_order,
                "cart_item_count": sum(max(1, safe_int(item.get("quantity"), 1)) for item in cart_items),
            },
            "numerical_features": [
                float(len(orders)),
                float(order_count_30d),
                float(total_spent),
                float(avg_order_value),
                float(avg_book_price),
                float(days_since_last_order),
                float(sum(max(1, safe_int(item.get("quantity"), 1)) for item in cart_items)),
                float(len(cart_items)),
                float(len(reviews)),
                float(avg_rating_given),
                float(favorite_category_ratio),
                float(technology_ratio),
            ],
            "favorite_category_id": favorite_category_id,
            "recent_book_ids": recent_book_ids,
            "recent_category_ids": recent_category_ids,
            "interacted_book_ids": interacted_book_ids,
            "purchased_book_ids": list(dict.fromkeys(purchased_book_ids)),
            "review_items": reviews,
            "cart_items": cart_items,
        }

    def _build_training_samples(self, reference_data):
        books = [book for book in reference_data["books"] if safe_int(book.get("stock"), 0) > 0]
        all_book_ids = [book["id"] for book in books]
        customer_ids = [customer["id"] for customer in reference_data["customers"] if isinstance(customer, dict)]
        category_ids = [category["id"] for category in reference_data["categories"] if isinstance(category, dict)]
        samples = []
        positives = 0
        negatives = 0

        for customer_id in customer_ids:
            context = self._customer_context(customer_id, reference_data)
            positive_book_ids = list(dict.fromkeys(
                context["purchased_book_ids"] +
                [review.get("book_id") for review in context["review_items"]] +
                [item.get("book_id") for item in context["cart_items"]]
            ))
            if not positive_book_ids:
                continue
            negative_pool = [book_id for book_id in all_book_ids if book_id not in positive_book_ids]
            for positive_book_id in positive_book_ids:
                samples.append({
                    "customer_id": customer_id,
                    "candidate_book_id": positive_book_id,
                    "recent_book_ids": context["recent_book_ids"],
                    "recent_category_ids": context["recent_category_ids"],
                    "numerical_features": context["numerical_features"],
                    "label": 1,
                })
                positives += 1
                positive_category = reference_data["books_by_id"].get(positive_book_id, {}).get("category_id")
                same_category = [
                    book_id for book_id in negative_pool
                    if reference_data["books_by_id"].get(book_id, {}).get("category_id") == positive_category
                ][:2]
                additional = [book_id for book_id in negative_pool if book_id not in same_category][:2]
                for negative_book_id in same_category + additional:
                    samples.append({
                        "customer_id": customer_id,
                        "candidate_book_id": negative_book_id,
                        "recent_book_ids": context["recent_book_ids"],
                        "recent_category_ids": context["recent_category_ids"],
                        "numerical_features": context["numerical_features"],
                        "label": 0,
                    })
                    negatives += 1

        return {
            "samples": samples,
            "customer_ids": customer_ids,
            "book_ids": all_book_ids,
            "category_ids": category_ids,
            "positives": positives,
            "negatives": negatives,
        }

    def train_model(self):
        reference_data = self.fetch_reference_data()
        training = self._build_training_samples(reference_data)
        if not training["samples"]:
            return {
                "trained": False,
                "model": None,
                "model_version": MODEL_VERSION,
                "trained_at": None,
                "dataset_stats": {"samples": 0, "positives": 0, "negatives": 0},
                "message": "Not enough interaction data to train model.",
            }

        model = BehaviorMLPModel.initialize(
            training["customer_ids"],
            training["book_ids"],
            training["category_ids"],
            len(training["samples"][0]["numerical_features"]),
        )
        model.train(training["samples"])
        model.artifact["dataset_stats"] = {
            "samples": len(training["samples"]),
            "positives": training["positives"],
            "negatives": training["negatives"],
        }
        self._save_model(model)
        return {
            "trained": True,
            "model": model,
            "model_version": MODEL_VERSION,
            "trained_at": model.artifact.get("trained_at"),
            "dataset_stats": model.artifact.get("dataset_stats"),
        }

    def get_status(self):
        model = self._load_model()
        if not model:
            return {
                "healthy": True,
                "artifact_exists": False,
                "artifact_path": str(MODEL_ARTIFACT_PATH),
                "model_version": MODEL_VERSION,
                "trained_at": None,
                "dataset_stats": {},
            }
        return {
            "healthy": True,
            "artifact_exists": True,
            "artifact_path": str(MODEL_ARTIFACT_PATH),
            "model_version": model.artifact.get("model_version", MODEL_VERSION),
            "trained_at": model.artifact.get("trained_at"),
            "dataset_stats": model.artifact.get("dataset_stats", {}),
        }

    def _ensure_model(self):
        model = self._load_model()
        if model:
            return model
        return self.train_model().get("model")

    def _cold_start_candidates(self, reference_data, limit):
        ranked = []
        for book in reference_data["books"]:
            if safe_int(book.get("stock"), 0) <= 0:
                continue
            review_stats = self._book_review_stats(book["id"], reference_data)
            score = review_stats["average_rating"] * 10 + review_stats["total_reviews"]
            ranked.append((score, book))
        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = []
        seen_categories = set()
        for _, book in ranked:
            category_id = book.get("category_id")
            if category_id and category_id not in seen_categories:
                selected.append(book)
                seen_categories.add(category_id)
            if len(selected) >= limit:
                break
        if len(selected) < limit:
            selected_ids = {book["id"] for book in selected}
            for _, book in ranked:
                if book["id"] not in selected_ids:
                    selected.append(book)
                if len(selected) >= limit:
                    break
        return [{
            "book_id": book["id"],
            "score": round(0.45 + (self._book_review_stats(book["id"], reference_data)["average_rating"] / 10.0), 4),
            "reason_codes": ["cold_start", "top_rated"],
        } for book in selected[:limit]]

    def _reason_codes(self, book, context, review_stats):
        reasons = []
        if context["favorite_category_id"] and book.get("category_id") == context["favorite_category_id"]:
            reasons.append("favorite_category")
        if book["id"] in context["recent_book_ids"] or book.get("category_id") in context["recent_category_ids"]:
            reasons.append("matches_recent_interest")
        if price_band_from_value(safe_float(book.get("price"), 0)) == context["price_band"]:
            reasons.append(f"{context['price_band']}_price_match")
        if review_stats["average_rating"] >= 4.0:
            reasons.append("review_affinity")
        return reasons[:3] or ["catalog_match"]

    def _heuristic_score(self, book, context, review_stats):
        score = 0.15
        if context["favorite_category_id"] and book.get("category_id") == context["favorite_category_id"]:
            score += 0.35
        if book.get("category_id") in context["recent_category_ids"]:
            score += 0.20
        if price_band_from_value(safe_float(book.get("price"), 0)) == context["price_band"]:
            score += 0.10
        score += min(0.15, review_stats["average_rating"] / 35.0)
        return max(0.0, min(score, 0.99))

    def build_profile(self, customer_id, limit=10, exclude_recent_purchased=True):
        reference_data = self.fetch_reference_data()
        context = self._customer_context(customer_id, reference_data)
        if not context["interacted_book_ids"]:
            categories = context["top_categories"] or [{
                "category_id": category["id"],
                "category_name": category.get("name", f"Category #{category['id']}"),
                "score": 0.33,
            } for category in reference_data["categories"][:3]]
            return {
                "customer_id": customer_id,
                "preferred_categories": categories,
                "price_band": "medium",
                "signals_summary": context["signals_summary"],
                "candidate_books": self._cold_start_candidates(reference_data, limit),
                "fallback_used": True,
                "model_version": MODEL_VERSION,
            }

        model = self._ensure_model()
        model_ok = bool(model)
        excluded_book_ids = set(context["purchased_book_ids"]) if exclude_recent_purchased else set()
        ranked = []
        for book in reference_data["books"]:
            if safe_int(book.get("stock"), 0) <= 0:
                continue
            if book["id"] in excluded_book_ids:
                continue
            review_stats = self._book_review_stats(book["id"], reference_data)
            heuristic_score = self._heuristic_score(book, context, review_stats)
            model_score = heuristic_score
            if model_ok:
                try:
                    model_score = model.predict({
                        "customer_id": customer_id,
                        "candidate_book_id": book["id"],
                        "recent_book_ids": context["recent_book_ids"],
                        "recent_category_ids": context["recent_category_ids"],
                        "numerical_features": context["numerical_features"],
                    })
                except Exception:
                    model_ok = False
                    model_score = heuristic_score
            ranked.append({
                "book_id": book["id"],
                "score": round((0.75 * model_score) + (0.25 * heuristic_score), 4),
                "reason_codes": self._reason_codes(book, context, review_stats),
            })
        ranked.sort(key=lambda item: item["score"], reverse=True)
        if not ranked:
            ranked = self._cold_start_candidates(reference_data, limit)
            model_ok = False
        return {
            "customer_id": customer_id,
            "preferred_categories": context["top_categories"],
            "price_band": context["price_band"],
            "signals_summary": context["signals_summary"],
            "candidate_books": ranked[:limit],
            "fallback_used": not model_ok,
            "model_version": MODEL_VERSION,
        }
