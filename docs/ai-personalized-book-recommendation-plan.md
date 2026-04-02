# AI Personalized Book Recommendation Plan

## Summary
This implementation adds a 3-layer recommendation flow for the bookstore system:
- `behavior-ai-service` builds personalized behavior profiles and candidate books.
- `recommender-ai-service` now acts as the advisor layer that enriches books with KB-style summaries and generates personalized recommendation answers.
- `api-gateway` keeps the existing recommendation page and adds an advisor chat form on the same screen.

## Layer 1: Behavior Model
- Internal endpoint: `POST /behavior/profile/`
- Internal endpoint: `POST /behavior/train/`
- Internal endpoint: `GET /behavior/status/`
- Data sources: customer, orders, cart, books, categories, reviews.
- Output includes:
  - `preferred_categories`
  - `price_band`
  - `signals_summary`
  - `candidate_books`
  - `fallback_used`
  - `model_version`
- Model strategy in V1:
  - lightweight pure-Python embedding + MLP implementation
  - artifact stored in `/app/data/behavior_model.json`
  - automatic lazy training when profile inference needs a model and no artifact exists
  - rule-based fallback for cold start and degraded cases

## Layer 2: Knowledge Base
- Implemented inside `recommender-ai-service` as canonical per-book enrichment.
- Source fields:
  - book metadata from `book-service`
  - category labels from `catalog-service`
  - review aggregates and comments from `comment-rate-service`
- Per-book KB payload includes:
  - product facts
  - short description
  - review summary
  - positive and negative themes
  - reader fit summary
  - average rating and review count
  - behavior score and reason codes
- Retrieval strategy is candidate-first lookup using `candidate_book_ids` from behavior output.

## Layer 3: Advisor RAG
- Public internal endpoint: `POST /advisor/recommendations/`
- Compatibility endpoint kept: `GET /recommendations/<customer_id>/`
- Context assembly:
  - customer profile text
  - candidate book text
  - user prompt
- Gemini call is optional and uses:
  - `GEMINI_API_KEY`
  - `GEMINI_MODEL`
- If Gemini fails or no key is present, the service returns a deterministic fallback explanation.

## Gateway Integration
- `GET /recommendations/<customer_id>/` still renders the main recommendation page.
- Added `POST /recommendations/<customer_id>/ask/` for the advisor chat form.
- UI now shows:
  - answer text from the advisor
  - personalized recommended books
  - explanation tags and summary
  - cart and review actions for each recommended book

## Infrastructure
- Added new service: `behavior-ai-service`
- Updated `docker-compose.yml` to wire:
  - `behavior-ai-service`
  - `recommender-ai-service` environment for Gemini
  - gateway dependency on the new service

## Review Checklist
- Verify behavior profile endpoint returns non-empty candidates for seeded customer data.
- Verify advisor endpoint returns `answer_text`, `recommended_books`, and `behavior_summary`.
- Verify recommendation page renders correctly and submits advisor prompts.
- Verify fallback behavior still works when Gemini is unavailable.
