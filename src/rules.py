"""Weather warning classification rules."""

from __future__ import annotations

from src.hko_client import WarningSummary

# Immediate alert subtypes
IMMEDIATE_SUBTYPES = frozenset(
    {
        "WRAINR",  # Red rainstorm
        "WRAINB",  # Black rainstorm
        "TC8NE",
        "TC8NW",
        "TC8SE",
        "TC8SW",
        "TC10",
    }
)

SUBTYPE_LABELS = {
    "WRAINR": "紅色暴雨警告",
    "WRAINB": "黑色暴雨警告",
    "TC8NE": "八號東北烈風或暴風信號",
    "TC8NW": "八號西北烈風或暴風信號",
    "TC8SE": "八號東南烈風或暴風信號",
    "TC8SW": "八號西南烈風或暴風信號",
    "TC10": "十號颶風信號",
    "WRAINA": "黃色暴雨警告",
    "TC1": "一號戒備信號",
    "TC3": "三號強風信號",
    "TC9": "九號烈風或暴風風力增強信號",
    "WTS": "雷暴警告",
    "WL": "山泥傾瀉警告",
    "WCOLD": "寒冷天氣警告",
    "WHOT": "酷熱天氣警告",
    "WMSGNL": "強烈季候風信號",
    "WFROST": "霜凍警告",
    "WFIREY": "黃色火災危險警告",
    "WFIRER": "紅色火災危險警告",
    "WTMW": "海嘯警告",
    "WFNTSA": "新界北部水浸特別報告",
}


def is_immediate_alert(warning: WarningSummary) -> bool:
    """Return True if the warning should trigger an immediate notification."""
    return warning.subtype.upper() in IMMEDIATE_SUBTYPES


def get_warning_label(warning: WarningSummary) -> str:
    """Human-readable label for a warning."""
    label = SUBTYPE_LABELS.get(warning.subtype.upper())
    if label:
        return label
    if warning.warning_type:
        return f"{warning.name} ({warning.warning_type})"
    return warning.name


def filter_immediate_alerts(warnings: list[WarningSummary]) -> list[WarningSummary]:
    """Return warnings that qualify for immediate notification."""
    return [warning for warning in warnings if is_immediate_alert(warning)]


def filter_daily_warnings(warnings: list[WarningSummary]) -> list[WarningSummary]:
    """Return warnings for daily summary (excludes immediate-alert types)."""
    return [warning for warning in warnings if not is_immediate_alert(warning)]
