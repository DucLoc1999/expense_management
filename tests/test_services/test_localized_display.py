import pytest

from bot.i18n import load_locales, localized_name, set_locale
from bot.responses import categories_list, history_list
from db.models import Bill, Category


@pytest.fixture(autouse=True)
def _reset_locale():
    load_locales()
    set_locale("vi")
    yield
    set_locale("vi")


class TestLocalizedName:
    def test_vi_prefers_name_vi(self):
        set_locale("vi")
        assert localized_name("Food & Drink", "Ăn uống") == "Ăn uống"

    def test_vi_falls_back_to_name(self):
        set_locale("vi")
        assert localized_name("Gia vị", None) == "Gia vị"

    def test_en_uses_name(self):
        set_locale("en")
        assert localized_name("Food & Drink", "Ăn uống") == "Food & Drink"


class TestCategoriesList:
    def test_vi_shows_vietnamese_names(self):
        set_locale("vi")
        cats = [
            Category(id=1, name="Food & Drink", is_system=True, name_vi="Ăn uống"),
            Category(id=2, name="Gia vị", is_system=False, name_vi="Gia vị"),
        ]
        text = categories_list(cats)
        assert "Ăn uống" in text
        assert "Food & Drink" not in text

    def test_en_shows_english_names(self):
        set_locale("en")
        cats = [Category(id=1, name="Food & Drink", is_system=True, name_vi="Ăn uống")]
        text = categories_list(cats)
        assert "Food &amp; Drink" in text
        assert "Ăn uống" not in text


class TestHistoryList:
    def _make_bill(self):
        return Bill(
            id=1,
            name="Cà phê",
            money=35000,
            shop="Highlands",
            date="2026-08-01",
            notes="",
            category_name="Food & Drink",
            category_name_vi="Ăn uống",
        )

    def test_vi_shows_vietnamese_category(self):
        set_locale("vi")
        text = history_list([self._make_bill()])
        assert "Ăn uống" in text
        assert "Food & Drink" not in text

    def test_en_shows_english_category(self):
        set_locale("en")
        text = history_list([self._make_bill()])
        assert "Food &amp; Drink" in text
        assert "Ăn uống" not in text
