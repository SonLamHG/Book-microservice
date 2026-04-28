import os
import re
import time
import uuid
import logging
from datetime import timedelta
from datetime import datetime, timezone
from pathlib import Path

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Integer, String, create_engine, desc, select
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from app.graph_store import GraphStore
from app.inference import SequenceRecommender
from app.vector_store import VectorProductStore

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/ai.db")
JWT_SECRET = os.getenv("JWT_SHARED_SECRET", "change-me-shared-secret")
JWT_ALGORITHM = "HS256"
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8000/api/v1/products/")
REQUEST_TIMEOUT_SEC = float(os.getenv("AI_REQUEST_TIMEOUT_SEC", "5"))
MODEL_WEIGHT = float(os.getenv("AI_MODEL_WEIGHT", "3.0"))
GRAPH_WEIGHT = float(os.getenv("AI_GRAPH_WEIGHT", "1.8"))
RAG_WEIGHT = float(os.getenv("AI_RAG_WEIGHT", os.getenv("AI_VECTOR_WEIGHT", "2.2")))
VECTOR_WEIGHT = RAG_WEIGHT
LLM_ENABLED = os.getenv("AI_LLM_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
LLM_BASE_URL = os.getenv("AI_LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("AI_LLM_API_KEY", "")
LLM_MODEL = os.getenv("AI_LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT_SEC = float(os.getenv("AI_LLM_TIMEOUT_SEC", "20"))

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
Base = declarative_base()
BASE_DIR = Path(__file__).resolve().parents[1]
sequence_recommender = SequenceRecommender(BASE_DIR)
graph_store = GraphStore.from_env()
vector_store = VectorProductStore(dim=int(os.getenv("AI_VECTOR_DIM", "384")))
logger = logging.getLogger("ai-service")
logging.basicConfig(level=os.getenv("AI_LOG_LEVEL", "INFO"))


class BehaviorEvent(Base):
    __tablename__ = "behavior_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    product_id = Column(Integer, nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    query = Column(String(255), nullable=True)
    timestamp = Column(
        DateTime(timezone=True), nullable=False, index=True, default=lambda: datetime.now(timezone.utc)
    )

class EndpointMetric(Base):
    __tablename__ = "endpoint_metrics"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(64), nullable=False, index=True)
    endpoint = Column(String(64), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    role = Column(String(20), nullable=True, index=True)
    latency_ms = Column(Integer, nullable=False)
    status_code = Column(Integer, nullable=False, index=True)
    recommended_count = Column(Integer, nullable=True)
    chatbot_success = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, index=True, default=lambda: datetime.now(timezone.utc)
    )
class BehaviorEventCreate(BaseModel):
    product_id: int | None = None
    action: str = Field(min_length=2, max_length=50)
    query: str | None = Field(default=None, max_length=255)
    timestamp: datetime | None = None
    user_id: int | None = None


class ChatbotRequest(BaseModel):
    message: str = Field(min_length=2, max_length=500)
    user_id: int | None = None


class GraphRebuildRequest(BaseModel):
    reset: bool = True


ALLOWED_ACTIONS = {
    "view",
    "click",
    "add_to_cart",
    "purchase",
    "search",
    "remove_from_cart",
    "wishlist",
    "chat",
    "recommend_impression",
}


def _to_ms(start_time: float) -> int:
    return int((time.perf_counter() - start_time) * 1000)


def _p95(values: list[int]) -> float:
    if not values:
        return 0.0
    v = sorted(values)
    idx = int(0.95 * (len(v) - 1))
    return float(v[idx])


def _log_endpoint_metric(
    db: Session,
    *,
    request_id: str,
    endpoint: str,
    user_id: int | None,
    role: str | None,
    latency_ms: int,
    status_code: int,
    recommended_count: int | None = None,
    chatbot_success: int | None = None,
) -> None:
    db.add(
        EndpointMetric(
            request_id=request_id,
            endpoint=endpoint,
            user_id=user_id,
            role=role,
            latency_ms=latency_ms,
            status_code=status_code,
            recommended_count=recommended_count,
            chatbot_success=chatbot_success,
        )
    )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_optional_claims(authorization: str | None = Header(default=None)) -> dict | None:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth header")
    token = authorization.split(" ", 1)[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def get_required_claims(claims: dict | None = Depends(get_optional_claims)) -> dict:
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return claims


def get_role(claims: dict) -> str:
    return str(claims.get("role", "customer")).lower()


def ensure_can_access_user(claims: dict, target_user_id: int) -> None:
    role = get_role(claims)
    own_user_id = int(claims["sub"])
    if role not in {"admin", "staff"} and target_user_id != own_user_id:
        raise HTTPException(status_code=403, detail="Forbidden for target user")


def ensure_staff_or_admin(claims: dict) -> None:
    if get_role(claims) not in {"admin", "staff"}:
        raise HTTPException(status_code=403, detail="Staff or admin role required")


def fetch_products(search: str | None = None, category: str | None = None) -> list[dict]:
    params: dict[str, str] = {"ordering": "-created_at"}
    if search:
        params["search"] = search
    if category:
        params["category"] = category

    try:
        resp = requests.get(PRODUCT_SERVICE_URL, params=params, timeout=REQUEST_TIMEOUT_SEC)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="Cannot connect product-service") from exc

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail="product-service returned error")

    payload = resp.json()
    if isinstance(payload, list):
        return payload
    return payload.get("results", [])


def fetch_all_products_for_graph() -> list[dict]:
    products: list[dict] = []
    url = PRODUCT_SERVICE_URL
    params = {"page_size": 200}
    while url:
        try:
            resp = requests.get(url, params=params if url == PRODUCT_SERVICE_URL else None, timeout=REQUEST_TIMEOUT_SEC)
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail="Cannot connect product-service") from exc

        if resp.status_code >= 400:
            raise HTTPException(status_code=502, detail="product-service returned error")

        payload = resp.json()
        if isinstance(payload, list):
            products.extend(payload)
            break

        products.extend(payload.get("results", []))
        next_url = payload.get("next")
        if not next_url:
            break
        if next_url.startswith("http://localhost"):
            next_url = next_url.replace("http://localhost", "http://product-service:8000")
        url = next_url
    return products


def _money_to_number(number_str: str, unit: str | None) -> float:
    base = float(number_str.replace(",", "."))
    u = (unit or "").strip().lower()
    if u in {"tr", "triệu", "m"}:
        return base * 1_000_000
    if u in {"k", "nghìn", "ngàn"}:
        return base * 1_000
    return base


def parse_budget(message: str) -> float | None:
    # Backward-compatible single-value parser (used by other paths).
    text = message.lower()
    m = re.search(r"(\d+[\.,]?\d*)\s*(tr|triệu|m|k|nghìn|ngàn)?\b", text)
    if not m:
        return None
    return _money_to_number(m.group(1), m.group(2))


def parse_budget_constraint(message: str) -> tuple[float | None, float | None]:
    text = message.lower()
    range_match = re.search(
        r"(\d+[\.,]?\d*)\s*(tr|triệu|m|k|nghìn|ngàn)?\s*(?:đến|to|-)\s*(\d+[\.,]?\d*)\s*(tr|triệu|m|k|nghìn|ngàn)?",
        text,
    )
    if range_match:
        left = _money_to_number(range_match.group(1), range_match.group(2))
        right = _money_to_number(range_match.group(3), range_match.group(4) or range_match.group(2))
        return (min(left, right), max(left, right))

    value = parse_budget(text)
    if value is None:
        return (None, None)

    lower_keywords = [
        "trên",
        "hơn",
        "lớn hơn",
        "ít nhất",
        "tối thiểu",
        "minimum",
        "min",
        ">=",
    ]
    upper_keywords = [
        "dưới",
        "nhỏ hơn",
        "bé hơn",
        "không quá",
        "tối đa",
        "maximum",
        "max",
        "<=",
    ]
    if any(k in text for k in lower_keywords):
        return (value, None)
    if any(k in text for k in upper_keywords):
        return (None, value)
    return (None, value)


def _is_price_in_budget(price: float | int | str | None, budget_min: float | None, budget_max: float | None) -> bool:
    if price is None:
        return True
    try:
        p = float(price)
    except (TypeError, ValueError):
        return True
    if budget_min is not None and p < budget_min:
        return False
    if budget_max is not None and p > budget_max:
        return False
    return True


def format_vnd(value: float | int | str | None) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return f"{int(round(amount)):,.0f}".replace(",", ".")


# ---------------------------------------------------------------------------
# Category inference -- driven by CATEGORY_TERMS env variable.
# Format:  CATEGORY_TERMS=slug1:kw1,kw2;slug2:kw3,kw4
# Falls back to book-domain defaults when env var is not set.
# ---------------------------------------------------------------------------
_DEFAULT_CATEGORY_TERMS = (
    "fiction:tieu thuyet,fiction,van hoc,truyen,novel;"
    "science:khoa hoc,science,vat ly,toan,hoa hoc,sinh hoc,physics,math;"
    "children:thieu nhi,tre em,children,kids;"
    "history:lich su,history,su ky;"
    "self-help:ky nang song,self-help,phat trien ban than,tam ly,mindset;"
    "technology:cong nghe,technology,lap trinh,programming,software;"
    "business:kinh doanh,business,quan tri,marketing,tai chinh,economics;"
    "arts:nghe thuat,arts,am nhac,hoi hoa,dien anh,design;"
    "language:ngoai ngu,language,tieng anh,english,tu dien,grammar;"
    "religion:ton giao,religion,phat giao,thien chua,triet hoc,philosophy"
)


def _parse_category_terms(raw: str) -> dict[str, list[str]]:
    """Parse 'slug:kw1,kw2;slug2:kw3' format into {slug: [kw1, kw2], ...}."""
    result: dict[str, list[str]] = {}
    for entry in raw.split(";"):
        entry = entry.strip()
        if ":" not in entry:
            continue
        slug, _, kws_raw = entry.partition(":")
        slug = slug.strip()
        kws = [k.strip().lower() for k in kws_raw.split(",") if k.strip()]
        if slug and kws:
            result[slug] = kws
    return result


_CATEGORY_TERMS: dict[str, list[str]] = _parse_category_terms(
    os.getenv("CATEGORY_TERMS", _DEFAULT_CATEGORY_TERMS)
)


def infer_category(message: str) -> str | None:
    text = message.lower()
    for category, words in _CATEGORY_TERMS.items():
        if any(word in text for word in words):
            return category
    return None

def infer_search_keyword(message: str) -> str | None:
    text = message.lower()
    keyword_map = [
        ("thảm yoga", "yoga"),
        ("yoga", "yoga"),
        ("xe điều khiển", "xe điều khiển"),
        ("xếp hình", "xếp hình"),
        ("bút bi", "bút bi"),
        ("sổ tay", "sổ tay"),
        ("laptop", "laptop"),
        ("điện thoại", "điện thoại"),
    ]
    for key, val in keyword_map:
        if key in text:
            return val
    return None


def _fallback_chat_answer(items: list[dict]) -> str:
    if items:
        lines = []
        for item in items:
            p = item["product"]
            lines.append(f"- {p.get('name')} - {format_vnd(p.get('price'))} VND")
        return "Mình gợi ý cho bạn một vài sản phẩm phù hợp:\n" + "\n".join(lines)
    return "Hiện mình chưa tìm thấy sản phẩm phù hợp. Bạn thử nêu rõ thêm ngân sách hoặc loại sản phẩm nhé."


def generate_chatbot_answer_with_llm(
    *,
    user_message: str,
    recommended_items: list[dict],
    category: str | None,
    budget_min: float | None,
    budget_max: float | None,
) -> tuple[str, bool]:
    if not recommended_items:
        return _fallback_chat_answer(recommended_items), False
    if not LLM_ENABLED or not LLM_API_KEY:
        return _fallback_chat_answer(recommended_items), False

    products_text = "\n".join(
        [
            f"- id={it['product_id']}; name={it['product'].get('name')}; price={format_vnd(it['product'].get('price'))}; "
            f"reason={it.get('reason', '')}"
            for it in recommended_items
        ]
    )
    budget_hint = f"min={format_vnd(budget_min)}" if budget_min is not None else "min=none"
    budget_hint += f", max={format_vnd(budget_max)}" if budget_max is not None else ", max=none"
    cat_hint = category or "none"

    system_prompt = (
        "Bạn là trợ lý mua sắm tiếng Việt cho hệ e-commerce. "
        "Nhiệm vụ: trả lời ngắn gọn, thân thiện, chỉ dựa trên danh sách sản phẩm được cung cấp, "
        "không bịa sản phẩm ngoài danh sách. Nếu không có sản phẩm phù hợp thì nói rõ và hỏi thêm nhu cầu."
    )
    user_prompt = (
        f"Tin nhắn người dùng: {user_message}\n"
        f"Category nhận diện: {cat_hint}\n"
        f"Ràng buộc ngân sách: {budget_hint}\n"
        "Danh sách sản phẩm candidate:\n"
        f"{products_text}\n"
        "Hãy trả lời 3-6 câu, có thể gợi ý top sản phẩm phù hợp nhất."
    )

    url = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 280,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=LLM_TIMEOUT_SEC)
        if resp.status_code >= 400:
            logger.warning("LLM call failed status=%s body=%s", resp.status_code, resp.text[:400])
            return _fallback_chat_answer(recommended_items), False
        data = resp.json()
        content = (
            ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        ).strip()
        if not content:
            return _fallback_chat_answer(recommended_items), False
        return content, True
    except requests.RequestException as exc:
        logger.warning("LLM request exception: %s", exc)
        return _fallback_chat_answer(recommended_items), False


def _normalize_positive_scores(scores: dict[int, float]) -> dict[int, float]:
    positive = {k: float(v) for k, v in scores.items() if float(v) > 0.0}
    if not positive:
        return {}
    max_val = max(positive.values())
    if max_val <= 0:
        return {}
    return {k: (v / max_val) for k, v in positive.items()}


def build_rag_scores(
    *,
    user_id: int,
    products: list[dict],
    limit: int,
    query: str | None = None,
    category: str | None = None,
    budget: float | None = None,
) -> dict[int, float]:
    product_map = {int(p["id"]): p for p in products if "id" in p}
    rag_scores: dict[int, float] = {}

    graph_rag_items = graph_store.rag_retrieve(user_id=user_id, limit=max(limit * 4, 20))
    for item in graph_rag_items:
        pid = int(item["product_id"])
        if pid not in product_map:
            continue
        rag_scores[pid] = rag_scores.get(pid, 0.0) + float(item.get("score", 0.0))

    if query and query.strip():
        vector_items = vector_store.search(
            query=query,
            products=products,
            top_k=max(limit * 4, 20),
            category=category,
            budget=budget,
        )
        for item in vector_items:
            rag_scores[item.product_id] = rag_scores.get(item.product_id, 0.0) + float(item.score)

    return rag_scores


def build_recommendations(
    *,
    db: Session,
    user_id: int,
    limit: int,
    query: str | None = None,
    category: str | None = None,
) -> list[dict]:
    products = fetch_products(search=query, category=category)
    product_map = {int(p["id"]): p for p in products if "id" in p}

    user_events = db.scalars(
        select(BehaviorEvent)
        .where(BehaviorEvent.user_id == user_id)
        .order_by(desc(BehaviorEvent.timestamp))
        .limit(200)
    ).all()

    score: dict[int, float] = {}
    reasons: dict[int, list[str]] = {}

    action_weight = {
        "view": 1.0,
        "click": 1.8,
        "add_to_cart": 3.0,
        "purchase": 4.0,
        "search": 1.2,
        "wishlist": 2.2,
        "remove_from_cart": -1.0,
        "chat": 0.8,
    }

    category_bias: dict[str, float] = {}
    recent_product_ids: set[int] = set()
    for idx, event in enumerate(user_events):
        if event.product_id:
            recent_product_ids.add(event.product_id)
        if not event.product_id or event.product_id not in product_map:
            continue

        recency_factor = 1.0 / (idx + 1)
        w = action_weight.get(event.action, 0.8)
        score[event.product_id] = score.get(event.product_id, 0) + (w * recency_factor)

        prod_category = ((product_map[event.product_id].get("category") or {}).get("slug") or "").strip()
        if prod_category:
            category_bias[prod_category] = category_bias.get(prod_category, 0) + (w * recency_factor)

    trending_events = db.scalars(
        select(BehaviorEvent).where(BehaviorEvent.action.in_(["click", "add_to_cart", "purchase"])).limit(2000)
    ).all()
    trending_score: dict[int, float] = {}
    for event in trending_events:
        if event.product_id:
            trending_score[event.product_id] = trending_score.get(event.product_id, 0) + 1.0

    model_scores_raw = sequence_recommender.predict_scores(db, BehaviorEvent, user_id)
    graph_scores_raw = graph_store.recommend(user_id=user_id, limit=max(limit * 4, 20))
    rag_scores_raw = build_rag_scores(
        user_id=user_id,
        products=products,
        limit=limit,
        query=query,
        category=category,
    )

    model_scores = _normalize_positive_scores(model_scores_raw)
    graph_scores = _normalize_positive_scores(graph_scores_raw)
    rag_scores = _normalize_positive_scores(rag_scores_raw)

    for product_id, product in product_map.items():
        product_category = ((product.get("category") or {}).get("slug") or "").strip()
        score.setdefault(product_id, 0.0)

        if product_category in category_bias:
            bonus = category_bias[product_category] * 0.6
            score[product_id] += bonus
            reasons.setdefault(product_id, []).append(f"hợp nhóm {product_category}")

        trend_bonus = trending_score.get(product_id, 0.0) * 0.08
        if trend_bonus > 0:
            score[product_id] += trend_bonus

        if query:
            name_l = str(product.get("name", "")).lower()
            query_l = query.lower().strip()
            q_tokens = [t for t in re.findall(r"\w+", query_l) if len(t) >= 3]
            if query_l and query_l in name_l:
                score[product_id] += 2.0
                reasons.setdefault(product_id, []).append("khớp cụm từ tìm kiếm")
            elif q_tokens and any(tok in name_l for tok in q_tokens):
                score[product_id] += 1.2
                reasons.setdefault(product_id, []).append("khớp từ khóa tìm kiếm")

        m_score = model_scores.get(product_id)
        if m_score is not None:
            score[product_id] += m_score * MODEL_WEIGHT
            reasons.setdefault(product_id, []).append(f"model ({MODEL_WEIGHT}x)")

        g_score = graph_scores.get(product_id)
        if g_score is not None:
            score[product_id] += g_score * GRAPH_WEIGHT
            reasons.setdefault(product_id, []).append(f"graph ({GRAPH_WEIGHT}x)")

        r_score = rag_scores.get(product_id)
        if r_score is not None:
            score[product_id] += r_score * RAG_WEIGHT
            reasons.setdefault(product_id, []).append(f"rag ({RAG_WEIGHT}x)")

        if product_id in recent_product_ids:
            score[product_id] -= 0.5

    sorted_ids = sorted(score.keys(), key=lambda pid: score[pid], reverse=True)
    top_ids = [pid for pid in sorted_ids if pid in product_map][:limit]

    items: list[dict] = []
    for pid in top_ids:
        product = product_map[pid]
        reason_text = ", ".join(reasons.get(pid, [])) or "phù hợp hành vi gần đây"
        items.append(
            {
                "product_id": pid,
                "score": round(float(score[pid]), 4),
                "reason": reason_text,
                "product": {
                    "name": product.get("name"),
                    "price": product.get("price"),
                    "category": (product.get("category") or {}).get("slug"),
                },
            }
        )
    return items


app = FastAPI(title="ai-service", version="1.0.0")
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.perf_counter()
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    latency_ms = _to_ms(start_time)
    logger.info(
        "request_id=%s method=%s path=%s status=%s latency_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
    )
    return response


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    sequence_recommender._load()
    try:
        graph_store.ensure_schema()
    except Exception:
        pass


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/ai/events")
def track_event(
    payload: BehaviorEventCreate,
    claims: dict = Depends(get_required_claims),
    db: Session = Depends(get_db),
):
    action = payload.action.strip().lower()
    if action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail="Unsupported action")

    own_user_id = int(claims["sub"])
    target_user_id = int(payload.user_id) if payload.user_id is not None else own_user_id
    ensure_can_access_user(claims, target_user_id)

    event = BehaviorEvent(
        user_id=target_user_id,
        product_id=payload.product_id,
        action=action,
        query=payload.query,
        timestamp=payload.timestamp or datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    graph_synced = False
    try:
        graph_store.upsert_event(
            user_id=event.user_id,
            product_id=event.product_id,
            action=event.action,
            timestamp=event.timestamp,
        )
        graph_synced = True
    except Exception:
        graph_synced = False

    return {
        "id": event.id,
        "user_id": event.user_id,
        "product_id": event.product_id,
        "action": event.action,
        "timestamp": event.timestamp.isoformat(),
        "graph_synced": graph_synced,
    }


@app.post("/ai/graph/rebuild")
def rebuild_graph(
    payload: GraphRebuildRequest,
    claims: dict = Depends(get_required_claims),
    db: Session = Depends(get_db),
):
    ensure_staff_or_admin(claims)
    if not graph_store.ready:
        raise HTTPException(status_code=503, detail="Neo4j is not configured or unavailable")

    events = db.scalars(select(BehaviorEvent).order_by(BehaviorEvent.id.asc())).all()
    products = fetch_all_products_for_graph()
    try:
        summary = graph_store.rebuild_from_events(events=events, products=products, reset=payload.reset)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Neo4j rebuild failed: {exc}") from exc
    return {
        "events_processed": summary.get("events", 0),
        "products_synced": summary.get("products", 0),
        "viewed_after_edges": summary.get("viewed_after", 0),
        "bought_with_edges": summary.get("bought_with", 0),
        "similar_edges": summary.get("similar", 0),
        "graph_ready": graph_store.ping(),
    }


@app.get("/ai/graph/recommend")
def graph_recommend(
    user_id: int | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=30),
    claims: dict = Depends(get_required_claims),
):
    own_user_id = int(claims["sub"])
    target_user_id = int(user_id) if user_id is not None else own_user_id
    ensure_can_access_user(claims, target_user_id)
    if not graph_store.ready:
        raise HTTPException(status_code=503, detail="Neo4j is not configured or unavailable")

    rec = graph_store.recommend(user_id=target_user_id, limit=limit)
    items = [{"product_id": pid, "score": round(score, 4)} for pid, score in rec.items()]
    return {"user_id": target_user_id, "count": len(items), "items": items}


@app.get("/ai/recommend")
def recommend(
    request: Request,
    user_id: int | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=30),
    query: str | None = Query(default=None),
    category: str | None = Query(default=None),
    claims: dict = Depends(get_required_claims),
    db: Session = Depends(get_db),
):
    start_time = time.perf_counter()
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    role = get_role(claims)
    own_user_id = int(claims["sub"])
    target_user_id = int(user_id) if user_id is not None else own_user_id
    ensure_can_access_user(claims, target_user_id)

    try:
        items = build_recommendations(db=db, user_id=target_user_id, limit=limit, query=query, category=category)

        if items:
            now = datetime.now(timezone.utc)
            db.add_all(
                [
                    BehaviorEvent(
                        user_id=target_user_id,
                        product_id=int(it["product_id"]),
                        action="recommend_impression",
                        query=query,
                        timestamp=now,
                    )
                    for it in items
                ]
            )

        _log_endpoint_metric(
            db,
            request_id=request_id,
            endpoint="/ai/recommend",
            user_id=target_user_id,
            role=role,
            latency_ms=_to_ms(start_time),
            status_code=200,
            recommended_count=len(items),
        )
        db.commit()
    except HTTPException as exc:
        db.rollback()
        try:
            _log_endpoint_metric(
                db,
                request_id=request_id,
                endpoint="/ai/recommend",
                user_id=target_user_id,
                role=role,
                latency_ms=_to_ms(start_time),
                status_code=exc.status_code,
                recommended_count=0,
            )
            db.commit()
        except Exception:
            db.rollback()
        raise
    except Exception:
        db.rollback()
        try:
            _log_endpoint_metric(
                db,
                request_id=request_id,
                endpoint="/ai/recommend",
                user_id=target_user_id,
                role=role,
                latency_ms=_to_ms(start_time),
                status_code=500,
                recommended_count=0,
            )
            db.commit()
        except Exception:
            db.rollback()
        raise

    return {
        "user_id": target_user_id,
        "count": len(items),
        "items": items,
        "request_id": request_id,
    }


@app.post("/ai/chatbot")
def chatbot(
    request: Request,
    payload: ChatbotRequest,
    claims: dict = Depends(get_required_claims),
    db: Session = Depends(get_db),
):
    start_time = time.perf_counter()
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    role = get_role(claims)
    own_user_id = int(claims["sub"])
    target_user_id = int(payload.user_id) if payload.user_id is not None else own_user_id
    ensure_can_access_user(claims, target_user_id)

    try:
        category = infer_category(payload.message)
        search_keyword = infer_search_keyword(payload.message) or payload.message
        budget_min, budget_max = parse_budget_constraint(payload.message)
        recommendations = build_recommendations(
            db=db,
            user_id=target_user_id,
            limit=6,
            query=search_keyword,
            category=category,
        )
        rag_items = graph_store.rag_retrieve(user_id=target_user_id, limit=12)
        products_for_rag = fetch_all_products_for_graph()
        product_by_id = {int(p["id"]): p for p in products_for_rag if "id" in p}
        vector_items = vector_store.search(
            query=payload.message,
            products=products_for_rag,
            top_k=12,
            category=category,
            budget=budget_max,
        )

        rag_enriched: list[dict] = []
        for it in rag_items:
            pid = int(it["product_id"])
            product = product_by_id.get(pid)
            if not product:
                continue
            if category:
                c = ((product.get("category") or {}).get("slug") or "").strip()
                if c != category:
                    continue
            rag_enriched.append(
                {
                    "product_id": pid,
                    "score": round(float(it["score"]), 4),
                    "reason": "; ".join(it.get("evidence") or []) or "retrieved from KB_Graph",
                    "product": {
                        "name": product.get("name"),
                        "price": product.get("price"),
                        "category": (product.get("category") or {}).get("slug"),
                    },
                    "source_products": it.get("source_products") or [],
                }
            )

        vector_enriched: list[dict] = []
        for it in vector_items:
            p = product_by_id.get(int(it.product_id))
            if not p:
                continue
            vector_enriched.append(
                {
                    "product_id": int(it.product_id),
                    "score": round(float(it.score) * VECTOR_WEIGHT, 4),
                    "reason": it.reason,
                    "product": {
                        "name": p.get("name"),
                        "price": p.get("price"),
                        "category": (p.get("category") or {}).get("slug"),
                    },
                }
            )

        filtered: list[dict] = []
        merged = vector_enriched + rag_enriched + recommendations
        deduped_by_id: dict[int, dict] = {}
        for rec in merged:
            pid = int(rec["product_id"])
            current = deduped_by_id.get(pid)
            if current is None or float(rec.get("score", 0.0)) > float(current.get("score", 0.0)):
                deduped_by_id[pid] = rec
        deduped = sorted(deduped_by_id.values(), key=lambda x: float(x.get("score", 0.0)), reverse=True)
        seen = {int(x["product_id"]) for x in deduped}

        for rec in deduped:
            price = rec["product"].get("price")
            if not _is_price_in_budget(price, budget_min, budget_max):
                continue
            filtered.append(rec)

        if not filtered:
            direct = fetch_products(search=search_keyword, category=category)
            for p in direct:
                pid = int(p["id"])
                if pid in seen:
                    continue
                price = p.get("price")
                if not _is_price_in_budget(price, budget_min, budget_max):
                    continue
                filtered.append(
                    {
                        "product_id": pid,
                        "score": 0.99,
                        "reason": "khớp truy vấn trực tiếp",
                        "product": {
                            "name": p.get("name"),
                            "price": p.get("price"),
                            "category": (p.get("category") or {}).get("slug"),
                        },
                    }
                )

        final_items = filtered[:3] if filtered else deduped[:3]
        answer, llm_used = generate_chatbot_answer_with_llm(
            user_message=payload.message,
            recommended_items=final_items,
            category=category,
            budget_min=budget_min,
            budget_max=budget_max,
        )

        chat_event = BehaviorEvent(
            user_id=target_user_id,
            product_id=final_items[0]["product_id"] if final_items else None,
            action="chat",
            query=payload.message,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(chat_event)

        chatbot_success = 1 if final_items and answer else 0
        _log_endpoint_metric(
            db,
            request_id=request_id,
            endpoint="/ai/chatbot",
            user_id=target_user_id,
            role=role,
            latency_ms=_to_ms(start_time),
            status_code=200,
            recommended_count=len(final_items),
            chatbot_success=chatbot_success,
        )
        db.commit()

        return {
            "user_id": target_user_id,
            "answer": answer,
            "recommended_products": final_items,
            "follow_up_questions": [
                "Bạn muốn mức giá tối đa khoảng bao nhiêu?",
                "Bạn ưu tiên thương hiệu hoặc danh mục nào?",
                "Bạn cần dùng cho mục đích học tập, làm việc hay giải trí?",
            ],
            "detected": {
                "category": category,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "search_keyword": search_keyword,
            },
            "rag": {
                "retrieved_count": len(rag_enriched),
                "used_graph": len(rag_enriched) > 0,
                "vector_retrieved_count": len(vector_enriched),
                "vector_backend": "faiss" if vector_store.faiss_enabled else "numpy_fallback",
            },
            "llm": {
                "enabled": LLM_ENABLED,
                "used": llm_used,
                "model": LLM_MODEL if llm_used else None,
            },
            "request_id": request_id,
        }
    except HTTPException as exc:
        db.rollback()
        try:
            _log_endpoint_metric(
                db,
                request_id=request_id,
                endpoint="/ai/chatbot",
                user_id=target_user_id,
                role=role,
                latency_ms=_to_ms(start_time),
                status_code=exc.status_code,
                recommended_count=0,
                chatbot_success=0,
            )
            db.commit()
        except Exception:
            db.rollback()
        raise
    except Exception:
        db.rollback()
        try:
            _log_endpoint_metric(
                db,
                request_id=request_id,
                endpoint="/ai/chatbot",
                user_id=target_user_id,
                role=role,
                latency_ms=_to_ms(start_time),
                status_code=500,
                recommended_count=0,
                chatbot_success=0,
            )
            db.commit()
        except Exception:
            db.rollback()
        raise


@app.get("/ai/admin/metrics")
def admin_metrics(
    days: int = Query(default=7, ge=1, le=30),
    claims: dict = Depends(get_required_claims),
    db: Session = Depends(get_db),
):
    ensure_staff_or_admin(claims)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    endpoint_rows = db.scalars(
        select(EndpointMetric).where(EndpointMetric.created_at >= since).order_by(EndpointMetric.created_at.desc())
    ).all()
    rec_rows = [r for r in endpoint_rows if r.endpoint == "/ai/recommend"]
    chat_rows = [r for r in endpoint_rows if r.endpoint == "/ai/chatbot"]
    rec_ok = [r for r in rec_rows if r.status_code == 200]
    chat_ok = [r for r in chat_rows if r.status_code == 200]

    rec_lat = [int(r.latency_ms) for r in rec_ok]
    chat_lat = [int(r.latency_ms) for r in chat_ok]

    recommend_impressions = db.query(BehaviorEvent).filter(
        BehaviorEvent.timestamp >= since,
        BehaviorEvent.action == "recommend_impression",
    ).count()
    recommendation_interactions = db.query(BehaviorEvent).filter(
        BehaviorEvent.timestamp >= since,
        BehaviorEvent.action.in_(["click", "add_to_cart", "purchase"]),
    ).count()

    chatbot_success_count = sum(int(r.chatbot_success or 0) for r in chat_ok)
    chatbot_success_rate = (chatbot_success_count / len(chat_ok)) if chat_ok else 0.0
    recommendation_ctr = (
        min(1.0, recommendation_interactions / recommend_impressions) if recommend_impressions > 0 else 0.0
    )

    return {
        "window_days": days,
        "since": since.isoformat(),
        "recommendation": {
            "requests": len(rec_rows),
            "success_requests": len(rec_ok),
            "latency_ms": {
                "avg": round((sum(rec_lat) / len(rec_lat)) if rec_lat else 0.0, 2),
                "p95": round(_p95(rec_lat), 2),
            },
            "impressions": recommend_impressions,
            "interactions": recommendation_interactions,
            "ctr": round(recommendation_ctr, 4),
        },
        "chatbot": {
            "requests": len(chat_rows),
            "success_requests": len(chat_ok),
            "latency_ms": {
                "avg": round((sum(chat_lat) / len(chat_lat)) if chat_lat else 0.0, 2),
                "p95": round(_p95(chat_lat), 2),
            },
            "success_rate": round(chatbot_success_rate, 4),
        },
        "graph": {
            "enabled": graph_store.ready,
            "healthy": graph_store.ping() if graph_store.ready else False,
        },
    }


@app.get("/ai/admin/recent-requests")
def admin_recent_requests(
    limit: int = Query(default=50, ge=1, le=200),
    claims: dict = Depends(get_required_claims),
    db: Session = Depends(get_db),
):
    ensure_staff_or_admin(claims)
    rows = db.scalars(select(EndpointMetric).order_by(EndpointMetric.created_at.desc()).limit(limit)).all()
    return {
        "count": len(rows),
        "items": [
            {
                "request_id": r.request_id,
                "endpoint": r.endpoint,
                "user_id": r.user_id,
                "role": r.role,
                "latency_ms": r.latency_ms,
                "status_code": r.status_code,
                "recommended_count": r.recommended_count,
                "chatbot_success": r.chatbot_success,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }

