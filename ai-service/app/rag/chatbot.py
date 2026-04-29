"""RAG chatbot: retrieve products with FAISS, generate a response.

If `OPENAI_API_KEY` is set the LLM is GPT-4o-mini; otherwise we fall back
to a deterministic templated answer so the endpoint still works in
demos without API access."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from .. import config
from .index import faiss_index

log = logging.getLogger("ai-service.rag.chatbot")


SYSTEM_PROMPT = (
    "Bạn là trợ lý AI cho cửa hàng e-commerce gồm sách, điện tử, thời trang. "
    "Trả lời ngắn gọn (3–5 câu), lịch sự, dùng tiếng Việt. "
    "Chỉ giới thiệu sản phẩm trong danh sách context — không bịa thông tin."
)


def _format_context(retrieved: List[Dict[str, Any]]) -> str:
    lines = []
    for r in retrieved:
        lines.append(
            f"- [{r['product_type']}] {r['name']} (ID {r['product_id']}, "
            f"giá {r['price']:.0f}đ, độ tương đồng {r['score']:.2f})"
        )
    return "\n".join(lines)


def _template_response(query: str, retrieved: List[Dict[str, Any]]) -> str:
    if not retrieved:
        return "Xin lỗi, hiện chưa có sản phẩm phù hợp với truy vấn của bạn."
    top = retrieved[0]
    others = retrieved[1:3]
    parts = [
        f"Theo nhu cầu \"{query}\", mình đề xuất **{top['name']}** "
        f"(giá {top['price']:.0f}đ, ID {top['product_id']})."
    ]
    if others:
        parts.append("Bạn cũng có thể tham khảo: " + ", ".join(o["name"] for o in others) + ".")
    return " ".join(parts)


def _llm_response(query: str, retrieved: List[Dict[str, Any]]) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        log.warning("openai SDK missing; falling back to template")
        return _template_response(query, retrieved)
    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        completion = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Câu hỏi của khách: {query}\n\n"
                        f"Sản phẩm liên quan (từ FAISS):\n{_format_context(retrieved)}\n\n"
                        "Hãy trả lời tự nhiên, gợi ý 1-3 sản phẩm phù hợp nhất."
                    ),
                },
            ],
            temperature=0.4,
            max_tokens=400,
        )
        return completion.choices[0].message.content.strip()
    except Exception as exc:
        log.warning("LLM call failed (%s); falling back to template", exc)
        return _template_response(query, retrieved)


def answer(query: str, top_k: int = 5) -> Dict[str, Any]:
    retrieved = faiss_index.search(query, top_k=top_k)
    use_llm = bool(config.OPENAI_API_KEY)
    response_text = _llm_response(query, retrieved) if use_llm else _template_response(query, retrieved)
    return {
        "query": query,
        "response": response_text,
        "retrieved": retrieved,
        "llm_used": use_llm,
    }
