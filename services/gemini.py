import json
import re
import httpx
from dataclasses import dataclass
import config

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


@dataclass
class ExtractedOrder:
    name: str
    quantity: int
    price: int
    money: int
    shop: str
    suggested_category: str


async def extract_orders(
    image_bytes: bytes,
    mime_type: str,
    categories: list[str],
) -> tuple[list[ExtractedOrder], str | None]:
    """Return (orders, error_message). error_message is None on success."""
    category_list = ", ".join(categories)
    prompt = (
        "You are extracting expense data from payment screenshots.\n"
        f"Available categories: {category_list}\n\n"
        "Extract ALL expense items visible in the image and return a JSON array. "
        "Each object must have these fields:\n"
        '  "name": item name (string)\n'
        '  "quantity": number of items (int, default 1)\n'
        '  "price": price per item in VND (int, no decimals)\n'
        '  "money": total paid in VND (int)\n'
        '  "shop": seller/payee name (string)\n'
        '  "suggested_category": best match from the category list above (string)\n'
        '  "payment_source": one of "shopee", "bank_transfer", "other" (string)\n\n'
        "If the image is not a payment receipt or no expenses are found, "
        'return {"error": "No expenses found"}.\n'
        "Return ONLY valid JSON, no markdown fences."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": _b64(image_bytes),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                GEMINI_API_URL,
                params={"key": config.GEMINI_API_KEY},
                json=payload,
            )
            resp.raise_for_status()
    except httpx.TimeoutException:
        return [], "Request timed out. Please try again."
    except httpx.HTTPStatusError as e:
        return [], f"Gemini API error: {e.response.status_code}"

    try:
        raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return [], "Unexpected response from Gemini."

    raw_text = raw_text.strip()
    # Strip markdown fences if present
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return [], "Could not read orders from this image. Try a clearer screenshot."

    if isinstance(parsed, dict) and "error" in parsed:
        return [], parsed["error"]

    if not isinstance(parsed, list):
        return [], "Could not read orders from this image. Try a clearer screenshot."

    orders: list[ExtractedOrder] = []
    for item in parsed:
        order = _parse_order(item, categories)
        if order:
            orders.append(order)

    if not orders:
        return [], "Could not read orders from this image. Try a clearer screenshot."

    return orders, None


def _parse_order(item: dict, categories: list[str]) -> ExtractedOrder | None:
    try:
        name = str(item.get("name", "")).strip()
        quantity = int(item.get("quantity", 1))
        price = int(item.get("price", 0))
        money = int(item.get("money", 0))
        shop = str(item.get("shop", "")).strip()
        suggested = str(item.get("suggested_category", "Khác")).strip()

        if not name or price <= 0:
            return None
        if quantity <= 0:
            quantity = 1
        # Fallback: if money missing, calculate
        if money <= 0:
            money = price * quantity
        # Validate suggested category is in list
        if suggested not in categories:
            suggested = "Khác"

        return ExtractedOrder(
            name=name,
            quantity=quantity,
            price=price,
            money=money,
            shop=shop,
            suggested_category=suggested,
        )
    except (TypeError, ValueError):
        return None


def _b64(data: bytes) -> str:
    import base64
    return base64.b64encode(data).decode()
