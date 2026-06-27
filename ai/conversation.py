"""
WanderHUB AI — Layer 4: Conversation Layer
Builds prompts with real data and calls the LLM (Groq API) server-side.
"""

from __future__ import annotations
import json
import httpx

from config import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL


SYSTEM_PROMPT_TEMPLATE = """Bạn là WanderBot — trợ lý AI thông minh hỗ trợ chăm sóc khách hàng chuyên nghiệp của WanderHUB, nền tảng gợi ý trải nghiệm đô thị tại TP.HCM.

VAI TRÒ CỦA BẠN (Layer 4 — AI Conversation Layer):
- Giải đáp thắc mắc và hỗ trợ khách hàng về các vấn đề phát sinh (chính sách, dịch vụ, CSKH).
- Cung cấp thông tin chi tiết và hữu ích về các địa điểm (giới thiệu địa điểm, món ăn, khoảng giá, địa chỉ) từ dữ liệu hệ thống dựa trên nhu cầu tìm kiếm của người dùng.
- KHÔNG gợi ý hoặc tự tạo lịch trình/tuyến đường mẫu (itinerary/route). Nếu người dùng muốn lên lịch trình, hãy hướng dẫn họ sử dụng tính năng "Lên lịch trình" chính trên website WanderHUB.
- Trả lời hội thoại theo phong cách Gen Z Sài Gòn: trẻ trung, gần gũi nhưng chuyên nghiệp.

QUY TẮC BẮT BUỘC:
- ƯU TIÊN DỮ LIỆU HỆ THỐNG: Đối với thông tin các gói dịch vụ, chính sách CSKH của WanderHUB hoặc các địa điểm có sẵn trong dữ liệu backend bên dưới, bạn BẮT BUỘC phải dùng thông tin chính xác được cung cấp. Không tự ý thay đổi giá cả hoặc quyền lợi gói của WanderHUB.
- LINH HOẠT TỰ DO DÙNG KIẾN THỨC INTERNET: Nếu người dùng hỏi/tìm kiếm các địa điểm check-in, vui chơi, ăn uống nổi tiếng tại Sài Gòn/Việt Nam (ví dụ: Landmark 81, Dinh Độc Lập, Nhà thờ Đức Bà, v.v.) mà không có trong dữ liệu backend được cung cấp, bạn hãy LINH HOẠT sử dụng kiến thức tích hợp của mình (internet) để giới thiệu chi tiết, đầy đủ và thân thiện cho khách hàng. Tuyệt đối KHÔNG trả lời kiểu "tôi không tìm thấy thông tin trong dữ liệu của tôi".
- KHÔNG tạo tuyến đường/lịch trình mẫu cho người dùng.
- Giữ câu trả lời ngắn gọn, hữu ích, tập trung đúng trọng tâm câu hỏi của khách hàng.
- Luôn trả lời bằng tiếng Việt.
- Khi giới thiệu địa điểm, nêu rõ tên, quận/khu vực, khoảng giá và lý do phù hợp.
- CHỈ giới thiệu địa điểm khi người dùng chủ động hỏi/tìm kiếm địa điểm vui chơi, ăn uống, giải trí. Tuyệt đối KHÔNG tự động đính kèm các gợi ý địa điểm ăn uống/vui chơi khi người dùng đang hỏi về các vấn đề CSKH, hỗ trợ kỹ thuật, tài khoản, đặt xe hoặc gói dịch vụ.

DỮ LIỆU TỪ HỆ THỐNG BACKEND:
{system_data}"""


# ── Fallback mock responses ──────────────────────────────────────
MOCK_RESPONSES = {
    "chill": "Với mood chill, mình gợi ý bạn ghé thử một số quán cafe hoặc không gian thoáng đãng tại Quận 1 có điểm đánh giá cao của hệ thống. Bạn có muốn mình giới thiệu các địa điểm chill cụ thể không? 🌿",
    "date": "Để đi hẹn hò, mình gợi ý bạn chọn một số quán ăn lãng mạn hoặc quán nước rooftop view đẹp. Bạn thích tìm quán ở khu vực nào để mình giới thiệu cụ thể nhé? 💫",
    "food": "Đi ăn uống tại Sài Gòn thì tuyệt vời! Hệ thống của mình có rất nhiều quán ăn ngon từ bình dân đến cao cấp. Bạn đang thèm ăn món gì hoặc muốn tìm quán ở quận mấy? 🍜",
    "default": "Cảm ơn bạn đã liên hệ WanderBot! Mình có thể hỗ trợ giải đáp thông tin dịch vụ, giải quyết các vấn đề phát sinh hoặc giới thiệu các địa điểm ăn chơi phù hợp với nhu cầu của bạn. Bạn cần hỗ trợ gì hôm nay? 🗺️",
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

    policies_and_plans = {
        "subscription_plans": [
            {"name": "Gói Basic (Cơ bản)", "price": "Miễn phí", "benefits": "Giới hạn tạo 1 lịch trình mỗi 20 ngày"},
            {"name": "Gói Premium (Cao cấp)", "price": "99.000 VND / tháng", "benefits": "Tạo lịch trình không giới hạn, mở khóa mọi tính năng cao cấp"},
            {"name": "Gói International (Quốc tế)", "price": "299.000 VND / tháng", "benefits": "Tạo lịch trình không giới hạn, hỗ trợ dịch thuật nâng cao cho du khách quốc tế và đối tác"}
        ],
        "policies": {
            "cancellation": "Người dùng có thể hủy đăng ký gói bất kỳ lúc nào tại mục Cài đặt tài khoản. Quyền lợi của gói sẽ được duy trì cho đến hết chu kỳ thanh toán hiện tại.",
            "refund": "Hoàn tiền 100% trong vòng 7 ngày kể từ ngày đăng ký/thanh toán nếu chưa dùng quá 3 lượt tạo lịch trình mới. Để yêu cầu hoàn tiền, liên hệ qua hotline 1900-0905 hoặc email support@wanderhub.vn.",
            "technical_issues": "Nếu gặp lỗi hệ thống hoặc sự cố kỹ thuật, hướng dẫn khách hàng tải lại trang (Ctrl+F5), xóa cache hoặc đăng nhập lại. Nếu không khắc phục được, báo cáo tại mục 'Liên hệ' hoặc gửi email về support@wanderhub.vn kèm ảnh chụp màn hình.",
            "vehicle_booking_issues": "Nếu gặp sự cố về xe đã đặt (xe đến trễ, hỏng xe), liên hệ số điện thoại tài xế trong trang chi tiết đặt xe, hoặc gọi hotline khẩn cấp 1900-0905 để đổi xe khác thay thế.",
            "account_security": "Người dùng tự đổi mật khẩu hoặc cập nhật thông tin trong trang cá nhân (Profile). Nếu quên mật khẩu, chọn 'Quên mật khẩu' ở màn hình đăng nhập hoặc gửi mail hỗ trợ.",
            "local_partners": "Các cơ sở kinh doanh muốn hiển thị ưu tiên/hợp tác quảng cáo có thể đăng ký tại trang 'Đối tác' hoặc gửi email về partner@wanderhub.vn."
        }
    }

    return {
        "current_district": district,
        "detected_moods": moods,
        "relevant_providers": relevant_providers,
        "district_stats": district_stats,
        "total_providers": conn.execute("SELECT COUNT(*) FROM providers").fetchone()[0],
        "wanderhub_policies_and_plans": policies_and_plans
    }
