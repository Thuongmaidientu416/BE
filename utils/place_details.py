"""
WanderHUB Backend — Place detail enrichment from OpenStreetMap raw tags.

Surfaces *truthful* facts already stored in providers.raw_tags_json so the
itinerary detail can describe each stop richly:
  - cuisine     → Vietnamese label + dishes typical of that cuisine ("Món nên thử")
  - amenities   → wifi / máy lạnh / chỗ ngồi ngoài trời / đồ chay / ... (highlight chips)
  - address / opening_hours / phone / website  (passed through)

We never invent facts about a specific venue. The dishes listed are the
well-known dishes *of that cuisine type* (a true statement about the cuisine),
surfaced as suggestions — not a claim that this exact shop's bestseller is X.
"""

from __future__ import annotations

import json

# cuisine code → (Vietnamese label, dishes typical of the cuisine)
CUISINE_VI: dict[str, tuple[str, list[str]]] = {
    "vietnamese": ("Món Việt", ["Phở", "Cơm tấm", "Bún thịt nướng", "Gỏi cuốn"]),
    "coffee_shop": ("Cà phê & đồ uống", ["Cà phê sữa đá", "Bạc xỉu", "Cold brew", "Trà đào"]),
    "coffee": ("Cà phê & đồ uống", ["Cà phê sữa đá", "Bạc xỉu", "Cold brew"]),
    "cafe": ("Cà phê & đồ uống", ["Cà phê sữa đá", "Bạc xỉu", "Trà trái cây"]),
    "tea": ("Trà & đồ uống", ["Trà đào", "Trà sen", "Trà trái cây"]),
    "bubble_tea": ("Trà sữa", ["Trà sữa trân châu", "Sữa tươi trân châu đường đen", "Trà trái cây"]),
    "burger": ("Burger & món Âu", ["Beef burger", "Cheeseburger", "Khoai tây chiên"]),
    "chicken": ("Gà rán", ["Gà rán giòn", "Gà sốt cay", "Combo gà + nước"]),
    "fried_chicken": ("Gà rán", ["Gà rán giòn", "Gà sốt cay", "Khoai tây chiên"]),
    "pizza": ("Pizza Ý", ["Pizza Margherita", "Pizza hải sản", "Pizza phô mai"]),
    "italian": ("Món Ý", ["Pizza", "Pasta sốt kem", "Spaghetti"]),
    "indian": ("Ẩm thực Ấn Độ", ["Cà ri gà", "Bánh naan", "Cơm biryani"]),
    "chinese": ("Món Hoa", ["Dimsum", "Mì xào", "Cơm chiên Dương Châu"]),
    "korean": ("Món Hàn", ["BBQ thịt nướng", "Kimchi", "Tteokbokki", "Cơm trộn bibimbap"]),
    "japanese": ("Món Nhật", ["Sushi", "Sashimi", "Ramen", "Tempura"]),
    "sushi": ("Sushi Nhật", ["Sushi", "Sashimi", "Maki cuộn"]),
    "ramen": ("Mì Ramen Nhật", ["Tonkotsu ramen", "Shoyu ramen", "Gyoza"]),
    "thai": ("Món Thái", ["Tom yum", "Pad Thai", "Xôi xoài"]),
    "seafood": ("Hải sản", ["Tôm hấp", "Cua rang me", "Nghêu hấp sả", "Cá nướng"]),
    "hotpot": ("Lẩu", ["Lẩu Thái", "Lẩu nấm", "Lẩu hải sản"]),
    "bbq": ("Đồ nướng BBQ", ["Thịt nướng", "Sườn nướng", "Hải sản nướng"]),
    "barbecue": ("Đồ nướng BBQ", ["Thịt nướng", "Sườn nướng"]),
    "mexican": ("Món Mexico", ["Taco", "Burrito", "Nachos"]),
    "ice_cream": ("Kem & tráng miệng", ["Kem Ý", "Sundae", "Kem cuộn"]),
    "dessert": ("Tráng miệng", ["Chè", "Bánh flan", "Kem"]),
    "bakery": ("Tiệm bánh", ["Bánh ngọt", "Croissant", "Bánh mì"]),
    "sandwich": ("Sandwich & bánh mì", ["Sandwich", "Bánh mì kẹp"]),
    "noodle": ("Mì & bún", ["Mì trộn", "Bún", "Hủ tiếu"]),
    "regional": ("Đặc sản vùng miền", ["Món đặc sản theo mùa"]),
    "asian": ("Ẩm thực châu Á", ["Món xào", "Mì / bún", "Cơm phần"]),
    "international": ("Món quốc tế", ["Thực đơn Á - Âu đa dạng"]),
    "breakfast": ("Điểm tâm sáng", ["Phở", "Bánh mì", "Xôi"]),
    "vegetarian": ("Món chay", ["Cơm chay", "Bún chay", "Lẩu nấm chay"]),
    "vegan": ("Món thuần chay", ["Cơm chay", "Salad", "Đồ chay healthy"]),
    "fast_food": ("Đồ ăn nhanh", ["Burger", "Gà rán", "Khoai tây chiên"]),
}

# amenity code → fallback (label, dishes) when no explicit cuisine tag exists
AMENITY_VI: dict[str, tuple[str, list[str]]] = {
    "cafe": ("Cà phê & đồ uống", ["Cà phê sữa đá", "Bạc xỉu", "Trà trái cây"]),
    "fast_food": ("Đồ ăn nhanh", ["Burger", "Gà rán", "Khoai tây chiên"]),
    "ice_cream": ("Kem & tráng miệng", ["Kem Ý", "Sundae", "Kem cuộn"]),
    "bar": ("Quán bar & đồ uống", ["Cocktail", "Bia thủ công", "Mocktail"]),
    "pub": ("Pub & đồ uống", ["Bia tươi", "Đồ nhắm", "Cocktail"]),
    "biergarten": ("Beer garden", ["Bia tươi", "Đồ nướng", "Đồ nhắm"]),
    "nightclub": ("Club về đêm", ["Cocktail", "Nhạc & DJ"]),
    "food_court": ("Khu ẩm thực", ["Đa dạng món Á - Âu", "Đồ ăn nhanh"]),
    "restaurant": ("Nhà hàng", ["Thực đơn đa dạng"]),
}


def parse_highlights(tags: dict) -> list[str]:
    """Turn real OSM amenity tags into Vietnamese highlight chips."""
    h: list[str] = []
    if str(tags.get("internet_access", "")).lower() in {"wlan", "yes", "wifi"}:
        h.append("📶 Wifi miễn phí")
    if str(tags.get("air_conditioning", "")).lower() == "yes":
        h.append("❄️ Máy lạnh")
    if str(tags.get("outdoor_seating", "")).lower() in {"yes", "terrace", "garden", "parklet", "rooftop", "sidewalk"}:
        h.append("🪑 Chỗ ngồi ngoài trời")
    if str(tags.get("indoor_seating", "")).lower() == "yes":
        h.append("🛋️ Chỗ ngồi trong nhà")
    veg = str(tags.get("diet:vegetarian", "")).lower()
    if veg == "only":
        h.append("🌱 Thuần chay")
    elif veg == "yes":
        h.append("🌱 Có món chay")
    if str(tags.get("diet:vegan", "")).lower() in {"yes", "only"}:
        h.append("🌿 Có món vegan")
    if str(tags.get("diet:halal", "")).lower() == "yes":
        h.append("☪️ Halal")
    if str(tags.get("diet:gluten_free", "")).lower() == "yes":
        h.append("🌾 Không gluten")
    if str(tags.get("takeaway", "")).lower() == "yes":
        h.append("🥡 Có mang đi")
    if str(tags.get("delivery", "")).lower() == "yes":
        h.append("🛵 Có giao hàng")
    if str(tags.get("smoking", "")).lower() in {"no", "outside", "separated", "isolated"}:
        h.append("🚭 Không khói thuốc")
    if str(tags.get("wheelchair", "")).lower() == "yes":
        h.append("♿ Thân thiện xe lăn")
    if str(tags.get("payment:credit_cards", "")).lower() == "yes" or str(tags.get("payment:cards", "")).lower() == "yes":
        h.append("💳 Nhận thẻ")
    if str(tags.get("changing_table", "")).lower() == "yes":
        h.append("🍼 Có bàn thay tã")
    return h[:6]


_DAY_REPL = [
    ("Mo-Su", "Cả tuần"), ("Mo-Sa", "T2–T7"), ("Mo-Fr", "T2–T6"),
    ("Sa-Su", "Cuối tuần"), ("Mo-Th", "T2–T5"),
    ("Mo", "T2"), ("Tu", "T3"), ("We", "T4"), ("Th", "T5"),
    ("Fr", "T6"), ("Sa", "T7"), ("Su", "CN"),
]


def format_hours(oh: str | None) -> str | None:
    """Best-effort prettify of OSM opening_hours into Vietnamese."""
    if not oh:
        return None
    s = str(oh).strip()
    if s in {"24/7", "Mo-Su 00:00-24:00"}:
        return "Mở cửa 24/7"
    for a, b in _DAY_REPL:
        s = s.replace(a, b)
    s = s.replace(";", " · ").replace(",", " & ")
    return s


def build_place_detail(row: dict) -> dict:
    """Build the truthful detail payload for a single provider row."""
    try:
        tags = json.loads(row.get("raw_tags_json") or "{}")
    except Exception:
        tags = {}

    cuisine_label = None
    must_try: list[str] = []
    raw_cuisine = str(tags.get("cuisine", "")).lower()
    if raw_cuisine:
        labels: list[str] = []
        for part in raw_cuisine.replace(",", ";").split(";"):
            part = part.strip()
            if part in CUISINE_VI:
                label, dishes = CUISINE_VI[part]
                labels.append(label)
                must_try.extend(dishes)
        if labels:
            cuisine_label = " · ".join(dict.fromkeys(labels))
            must_try = list(dict.fromkeys(must_try))[:5]

    # Fallback to the amenity type when there's no explicit cuisine tag
    if not cuisine_label:
        amenity = str(tags.get("amenity", "")).lower()
        if amenity in AMENITY_VI:
            cuisine_label, must_try = AMENITY_VI[amenity][0], list(AMENITY_VI[amenity][1])

    return {
        "cuisine": cuisine_label,
        "must_try": must_try,
        "highlights": parse_highlights(tags),
        "address": row.get("address"),
        "opening_hours": format_hours(row.get("opening_hours") or tags.get("opening_hours")),
        "phone": row.get("phone") or tags.get("phone"),
        "website": row.get("website") or tags.get("website"),
    }


def fetch_place_details(conn, provider_ids: list[int]) -> dict[int, dict]:
    """Fetch + parse truthful details for many providers at once.

    Returns {provider_id: detail_dict}. Never raises — enrichment is best-effort.
    """
    ids = [pid for pid in dict.fromkeys(provider_ids) if pid is not None]
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    try:
        rows = conn.execute(
            f"SELECT id, address, phone, website, opening_hours, raw_tags_json "
            f"FROM providers WHERE id IN ({placeholders})",
            tuple(ids),
        ).fetchall()
    except Exception:
        return {}
    out: dict[int, dict] = {}
    for r in rows:
        d = dict(r)
        out[d["id"]] = build_place_detail(d)
    return out
