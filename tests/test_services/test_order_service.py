import pytest
from unittest.mock import AsyncMock, patch

from bot.models import PendingOrder
from services.gemini import ExtractedOrder
from services.order_service import confirm_order, confirm_all_orders
from db.models import Category


def _make_extracted(**overrides) -> ExtractedOrder:
    return ExtractedOrder(
        name=overrides.get("name", "Cà phê"),
        quantity=overrides.get("quantity", 1),
        price=overrides.get("price", 35000),
        money=overrides.get("money", 35000),
        shop=overrides.get("shop", "Highlands"),
        suggested_category=overrides.get("suggested_category", "Ăn uống"),
        payment_source=overrides.get("payment_source", "shopee"),
    )


def _make_pending(**overrides):
    extracted = overrides.pop("extracted", _make_extracted())
    return PendingOrder(extracted=extracted, **overrides)


@pytest.fixture
def mock_db():
    with patch("services.order_service.get_category_by_name", new_callable=AsyncMock) as get_cat, \
         patch("services.order_service.save_bill", new_callable=AsyncMock) as save:
        get_cat.return_value = Category(id=1, name="Ăn uống", is_system=False)
        save.return_value = 101
        yield {"get_category_by_name": get_cat, "save_bill": save}


@pytest.mark.asyncio
class TestConfirmOrder:
    async def test_confirms_and_saves(self, mock_db):
        po = _make_pending()

        order_id = await confirm_order(po, tele_user_id=111)

        assert order_id == 101
        assert po.status == "confirmed"
        mock_db["save_bill"].assert_awaited_once()
        call_kwargs = mock_db["save_bill"].await_args.kwargs
        assert call_kwargs["tele_user_id"] == 111

    async def test_falls_back_to_khac_category(self, mock_db):
        mock_db["get_category_by_name"].side_effect = [
            None,
            Category(id=99, name="Khác", is_system=True),
        ]
        po = _make_pending(category_name="NonExistent")

        await confirm_order(po, tele_user_id=111)

        calls = mock_db["get_category_by_name"].await_args_list
        assert calls[0].args[0] == "NonExistent"
        assert calls[0].args[1] == 111
        assert calls[1].args[0] == "Khác"
        assert calls[1].args[1] == 111

    async def test_uses_pending_order_fields(self, mock_db):
        po = _make_pending(
            extracted=_make_extracted(name="Pizza", money=120000, shop="Pizza4Ps"),
            notes="extra cheese",
        )

        await confirm_order(po, tele_user_id=111)

        call_kwargs = mock_db["save_bill"].await_args.kwargs
        assert call_kwargs["name"] == "Pizza"
        assert call_kwargs["money"] == 120000
        assert call_kwargs["shop"] == "Pizza4Ps"
        assert call_kwargs["notes"] == "extra cheese"


@pytest.mark.asyncio
class TestConfirmAllOrders:
    async def test_confirms_all_pending(self, mock_db):
        pending = [_make_pending(), _make_pending(), _make_pending()]

        count = await confirm_all_orders(pending, tele_user_id=111)

        assert count == 3
        assert all(po.status == "confirmed" for po in pending)
        assert mock_db["save_bill"].await_count == 3

    async def test_skips_already_confirmed(self, mock_db):
        pending = [
            _make_pending(),
            _make_pending(status="confirmed"),
            _make_pending(),
        ]

        count = await confirm_all_orders(pending, tele_user_id=111)

        assert count == 2
        assert mock_db["save_bill"].await_count == 2

    async def test_empty_list_returns_early(self, mock_db):
        count = await confirm_all_orders([], tele_user_id=111)

        assert count == 0
        mock_db["save_bill"].assert_not_awaited()

    async def test_all_confirmed_returns_zero(self, mock_db):
        pending = [_make_pending(status="confirmed"), _make_pending(status="confirmed")]

        count = await confirm_all_orders(pending, tele_user_id=111)

        assert count == 0
