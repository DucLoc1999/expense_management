import json
import re
import logging
import httpx
from dataclasses import dataclass
import config
from bot.i18n import _

logger = logging.getLogger(__name__)

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-3.6-flash:generateContent"
)


@dataclass
class ExtractedOrder:
    name: str
    quantity: int
    price: int
    money: int
    shop: str
    suggested_category: str
    payment_source: str = "shopee"


async def extract_orders(
    image_bytes: bytes,
    mime_type: str,
    categories: list[str],
) -> tuple[list[ExtractedOrder], str | None]:
    """Return (orders, error_message). error_message is None on success."""
    category_list = ", ".join(categories)
    prompt = _("gemini.prompt", categories=category_list)
    print("--------", prompt)

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
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096},
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
        print("== GEMINI RAW TEXT ==", raw_text)
    except (KeyError, IndexError) as e:
        print("== GEMINI RESP KEYERROR ==", e, resp.text)
        return [], "Unexpected response from Gemini."

    raw_text = raw_text.strip()
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        parsed = json.loads(raw_text)
        print("== GEMINI PARSED ==", parsed)
    except json.JSONDecodeError as e:
        print("== JSON DECODE ERROR == ", e, "RAW:", raw_text)
        return [], "Could not read orders from this image. Try a clearer screenshot."

    if isinstance(parsed, dict) and "error" in parsed:
        print("== GEMINI ERROR DICT ==", parsed["error"])
        return [], parsed["error"]

    if not isinstance(parsed, list):
        print("== GEMINI NOT LIST ==", type(parsed), parsed)
        return [], "Could not read orders from this image. Try a clearer screenshot."

    orders: list[ExtractedOrder] = []
    for item in parsed:
        order = _parse_order(item, categories)
        if order:
            orders.append(order)
        else:
            print("== PARSE ORDER FAILED FOR ITEM ==", item)

    if not orders:
        return [], "Could not read orders from this image. Try a clearer screenshot."

    return orders, None


def _parse_order(item: dict, categories: list[str]) -> ExtractedOrder | None:
    try:
        name = str(item.get("name", "")).strip()
        quantity = int(item.get("quantity", 1))
        money = int(item.get("money", 0))
        price = int(item.get("price", money if money > 0 else 0))
        shop = str(item.get("shop", "")).strip()
        suggested = str(item.get("suggested_category", "Khác")).strip()
        payment_source = str(item.get("payment_source", "shopee")).strip()

        if not name or money <= 0:
            return None
        if quantity <= 0:
            quantity = 1
        if price <= 0:
            price = money
        if suggested not in categories:
            suggested = "Khác"
        if payment_source not in ("shopee", "bank_transfer", "other"):
            payment_source = "shopee"

        return ExtractedOrder(
            name=name,
            quantity=quantity,
            price=price,
            money=money,
            shop=shop,
            suggested_category=suggested,
            payment_source=payment_source,
        )
    except (TypeError, ValueError) as e:
        print("== PARSE ORDER EXCEPTION ==", e)
        return None


def _b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode()

