import os
import re
from collections import Counter

import requests

BEHAVIOR_SERVICE_URL = "http://behavior-ai-service:8000"
BOOK_SERVICE_URL = "http://book-service:8000"
CATALOG_SERVICE_URL = "http://catalog-service:8000"
COMMENT_RATE_SERVICE_URL = "http://comment-rate-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_PROMPT = "Suggest books for me based on my profile."
STOP_WORDS = {
    "i", "me", "my", "you", "your", "for", "the", "and", "with", "want", "about", "learn",
    "learnt", "books", "book", "suggest", "recommend", "recommendation", "please", "help", "find",
    "toi", "muon", "sach", "goi", "y", "cho", "ve", "hoc", "tim", "mot", "cuon", "nhung",
    "khi", "toi", "can", "them", "mua", "doc", "gia", "that", "that", "from", "when",
}


class HttpClient:
    def get_json(self, url, params=None, timeout=5, default=None):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException:
            pass
        return [] if default is None else default

    def post_json(self, url, payload, timeout=8, default=None):
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            if response.status_code in (200, 201):
                return response.json()
        except requests.exceptions.RequestException:
            pass
        return {} if default is None else default


class AdvisorService:
    def __init__(self):
        self.client = HttpClient()

    def recommend(self, customer_id, user_prompt=None, limit=3):
        user_prompt = (user_prompt or DEFAULT_PROMPT).strip() or DEFAULT_PROMPT
        categories = self.client.get_json(f"{CATALOG_SERVICE_URL}/categories/", default=[])
        category_map = {item["id"]: item for item in categories if isinstance(item, dict)}
        query_intent = self._parse_query_intent(user_prompt, categories)

        behavior = self.client.post_json(
            f"{BEHAVIOR_SERVICE_URL}/behavior/profile/",
            {"customer_id": customer_id, "limit": max(limit * 6, 18), "exclude_recent_purchased": True},
            default={},
        )
        fallback_used = not bool(behavior)
        if not behavior:
            behavior = {
                "customer_id": customer_id,
                "preferred_categories": [],
                "price_band": "medium",
                "signals_summary": {},
                "candidate_books": [],
                "fallback_used": True,
                "model_version": "behavior-mlp-v1",
            }

        ordered_book_ids = self._fetch_ordered_book_ids(customer_id)
        candidate_books = [
            item for item in behavior.get("candidate_books", [])
            if item.get("book_id") and item.get("book_id") not in ordered_book_ids
        ]

        candidate_books.extend(
            self._supplement_unseen_candidates(
                behavior=behavior,
                ordered_book_ids=ordered_book_ids,
                existing_candidate_ids={item.get("book_id") for item in candidate_books if item.get("book_id")},
                limit_needed=max(0, max(limit * 4, 12) - len(candidate_books)),
                query_intent=query_intent,
                category_map=category_map,
            )
        )
        candidate_books = self._dedupe_candidates(candidate_books)

        candidate_ids = [item.get("book_id") for item in candidate_books if item.get("book_id")]
        kb_books = self._build_kb_books(candidate_books, candidate_ids, category_map)
        ranked_books = self._rerank_books(kb_books, behavior, query_intent)
        selected_books = self._focus_ranked_books(ranked_books, query_intent, limit)

        prompt_context = self._build_prompt_context(behavior, selected_books, user_prompt)
        answer_text = self._call_gemini(prompt_context)
        if not answer_text:
            fallback_used = True
            answer_text = self._build_fallback_answer(selected_books, behavior, user_prompt)

        return {
            "customer_id": customer_id,
            "answer_text": answer_text,
            "recommended_books": [self._public_book_payload(book) for book in selected_books],
            "behavior_summary": {
                "preferred_categories": [item.get("category_name") for item in behavior.get("preferred_categories", [])],
                "price_band": behavior.get("price_band", "medium"),
            },
            "sources": {
                "behavior_model_version": behavior.get("model_version", "behavior-mlp-v1"),
                "kb_book_ids": [book["book_id"] for book in selected_books],
                "ordered_book_ids_filtered": sorted(ordered_book_ids),
            },
            "fallback_used": fallback_used or behavior.get("fallback_used", False),
            "recommendations": [self._legacy_book_payload(book) for book in selected_books],
            "user_prompt": user_prompt,
        }

    def _fetch_ordered_book_ids(self, customer_id):
        orders = self.client.get_json(
            f"{ORDER_SERVICE_URL}/orders/",
            params={"customer_id": customer_id},
            default=[],
        )
        ordered_book_ids = set()
        for order in orders:
            for item in order.get("items", []) or []:
                book_id = item.get("book_id")
                if book_id:
                    ordered_book_ids.add(book_id)
        return ordered_book_ids

    def _dedupe_candidates(self, candidate_books):
        deduped = {}
        for item in candidate_books:
            book_id = item.get("book_id")
            if not book_id:
                continue
            current = deduped.get(book_id)
            if current is None or float(item.get("score", 0.0)) > float(current.get("score", 0.0)):
                deduped[book_id] = item
        return sorted(deduped.values(), key=lambda item: float(item.get("score", 0.0)), reverse=True)

    def _supplement_unseen_candidates(self, behavior, ordered_book_ids, existing_candidate_ids, limit_needed, query_intent, category_map):
        if limit_needed <= 0:
            return []

        books = self.client.get_json(f"{BOOK_SERVICE_URL}/books/", default=[])
        preferred_categories = {item.get("category_id") for item in behavior.get("preferred_categories", [])}
        preferred_price_band = behavior.get("price_band", "medium")
        supplements = []

        for book in books:
            book_id = book.get("id")
            if not book_id or book_id in ordered_book_ids or book_id in existing_candidate_ids:
                continue
            if int(book.get("stock") or 0) <= 0:
                continue

            category_name = category_map.get(book.get("category_id"), {}).get("name", "")
            haystack = self._book_prompt_haystack(book, category_name)
            query_score, query_reasons = self._query_match_score(haystack, query_intent)

            score = 0.10 + query_score
            reason_codes = ["unseen_book"] + query_reasons
            if book.get("category_id") in preferred_categories:
                score += 0.16
                reason_codes.append("preferred_category_exploration")
            if query_intent["matched_categories"] and book.get("category_id") in query_intent["matched_categories"]:
                score += 0.22
                reason_codes.append("query_category_match")
            elif query_intent["matched_categories"]:
                score -= 0.14
            if self._price_band(book.get("price")) == preferred_price_band:
                score += 0.06
                reason_codes.append(f"{preferred_price_band}_price_match")
            if query_intent["strong_intent"] and query_score == 0 and not query_intent["matched_categories"]:
                score -= 0.12

            supplements.append({
                "book_id": book_id,
                "score": round(min(max(score, 0.01), 0.98), 4),
                "reason_codes": list(dict.fromkeys(reason_codes))[:5],
            })

        supplements.sort(key=lambda item: item["score"], reverse=True)
        return supplements[:limit_needed]

    def _build_kb_books(self, candidate_books, candidate_ids, category_map):
        behavior_map = {item["book_id"]: item for item in candidate_books if item.get("book_id")}
        books = []
        for book_id in candidate_ids:
            book = self.client.get_json(f"{BOOK_SERVICE_URL}/books/{book_id}/", default={})
            if not isinstance(book, dict) or not book:
                continue
            review_bundle = self.client.get_json(f"{COMMENT_RATE_SERVICE_URL}/reviews/book/{book_id}/", default={})
            reviews = review_bundle.get("reviews", []) if isinstance(review_bundle, dict) else []
            review_summary = self._summarize_reviews(reviews, review_bundle)
            category = category_map.get(book.get("category_id"), {})
            behavior_item = behavior_map.get(book_id, {})
            books.append({
                "book_id": book["id"],
                "title": book.get("title", "Unknown"),
                "author": book.get("author", "Unknown"),
                "category_id": book.get("category_id"),
                "category_name": category.get("name", "Unknown"),
                "price": book.get("price"),
                "price_band": self._price_band(book.get("price")),
                "stock": book.get("stock", 0),
                "isbn": book.get("isbn", ""),
                "description_short": self._short_description(book.get("description", "")),
                "review_summary": review_summary["review_summary"],
                "positive_themes": review_summary["positive_themes"],
                "negative_themes": review_summary["negative_themes"],
                "reader_fit_summary": review_summary["reader_fit_summary"],
                "avg_rating": review_summary["avg_rating"],
                "total_reviews": review_summary["total_reviews"],
                "embedding_text": review_summary["embedding_text"],
                "behavior_score": behavior_item.get("score", 0.0),
                "reason_codes": behavior_item.get("reason_codes", []),
            })
        return books

    def _summarize_reviews(self, reviews, review_bundle):
        avg_rating = review_bundle.get("average_rating") if isinstance(review_bundle, dict) else None
        total_reviews = review_bundle.get("total_reviews") if isinstance(review_bundle, dict) else None
        comments = [review.get("comment", "") for review in reviews if review.get("comment")]
        combined = " ".join(comments).lower()
        tokens = {
            "practical": ["practical", "thuc hanh", "example", "hands-on", "project"],
            "clear": ["clear", "easy", "readable", "de doc"],
            "backend": ["backend", "django", "api", "python", "system design"],
            "productivity": ["habit", "atomic", "self", "productivity"],
            "advanced": ["advanced", "nang cao"],
            "basic": ["basic", "co ban", "beginner"],
        }
        counts = Counter()
        for label, keywords in tokens.items():
            for keyword in keywords:
                if keyword in combined:
                    counts[label] += 1
        positive_themes = []
        if counts["practical"]:
            positive_themes.append("practical")
        if counts["clear"]:
            positive_themes.append("clear_examples")
        if counts["backend"]:
            positive_themes.append("backend_friendly")
        if counts["productivity"]:
            positive_themes.append("habit_building")
        negative_themes = []
        if counts["advanced"]:
            negative_themes.append("advanced_leaning")
        if counts["basic"]:
            negative_themes.append("basic_for_advanced_readers")

        if avg_rating is None:
            ratings = [review.get("rating") for review in reviews if review.get("rating") is not None]
            avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
        if total_reviews is None:
            total_reviews = len(reviews)

        if avg_rating >= 4.5:
            sentiment = "Highly rated by readers"
        elif avg_rating >= 4.0:
            sentiment = "Well rated by readers"
        elif total_reviews:
            sentiment = "Mixed feedback from readers"
        else:
            sentiment = "Not enough reviews yet"

        fit_parts = []
        if counts["backend"]:
            fit_parts.append("backend and software engineering readers")
        if counts["productivity"]:
            fit_parts.append("readers interested in personal growth")
        if counts["basic"]:
            fit_parts.append("beginners")
        if counts["advanced"] and not counts["basic"]:
            fit_parts.append("intermediate to advanced readers")
        if not fit_parts:
            fit_parts.append("general readers")

        review_summary = sentiment
        if positive_themes:
            review_summary += " for " + ", ".join(theme.replace("_", " ") for theme in positive_themes)
        reader_fit_summary = "Best for " + ", ".join(fit_parts)
        embedding_text = ". ".join(part for part in [review_summary, reader_fit_summary] if part)
        return {
            "review_summary": review_summary,
            "positive_themes": positive_themes,
            "negative_themes": negative_themes,
            "reader_fit_summary": reader_fit_summary,
            "avg_rating": avg_rating,
            "total_reviews": total_reviews,
            "embedding_text": embedding_text,
        }

    def _parse_query_intent(self, user_prompt, categories):
        lowered = (user_prompt or "").lower()
        category_lookup = {str(category.get("name", "")).lower(): category.get("id") for category in categories}
        matched_categories = []
        for category in categories:
            name = category.get("name", "")
            if name and name.lower() in lowered:
                matched_categories.append(category.get("id"))

        price_pref = None
        if any(keyword in lowered for keyword in ["gia re", "cheap", "budget", "low price"]):
            price_pref = "low"
        elif any(keyword in lowered for keyword in ["vua phai", "medium", "mid price"]):
            price_pref = "medium"
        elif any(keyword in lowered for keyword in ["cao cap", "premium", "expensive"]):
            price_pref = "high"

        reading_level = None
        if any(keyword in lowered for keyword in ["de doc", "beginner", "moi bat dau", "co ban"]):
            reading_level = "beginner"
        elif any(keyword in lowered for keyword in ["nang cao", "advanced", "intermediate"]):
            reading_level = "advanced"

        preference_tags = []
        if any(keyword in lowered for keyword in ["thuc hanh", "practical", "hands-on"]):
            preference_tags.append("practical")
        if any(keyword in lowered for keyword in ["ly thuyet", "theory", "foundation"]):
            preference_tags.append("theory")
        if any(keyword in lowered for keyword in ["backend", "django", "api", "python", "system design", "software", "code", "architecture"]):
            preference_tags.append("backend")
        if any(keyword in lowered for keyword in ["habit", "self", "productivity", "phat trien"]):
            preference_tags.append("productivity")

        inferred_category_keywords = {
            "technology": ["backend", "django", "api", "python", "system design", "software", "code", "architecture", "programming"],
            "business": ["business", "startup", "money", "finance", "invest"],
            "self development": ["habit", "productivity", "self development", "growth", "focus"],
            "literature": ["novel", "literature", "fiction", "story"],
            "history": ["history", "historical", "civilization"],
            "biography": ["biography", "memoir", "life story"],
            "children": ["children", "kids", "comic", "manga"],
        }
        for category_name, keywords in inferred_category_keywords.items():
            category_id = category_lookup.get(category_name)
            if category_id and any(keyword in lowered for keyword in keywords):
                matched_categories.append(category_id)

        tokens = re.findall(r"[a-z0-9]+", lowered)
        filtered_tokens = [token for token in tokens if len(token) >= 3 and token not in STOP_WORDS]
        query_terms = list(dict.fromkeys(filtered_tokens))[:8]
        query_phrases = []
        for index in range(len(filtered_tokens) - 1):
            query_phrases.append(filtered_tokens[index] + " " + filtered_tokens[index + 1])
        query_phrases = list(dict.fromkeys(query_phrases))[:6]
        strong_intent = bool(query_terms or matched_categories or preference_tags)

        return {
            "matched_categories": matched_categories,
            "price_pref": price_pref,
            "reading_level": reading_level,
            "preference_tags": preference_tags,
            "query_terms": query_terms,
            "query_phrases": query_phrases,
            "strong_intent": strong_intent,
        }

    def _book_prompt_haystack(self, book, category_name):
        return " ".join([
            str(book.get("title", "")),
            str(book.get("author", "")),
            str(category_name or ""),
            str(book.get("description", "")),
        ]).lower()

    def _tokenize_text(self, text):
        return set(re.findall(r"[a-z0-9]+", (text or "").lower()))

    def _contains_phrase(self, haystack, phrase):
        if not phrase:
            return False
        pattern = rf"(?<![a-z0-9]){re.escape(phrase.lower())}(?![a-z0-9])"
        return re.search(pattern, haystack) is not None

    def _query_match_score(self, haystack, query_intent):
        haystack = (haystack or "").lower()
        haystack_tokens = self._tokenize_text(haystack)
        score = 0.0
        reasons = []
        phrase_hits = 0
        for phrase in query_intent.get("query_phrases", []):
            if self._contains_phrase(haystack, phrase):
                phrase_hits += 1
        if phrase_hits:
            score += min(0.45, 0.22 * phrase_hits)
            reasons.append("query_phrase_match")

        term_hits = 0
        for term in query_intent.get("query_terms", []):
            if term in haystack_tokens:
                term_hits += 1
        if term_hits:
            score += min(0.35, 0.08 * term_hits)
            reasons.append("query_term_match")

        for tag in query_intent.get("preference_tags", []):
            if tag == "backend" and (
                any(token in haystack_tokens for token in ["backend", "api", "django", "python", "software", "architecture", "code"])
                or self._contains_phrase(haystack, "system design")
            ):
                score += 0.10
                reasons.append("backend_match")
            elif tag == "practical" and (
                any(token in haystack_tokens for token in ["practical", "guide", "example", "examples", "hands"])
                or self._contains_phrase(haystack, "hands on")
            ):
                score += 0.08
                reasons.append("practical_match")
            elif tag == "productivity" and any(token in haystack_tokens for token in ["habit", "productivity", "focus", "growth"]):
                score += 0.08
                reasons.append("productivity_match")
            elif tag == "theory" and any(token in haystack_tokens for token in ["theory", "foundation", "principles"]):
                score += 0.08
                reasons.append("theory_match")

        return min(score, 0.75), list(dict.fromkeys(reasons))

    def _rerank_books(self, kb_books, behavior, query_intent):
        preferred_categories = {item.get("category_id") for item in behavior.get("preferred_categories", [])}
        price_band = behavior.get("price_band", "medium")
        ranked = []
        for book in kb_books:
            score = float(book.get("behavior_score", 0.0))
            reasons = list(book.get("reason_codes", []))
            if book.get("category_id") in preferred_categories:
                score += 0.12
            if query_intent["matched_categories"] and book.get("category_id") in query_intent["matched_categories"]:
                score += 0.20
                reasons.append("query_category_match")
            if query_intent["price_pref"] and book.get("price_band") == query_intent["price_pref"]:
                score += 0.12
                reasons.append("query_price_match")
            elif not query_intent["price_pref"] and book.get("price_band") == price_band:
                score += 0.04

            haystack = " ".join([
                book.get("title", ""),
                book.get("author", ""),
                book.get("category_name", ""),
                book.get("description_short", ""),
                book.get("review_summary", ""),
                book.get("reader_fit_summary", ""),
            ]).lower()
            query_score, query_reasons = self._query_match_score(haystack, query_intent)
            score += query_score
            reasons.extend(query_reasons)

            if query_intent["reading_level"] == "beginner" and any(tag in book.get("reader_fit_summary", "").lower() for tag in ["beginner", "general"]):
                score += 0.06
                reasons.append("beginner_fit")
            if query_intent["reading_level"] == "advanced" and "advanced" in " ".join(book.get("negative_themes", [])).lower():
                score += 0.04
                reasons.append("advanced_fit")

            score += min(0.08, float(book.get("avg_rating") or 0.0) / 60.0)
            if query_intent["strong_intent"] and query_score == 0 and not query_intent["matched_categories"]:
                score -= 0.18
            if int(book.get("stock") or 0) <= 0:
                score -= 1.0

            book["final_score"] = round(score, 4)
            book["query_match_score"] = round(query_score, 4)
            book["reason_codes"] = list(dict.fromkeys(reasons))[:6]
            ranked.append(book)
        ranked.sort(key=lambda item: item.get("final_score", 0.0), reverse=True)
        return ranked

    def _focus_ranked_books(self, ranked_books, query_intent, limit):
        hard_limit = max(1, min(limit, 5))
        if not query_intent.get("strong_intent"):
            return ranked_books[:hard_limit]

        def is_query_match(book):
            reasons = set(book.get("reason_codes", []))
            if book.get("query_match_score", 0.0) >= 0.18:
                return True
            if reasons.intersection({"query_phrase_match", "query_term_match", "query_category_match", "backend_match", "practical_match", "productivity_match", "theory_match"}):
                return True
            return False

        focused = ranked_books
        strong_matches = [book for book in ranked_books if is_query_match(book)]
        if strong_matches:
            focused = strong_matches

        matched_categories = set(query_intent.get("matched_categories", []))
        category_matches = [book for book in focused if book.get("category_id") in matched_categories]
        if matched_categories and category_matches:
            focused = category_matches

        if len(focused) < hard_limit:
            existing_ids = {book.get("book_id") for book in focused}
            for book in ranked_books:
                if book.get("book_id") in existing_ids:
                    continue
                if matched_categories and book.get("category_id") not in matched_categories and strong_matches:
                    continue
                focused.append(book)
                existing_ids.add(book.get("book_id"))
                if len(focused) >= hard_limit:
                    break

        return focused[:hard_limit]

    def _build_prompt_context(self, behavior, books, user_prompt):
        categories = ", ".join(item.get("category_name", "Unknown") for item in behavior.get("preferred_categories", [])) or "Unknown"
        customer_profile_text = (
            f"Preferred categories: {categories}\n"
            f"Price band: {behavior.get('price_band', 'medium')}\n"
            f"Signals: {behavior.get('signals_summary', {})}"
        )
        lines = []
        for index, book in enumerate(books, start=1):
            lines.append(
                f"{index}. {book['title']} by {book['author']} | Category: {book['category_name']} | Price: {book['price']} | "
                f"Avg rating: {book['avg_rating']} | Why: {', '.join(book.get('reason_codes', []))} | "
                f"Summary: {book['description_short']} | Reviews: {book['review_summary']}"
            )
        candidate_books_text = "\n".join(lines) if lines else "No strong candidates found."
        return (
            "You are a personalized book recommendation assistant.\n"
            "Your only goal is to recommend books that fit the user's interests.\n"
            "Use only the provided context.\n"
            "Do not invent books outside the candidate list.\n"
            "Prefer in-stock books.\n"
            "Prioritize the user's current request over generic profile similarity when they conflict.\n"
            "Answer briefly and clearly.\n\n"
            "[Customer Profile]\n"
            f"{customer_profile_text}\n\n"
            "[Candidate Books]\n"
            f"{candidate_books_text}\n\n"
            "[User Request]\n"
            f"{user_prompt}"
        )

    def _call_gemini(self, prompt):
        if not GEMINI_API_KEY:
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 220},
        }
        try:
            response = requests.post(url, json=payload, timeout=8)
            if response.status_code != 200:
                return None
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            return None

    def _build_fallback_answer(self, books, behavior, user_prompt):
        if not books:
            return "I could not find a strong personalized match yet. Try rating or ordering a few books so the system can learn your taste better."
        lead = books[0]
        titles = ", ".join(book["title"] for book in books[:3])
        return (
            f"You can start with {titles}. {lead['title']} stands out because it is unseen in your order history, "
            f"fits your current request, and still aligns with your broader reading profile. User request: {user_prompt}"
        )

    def _short_description(self, description):
        text = (description or "").strip()
        if not text:
            return "No short description available."
        return text[:180] + ("..." if len(text) > 180 else "")

    def _price_band(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0.0
        if value < 160000:
            return "low"
        if value < 300000:
            return "medium"
        return "high"

    def _public_book_payload(self, book):
        return {
            "book_id": book["book_id"],
            "title": book["title"],
            "author": book["author"],
            "price": book["price"],
            "category_name": book["category_name"],
            "why_recommended": self._reason_to_text(book),
            "avg_rating": book.get("avg_rating"),
            "description_short": book.get("description_short"),
            "reason_codes": book.get("reason_codes", []),
        }

    def _legacy_book_payload(self, book):
        return {
            "id": book["book_id"],
            "title": book["title"],
            "author": book["author"],
            "price": book["price"],
            "avg_rating": book.get("avg_rating"),
            "category_name": book.get("category_name"),
            "why_recommended": self._reason_to_text(book),
        }

    def _reason_to_text(self, book):
        mapping = {
            "favorite_category": "matches the category you buy most often",
            "matches_recent_interest": "aligns with your recent reading interest",
            "unseen_book": "is new to you and not in your past orders",
            "preferred_category_exploration": "matches your strong category preference while still being unseen",
            "medium_price_match": "fits your usual mid-price range",
            "low_price_match": "fits a budget-friendly range",
            "high_price_match": "fits your premium-leaning purchases",
            "review_affinity": "has strong review signals",
            "query_category_match": "matches the topic you asked for",
            "query_price_match": "matches the price you described",
            "query_term_match": "contains key terms from your request",
            "query_phrase_match": "directly matches the subject you asked about",
            "practical_match": "leans toward practical guidance",
            "backend_match": "fits software engineering or backend learning",
            "productivity_match": "fits productivity and self-growth interests",
            "theory_match": "leans toward foundational concepts",
            "beginner_fit": "easy to approach for newer readers",
            "advanced_fit": "better for readers with some background",
        }
        labels = [mapping[code] for code in book.get("reason_codes", []) if code in mapping]
        return ", ".join(labels[:2]) if labels else "fits your current reading profile"
