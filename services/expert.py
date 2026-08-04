import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import quote

import config
from bot.i18n import _, localized_name
from db.models import (
    get_bills_in_range,
    get_category_totals,
    get_period_stats,
    PeriodStats,
    CategoryTotal,
)

GMT7 = timezone(timedelta(hours=7))

DEFAULT_PRESET = "last_30"

_ROLLING_DAYS = {"last_7": 7, "last_30": 30, "last_90": 90}
_CALENDAR_MONTHS = {"last_3_months": 3, "last_6_months": 6}

_CUSTOM_RANGE_RE = re.compile(
    r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*-\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$"
)
_MAX_SPAN_DAYS = 200


class RangeError(ValueError):
    """Invalid custom range. ``message_key`` selects the i18n message."""

    def __init__(self, message_key: str):
        super().__init__(message_key)
        self.message_key = message_key


@dataclass
class Summary:
    start: str
    end: str
    count: int
    total: int
    avg_per_day: float
    avg_per_bill: float
    top_category: str | None
    top_category_share: float | None
    prev_total: int
    change_pct: float | None
    categories: list[CategoryTotal]


def today_now() -> date:
    """Current date in GMT+7."""
    return datetime.now(GMT7).date()


def resolve_preset(key: str, today: date | None = None) -> tuple[date, date]:
    """Resolve a preset key to an inclusive (start, end) date pair."""
    if today is None:
        today = today_now()
    if key in _ROLLING_DAYS:
        n = _ROLLING_DAYS[key]
        return today - timedelta(days=n - 1), today
    if key == "last_week":
        end = today - timedelta(days=today.weekday() + 1)
        start = end - timedelta(days=6)
        return start, end
    if key == "last_month":
        end = _first_of_month(today) - timedelta(days=1)
        start = _first_of_month(end)
        return start, end
    if key in _CALENDAR_MONTHS:
        n = _CALENDAR_MONTHS[key]
        end = _first_of_month(today) - timedelta(days=1)
        y, m = _shift_month(end.year, end.month, -(n - 1))
        start = date(y, m, 1)
        return start, end
    raise ValueError(f"Unknown preset: {key}")


def parse_custom_range(text: str) -> tuple[date, date]:
    """Parse ``dd/mm/yyyy - dd/mm/yyyy`` into an inclusive (start, end).

    Raises :class:`RangeError` for malformed input, invalid dates, ``from > to``,
    or spans longer than ``_MAX_SPAN_DAYS``.
    """
    m = _CUSTOM_RANGE_RE.match(text)
    if not m:
        raise RangeError("format")
    try:
        start = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        end = date(int(m.group(6)), int(m.group(5)), int(m.group(4)))
    except ValueError:
        raise RangeError("dates")
    if start > end:
        raise RangeError("order")
    if (end - start).days + 1 > _MAX_SPAN_DAYS:
        raise RangeError("span")
    return start, end


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + delta
    return total // 12, total % 12 + 1


def _previous_period(start: date, end: date) -> tuple[date, date]:
    span = (end - start).days + 1
    return start - timedelta(days=span), start - timedelta(days=1)


async def build_summary(
    tele_user_id: int, start: date | str, end: date | str
) -> Summary | None:
    """Build the spend summary for the window, or None when there are no bills."""
    start_d = _as_date(start)
    end_d = _as_date(end)
    stats = await get_period_stats(tele_user_id, start_d, end_d)
    if stats is None:
        return None

    categories = await get_category_totals(tele_user_id, start_d, end_d)
    top = categories[0] if categories else None
    top_name = localized_name(top.category_name, top.name_vi) if top else None
    top_share = (top.total / stats.total * 100) if top and stats.total else None

    prev_start, prev_end = _previous_period(start_d, end_d)
    prev_stats = await get_period_stats(tele_user_id, prev_start, prev_end)
    prev_total = prev_stats.total if prev_stats else 0
    change_pct = ((stats.total - prev_total) / prev_total * 100) if prev_total else None

    return Summary(
        start=start_d.isoformat(),
        end=end_d.isoformat(),
        count=stats.count,
        total=stats.total,
        avg_per_day=stats.avg_per_day,
        avg_per_bill=stats.avg_per_bill,
        top_category=top_name,
        top_category_share=top_share,
        prev_total=prev_total,
        change_pct=change_pct,
        categories=categories,
    )


def build_chart_url(summary: Summary | None) -> str | None:
    """QuickChart.io pie URL for top-5 categories + Other, or None when no chart data."""
    if not summary or not summary.categories:
        return None
    categories = summary.categories
    top = categories[:5]
    rest_total = sum(c.total for c in categories[5:])

    labels = [localized_name(c.category_name, c.name_vi) for c in top]
    data = [c.total for c in top]
    if rest_total > 0:
        labels.append(_("expert.chart_other"))
        data.append(rest_total)

    config_dict = {
        "type": "pie",
        "data": {
            "labels": labels,
            "datasets": [{"data": data}],
        },
    }
    encoded = quote(json.dumps(config_dict, ensure_ascii=False))
    return f"https://quickchart.io/chart?c={encoded}"


async def build_advisor_context(
    tele_user_id: int, start: date | str, end: date | str
) -> str:
    """Raw bill list when small enough, otherwise an aggregated summary."""
    start_d = _as_date(start)
    end_d = _as_date(end)
    stats = await get_period_stats(tele_user_id, start_d, end_d)
    if stats is None:
        return _("expert.advisor_context_none")

    max_bills = config.EXPERT_MAX_BILLS_FOR_AI
    if stats.count <= max_bills:
        bills = await get_bills_in_range(tele_user_id, start_d, end_d, limit=max_bills)
        lines = [
            f"{b.date} · {b.name} · {localized_name(b.category_name, b.category_name_vi)} · {b.money} VND"
            for b in bills
        ]
        return "\n".join(lines)

    lines = [
        f"Period: {start_d.isoformat()} to {end_d.isoformat()}",
        (
            f"Total: {stats.count} bills, {stats.total} VND total, "
            f"avg {round(stats.avg_per_bill)} VND per bill"
        ),
    ]
    for ct in await get_category_totals(tele_user_id, start_d, end_d):
        lines.append(f"{localized_name(ct.category_name, ct.name_vi)}: {ct.total} VND")
    return "\n".join(lines)


def build_memory(messages: list[dict], current_question: str) -> list[str]:
    """Bookends memory window: first exchange, last exchange, current question.

    ``messages`` are prior messages in chronological order. Returns at most 5 lines.
    """
    pairs = [
        (messages[i]["content"], messages[i + 1]["content"])
        for i in range(0, len(messages) - 1, 2)
        if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant"
    ]
    lines: list[str] = []
    if pairs:
        first = pairs[0]
        lines.append(_("expert.memory_user", content=first[0]))
        lines.append(_("expert.memory_assistant", content=first[1]))
        if len(pairs) > 1:
            last = pairs[-1]
            if len(pairs) > 2 or last != first:
                lines.append(_("expert.memory_user", content=last[0]))
                lines.append(_("expert.memory_assistant", content=last[1]))
    elif messages:
        for msg in messages[-2:]:
            key = "expert.memory_assistant" if msg["role"] == "assistant" else "expert.memory_user"
            lines.append(_(key, content=msg["content"]))
    lines.append(_("expert.memory_user", content=current_question))
    return lines


def _as_date(v) -> date:
    if isinstance(v, str):
        return datetime.strptime(v, "%Y-%m-%d").date()
    return v
