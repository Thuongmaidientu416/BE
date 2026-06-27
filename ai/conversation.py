"""
WanderHUB AI — Layer 4: Conversation Layer
Builds prompts with real data and calls the LLM (Groq API) server-side.
"""

from __future__ import annotations
import json
import httpx

from config import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL


SYSTEM_PROMPT_TEMPLATE = """Bạn là WanderBot — trợ lý AI thông minh của WanderHUB, nền tảng gợi ý trải nghiệm đô thị tại TP.HCM.

VAI TRÒ CỦA BẠN (Layer 4 — AI Conversation Layer):
- Diễn giải các đề xuất địa điểm một cách tự nhiên, thân thiện
- Trả lời hội thoại theo phong cách Gen Z Sài Gòn: trẻ trung, gần gũi nhưng chuyên nghiệp
- Cá nhân hóa giọng điệu theo bối cảnh người dùng
- Tóm tắt lịch trình rõ ràng, có thời gian và chi phí
- Hỏi follow-up khi thiếu thông tin

QUY TẮC BẮT BUỘC:
- CHỈ sử dụng dữ liệu được cung cấp bởi hệ thống backend
- KHÔNG bịa giá, giờ mở cửa, hoặc tuyến đường
- KHÔNG sáng tác khuyến mãi hay địa điểm không có trong data
- KHÔNG override logic nghiệp vụ từ backend
- Giữ câu trả lời ngắn gọn, hữu ích, thân thiện
- Luôn trả lời bằng tiếng Việt
- Khi gợi ý địa điểm, nêu rõ quận/khu vực, khoảng giá và lý do phù hợp

DỮ LIỆU TỪ HỆ THỐNG BACKEND:
{system_data}"""


# ── Fallback mock responses ──────────────────────────────────────
MOCK_RESPONSES = {
    "chill": "Với mood chill, mình gợi ý bạn bắt đầu từ một quán cafe view đẹp ở Quận 1, sau đó dạo bộ check-in vài điểm hot rồi kết thúc bằng bữa tối nhẹ nhàng. Bạn muốn mình tạo lịch trình chi tiết không? 🌿",
    "date": "Date night ở Sài Gòn thì chuẩn rồi! Mình có thể gợi ý tuyến cafe rooftop → ăn tối ven sông → ngắm city view đêm. Bạn thích khu vực nào? 💫",
    "food": "Foodie tour Sài Gòn thì phải có ốc, bún, và café! Mình sẽ chọn những quán có điểm WanderHUB cao nhất cho bạn. Bạn muốn ăn khu nào? 🍜",
    "default": "Cảm ơn bạn đã liên hệ WanderBot! Mình có thể giúp bạn tạo lịch trình, gợi ý địa điểm, hoặc giải đáp thông tin dịch vụ. Bạn muốn khám phá gì hôm nay? 🗺️",
}


async def generate_response(
    user_message: str,
    message_history: list[dict],
    system_data: dict,
    groq_key: str | None = None,
) -> tuple[str, str]:
    """
    Layer 4 — Generate AI response using LLM.

    Args:
        user_message: Current user message
        message_history: Previous messages [{"from": "user"|"ai", "text": "..."}]
        system_data: Backend data to inject into prompt (user context, rules, recommendations)
        groq_key: Optional override key (from user) or falls back to server env key

    Returns:
        (reply_text, source) where source is "ai", "mock", or "error"
    """
    api_key = groq_key or GROQ_API_KEY

    if not api_key:
        # No API key — use mock fallback
        reply = _mock_reply(user_message)
        return reply, "mock"

    # Build system prompt with real data
    system_content = SYSTEM_PROMPT_TEMPLATE.format(
        system_data=json.dumps(system_data, ensure_ascii=False, indent=2)
    )

    # Build message list
    messages = [{"role": "system", "content": system_content}]
    for msg in message_history[-20:]:  # Keep last 20 messages for context
        role = "assistant" if msg.get("from") == "ai" else "user"
        messages.append({"role": role, "content": msg.get("text", "")})
    messages.append({"role": "user", "content": user_message})

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "temperature": 0.6,
                    "max_tokens": 1024,
                },
            )

        if response.status_code != 200:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
            return f"Lỗi kết nối AI: {error_msg}", "error"

        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        return reply, "ai"

    except httpx.TimeoutException:
        return "Hệ thống AI đang bận, vui lòng thử lại sau ít giây. ⏳", "error"
    except Exception as exc:
        return f"Lỗi hệ thống: {str(exc)}", "error"


def _mock_reply(message: str) -> str:
    """Generate a mock reply based on keyword matching."""
    lower = message.lower()

    if any(kw in lower for kw in ["chill", "thư giãn", "relax"]):
        return MOCK_RESPONSES["chill"]
    if any(kw in lower for kw in ["date", "hẹn hò", "lãng mạn"]):
        return MOCK_RESPONSES["date"]
    if any(kw in lower for kw in ["ăn", "food", "quán", "ốc", "bún"]):
        return MOCK_RESPONSES["food"]

    return MOCK_RESPONSES["default"]


def build_chat_system_data(
    conn,
    user_message: str,
    moods: list[str],
    district: str = "Quận 1",
) -> dict:
    """Build system data for chat context by querying relevant providers."""
    import sqlite3

    # Fetch a few top providers matching detected mood
    mood_placeholders = ",".join("?" for _ in moods)
    query = f"""
        SELECT DISTINCT
            v.provider_name,
            v.district_name,
            v.category_name,
            v.role_name,
            v.price_min_vnd,
            v.price_max_vnd,
            v.wanderhub_score,
            v.description,
            v.ai_base_score
        FROM v_recommendation_base v
        LEFT JOIN provider_moods pm ON pm.provider_id = v.provider_id
        LEFT JOIN moods m ON m.id = pm.mood_id
        WHERE m.code IN ({mood_placeholders})
        ORDER BY v.ai_base_score DESC
        LIMIT 8
    """
    rows = conn.execute(query, moods).fetchall()
    relevant_providers = [dict(r) for r in rows]

    # Fetch district stats
    district_stats = dict(conn.execute(
        "SELECT * FROM v_district_summary WHERE district_name = ?",
        (district,),
    ).fetchone() or {})

    return {
        "current_district": district,
        "detected_moods": moods,
        "relevant_providers": relevant_providers,
        "district_stats": district_stats,
        "total_providers": conn.execute("SELECT COUNT(*) FROM providers").fetchone()[0],
    }
