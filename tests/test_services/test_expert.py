from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from db.models import CategoryTotal, PeriodStats
from services.expert import (
    RangeError,
    Summary,
    build_advisor_context,
    build_chart_url,
    build_memory,
    build_summary,
    parse_custom_range,
    resolve_preset,
)


class TestResolvePreset:
    def test_last_7_rolling(self):
        start, end = resolve_preset("last_7", today=date(2026, 8, 2))
        assert (start, end) == (date(2026, 7, 27), date(2026, 8, 2))

    def test_last_30_rolling(self):
        start, end = resolve_preset("last_30", today=date(2026, 8, 2))
        assert (start, end) == (date(2026, 7, 4), date(2026, 8, 2))

    def test_last_week_calendar(self):
        start, end = resolve_preset("last_week", today=date(2026, 8, 2))
        assert (start, end) == (date(2026, 7, 20), date(2026, 7, 26))

    def test_last_month_calendar(self):
        start, end = resolve_preset("last_month", today=date(2026, 8, 2))
        assert (start, end) == (date(2026, 7, 1), date(2026, 7, 31))

    def test_last_3_months_calendar(self):
        start, end = resolve_preset("last_3_months", today=date(2026, 8, 2))
        assert (start, end) == (date(2026, 5, 1), date(2026, 7, 31))

    def test_last_6_months_calendar(self):
        start, end = resolve_preset("last_6_months", today=date(2026, 8, 2))
        assert (start, end) == (date(2026, 2, 1), date(2026, 7, 31))

    def test_defaults_to_today(self):
        start, end = resolve_preset("last_30")
        assert end == date.today()
        assert start == end - timedelta(days=29)


class TestParseCustomRange:
    def test_valid(self):
        start, end = parse_custom_range("01/07/2026 - 31/07/2026")
        assert (start, end) == (date(2026, 7, 1), date(2026, 7, 31))

    def test_bad_format(self):
        with pytest.raises(RangeError) as exc:
            parse_custom_range("garbage")
        assert exc.value.message_key == "format"

    def test_invalid_dates(self):
        with pytest.raises(RangeError) as exc:
            parse_custom_range("32/01/2026 - 01/02/2026")
        assert exc.value.message_key == "dates"

    def test_reversed_order(self):
        with pytest.raises(RangeError) as exc:
            parse_custom_range("31/07/2026 - 01/07/2026")
        assert exc.value.message_key == "order"

    def test_span_too_long(self):
        with pytest.raises(RangeError) as exc:
            parse_custom_range("01/01/2020 - 01/08/2020")
        assert exc.value.message_key == "span"

    def test_exactly_max_span_ok(self):
        start, end = parse_custom_range("17/01/2026 - 04/08/2026")
        assert (end - start).days + 1 == 200


class TestBuildChartUrl:
    def _summary(self):
        return Summary(
            start="2026-07-01",
            end="2026-07-31",
            count=3,
            total=150000,
            avg_per_day=5000.0,
            avg_per_bill=50000.0,
            top_category="Food",
            top_category_share=60.0,
            prev_total=100000,
            change_pct=50.0,
            categories=[
                CategoryTotal("Food", "Đồ ăn", 90000),
                CategoryTotal("Other", "Khác", 60000),
            ],
        )

    def test_returns_url(self):
        url = build_chart_url(self._summary())
        assert url is not None
        assert url.startswith("https://quickchart.io/chart?c=")

    def test_none_without_categories(self):
        s = self._summary()
        s.categories = []
        assert build_chart_url(s) is None

    def test_none_without_summary(self):
        assert build_chart_url(None) is None


class TestBuildMemory:
    def test_bookends_when_few_pairs(self):
        messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        lines = build_memory(messages, "current?")
        assert len(lines) == 3
        assert "hi" in lines[0]
        assert "hello" in lines[1]
        assert "current?" in lines[2]

    def test_truncates_middle_pairs(self):
        messages = [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "q3"},
            {"role": "assistant", "content": "a3"},
            {"role": "user", "content": "q4"},
        ]
        lines = build_memory(messages, "final?")
        assert len(lines) == 5
        assert "q1" in lines[0] and "a1" in lines[1]
        assert "q3" in lines[2] and "a3" in lines[3]
        assert "final?" in lines[4]

    def test_empty_messages(self):
        lines = build_memory([], "only?")
        assert len(lines) == 1
        assert "only?" in lines[0]


@pytest.mark.asyncio
class TestBuildSummary:
    @patch("services.expert.get_category_totals", new_callable=AsyncMock)
    @patch("services.expert.get_period_stats", new_callable=AsyncMock)
    async def test_builds_summary(self, mock_stats, mock_cats):
        mock_stats.side_effect = [
            PeriodStats(count=3, total=150000, avg_per_day=5000.0, avg_per_bill=50000.0),
            PeriodStats(count=2, total=100000, avg_per_day=10000.0, avg_per_bill=50000.0),
        ]
        mock_cats.return_value = [
            CategoryTotal("Food", "Đồ ăn", 90000),
            CategoryTotal("Other", "Khác", 60000),
        ]

        s = await build_summary(111, date(2026, 7, 1), date(2026, 7, 31))

        assert s is not None
        assert s.count == 3
        assert s.total == 150000
        assert s.top_category == "Đồ ăn"
        assert s.top_category_share == 60.0
        assert s.change_pct == 50.0

    @patch("services.expert.get_category_totals", new_callable=AsyncMock)
    @patch("services.expert.get_period_stats", new_callable=AsyncMock)
    async def test_returns_none_without_bills(self, mock_stats, mock_cats):
        mock_stats.return_value = None

        s = await build_summary(111, date(2026, 7, 1), date(2026, 7, 31))

        assert s is None
        mock_cats.assert_not_awaited()


@pytest.mark.asyncio
class TestBuildAdvisorContext:
    @patch("services.expert.get_bills_in_range", new_callable=AsyncMock)
    @patch("services.expert.get_category_totals", new_callable=AsyncMock)
    @patch("services.expert.get_period_stats", new_callable=AsyncMock)
    async def test_raw_bills_when_small(self, mock_stats, mock_cats, mock_bills):
        mock_stats.return_value = PeriodStats(
            count=1, total=35000, avg_per_day=35000.0, avg_per_bill=35000.0
        )
        mock_bills.return_value = []
        mock_cats.return_value = []

        text = await build_advisor_context(111, date(2026, 7, 1), date(2026, 7, 31))

        assert mock_bills.await_args is not None
        assert isinstance(text, str)

    @patch("services.expert.get_bills_in_range", new_callable=AsyncMock)
    @patch("services.expert.get_category_totals", new_callable=AsyncMock)
    @patch("services.expert.get_period_stats", new_callable=AsyncMock)
    async def test_aggregates_when_large(self, mock_stats, mock_cats, mock_bills):
        mock_stats.return_value = PeriodStats(
            count=9999, total=35000, avg_per_day=35000.0, avg_per_bill=35000.0
        )
        mock_cats.return_value = [CategoryTotal("Food", "Đồ ăn", 35000)]

        text = await build_advisor_context(111, date(2026, 7, 1), date(2026, 7, 31))

        mock_bills.assert_not_awaited()
        assert "Đồ ăn" in text

    @patch("services.expert.get_period_stats", new_callable=AsyncMock)
    async def test_none_context(self, mock_stats):
        mock_stats.return_value = None

        text = await build_advisor_context(111, date(2026, 7, 1), date(2026, 7, 31))

        assert "expert.advisor_context_none" in text or "Không có" in text
