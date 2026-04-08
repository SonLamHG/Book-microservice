"""
RAG Chat Engine.
Orchestrates: query embedding → KB vector search → customer context → LLM generation.
"""
import logging
from openai import OpenAI
from django.conf import settings

from .models import ChatMessage, CustomerBehaviorSummary
from .knowledge_base import search_kb

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """Bạn là tư vấn viên AI của nhà sách trực tuyến BookStore Việt Nam.
Nhiệm vụ của bạn là tư vấn sách, hỗ trợ khách hàng tìm sách phù hợp, và trả lời câu hỏi về cửa hàng.

Quy tắc:
- Trả lời bằng tiếng Việt, thân thiện và chuyên nghiệp.
- Dựa trên thông tin khách hàng và kiến thức tham khảo bên dưới để đưa ra gợi ý cá nhân hóa.
- Nếu không biết câu trả lời, hãy nói rõ thay vì đoán.
- Gợi ý sách cụ thể khi có thể (tên sách, tác giả, giá).
- Giữ câu trả lời ngắn gọn, dưới 300 từ.

## Thông tin khách hàng
{customer_context}

## Kiến thức tham khảo
{kb_context}
"""


def _build_customer_context(customer_id):
    """Build customer context string from behavior summary."""
    try:
        summary = CustomerBehaviorSummary.objects.get(customer_id=customer_id)
    except CustomerBehaviorSummary.DoesNotExist:
        return "Khách hàng mới, chưa có lịch sử mua hàng."

    parts = [f"- Phân khúc: {summary.get_segment_display()}"]
    parts.append(f"- Tổng đơn hàng: {summary.total_orders}")
    parts.append(f"- Tổng chi tiêu: {summary.total_spent:,.0f} VND")
    parts.append(f"- Chi tiêu trung bình/đơn: {summary.avg_order_value:,.0f} VND")

    if summary.favorite_categories:
        cats = ', '.join(c.get('name', '') for c in summary.favorite_categories[:3])
        parts.append(f"- Thể loại yêu thích: {cats}")

    if summary.favorite_authors:
        authors = ', '.join(a.get('author', '') for a in summary.favorite_authors[:3])
        parts.append(f"- Tác giả yêu thích: {authors}")

    if summary.avg_rating_given:
        parts.append(f"- Điểm đánh giá trung bình cho sách: {summary.avg_rating_given}/5")

    if summary.purchase_frequency_days:
        parts.append(f"- Tần suất mua: mỗi {summary.purchase_frequency_days:.0f} ngày")

    return '\n'.join(parts)


def _build_kb_context(query, top_k=3):
    """Search KB and format results as context string."""
    results = search_kb(query, top_k=top_k)
    if not results:
        return "Không tìm thấy thông tin liên quan trong cơ sở kiến thức."

    parts = []
    for r in results:
        parts.append(f"### {r['title']} (nguồn: {r['source']}, độ liên quan: {r['similarity']})")
        parts.append(r['content'])
        parts.append("")

    return '\n'.join(parts)


def _get_chat_history(session, max_messages=10):
    """Get recent chat history formatted for LLM."""
    messages = ChatMessage.objects.filter(session=session).order_by('-created_at')[:max_messages]
    messages = list(reversed(messages))

    history = []
    for msg in messages:
        history.append({
            'role': msg.role,
            'content': msg.content,
        })
    return history


def generate_chat_response(session, user_message):
    """
    Main RAG pipeline:
    1. Search KB with user query
    2. Build customer context
    3. Assemble prompt with history
    4. Call OpenAI API
    5. Return response + context used

    Returns: (response_text, context_dict)
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')

    if not api_key:
        return (
            "Hệ thống chat tư vấn chưa được cấu hình API key. "
            "Vui lòng liên hệ quản trị viên.",
            None,
        )

    # Step 1: Search KB
    kb_context = _build_kb_context(user_message)
    kb_results = search_kb(user_message, top_k=3)

    # Step 2: Build customer context
    customer_context = _build_customer_context(session.customer_id)

    # Step 3: Build system prompt
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        customer_context=customer_context,
        kb_context=kb_context,
    )

    # Step 4: Assemble messages with history
    chat_history = _get_chat_history(session)
    messages = [{'role': 'system', 'content': system_prompt}]
    messages.extend(chat_history)
    messages.append({'role': 'user', 'content': user_message})

    # Step 5: Call OpenAI API
    try:
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )
        response_text = completion.choices[0].message.content
    except Exception as e:
        logger.error("OpenAI API error: %s", e)
        raise

    # Build context metadata for logging
    context_used = {
        'kb_results': [
            {'title': r['title'], 'source': r['source'], 'similarity': r['similarity']}
            for r in kb_results
        ],
        'customer_segment': None,
    }
    try:
        summary = CustomerBehaviorSummary.objects.get(customer_id=session.customer_id)
        context_used['customer_segment'] = summary.segment
    except CustomerBehaviorSummary.DoesNotExist:
        pass

    return response_text, context_used
