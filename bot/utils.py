"""Мелкие помощники: разбор и форматирование дат, экранирование HTML."""
from __future__ import annotations

import html
import re
from datetime import datetime

DATE_INPUT_HINT = "ДД.ММ.ГГГГ ЧЧ:ММ (например 15.05.2026 14:30)"

_DATE_RE = re.compile(
    r"^\s*(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})[\s,]+(\d{1,2})[:.](\d{2})\s*$"
)

_MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)
_WEEKDAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


def parse_datetime(raw: str) -> datetime | None:
    """'15.05.2026 14:30' -> datetime. None, если формат не распознан."""
    match = _DATE_RE.match(raw)
    if not match:
        return None
    day, month, year, hour, minute = (int(part) for part in match.groups())
    if year < 100:
        year += 2000
    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None


def format_datetime(value: datetime) -> str:
    """datetime -> '15 мая (пт), 14:30'."""
    return (
        f"{value.day} {_MONTHS[value.month - 1]} ({_WEEKDAYS[value.weekday()]}), "
        f"{value:%H:%M}"
    )


def format_short(value: datetime) -> str:
    """Компактный вид для кнопок: '15.05 14:30'."""
    return f"{value:%d.%m %H:%M}"


def to_db(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def from_db(raw: str) -> datetime:
    return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")


def esc(value: str | None) -> str:
    return html.escape(value or "", quote=False)
