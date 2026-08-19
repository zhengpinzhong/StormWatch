"""HKO Open Data API client with RSS fallback."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"
RSS_WARN_SUM_URL = "https://rss.weather.gov.hk/rss/WeatherWarningSummaryv2.xml"
RSS_WARN_INFO_URL = "https://rss.weather.gov.hk/rss/WeatherWarningInfov2.xml"
REQUEST_TIMEOUT = 30


@dataclass
class WarningSummary:
    """A single active warning from warnsum."""

    statement_code: str
    subtype: str
    name: str
    warning_type: str | None
    action_code: str
    issue_time: str
    update_time: str
    expire_time: str | None = None

    @property
    def dedupe_key(self) -> str:
        return f"{self.statement_code}|{self.subtype}|{self.action_code}|{self.issue_time}"


@dataclass
class WarningDetail:
    """Detailed warning content from warningInfo."""

    statement_code: str
    subtype: str | None
    contents: list[str] = field(default_factory=list)
    update_time: str | None = None


class HKOClient:
    """Client for Hong Kong Observatory weather warning APIs."""

    def __init__(self, lang: str = "tc") -> None:
        self.lang = lang
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "StormWatch/1.0"})

    def _get_json(self, data_type: str) -> dict[str, Any]:
        response = self.session.get(
            BASE_URL,
            params={"dataType": data_type, "lang": self.lang},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError(f"Unexpected {data_type} response type: {type(payload)}")
        return payload

    def fetch_warning_summary(self) -> list[WarningSummary]:
        """Fetch active weather warnings from warnsum endpoint."""
        try:
            return self._parse_warnsum(self._get_json("warnsum"))
        except Exception as exc:
            logger.warning("warnsum API failed, falling back to RSS: %s", exc)
            return self._parse_warnsum_rss()

    def fetch_warning_info(self) -> list[WarningDetail]:
        """Fetch detailed warning information from warningInfo endpoint."""
        try:
            return self._parse_warning_info(self._get_json("warningInfo"))
        except Exception as exc:
            logger.warning("warningInfo API failed, falling back to RSS: %s", exc)
            return self._parse_warning_info_rss()

    def _parse_warnsum(self, payload: dict[str, Any]) -> list[WarningSummary]:
        warnings: list[WarningSummary] = []
        for statement_code, item in payload.items():
            if not isinstance(item, dict):
                continue
            subtype = str(item.get("code", ""))
            if not subtype or subtype.upper() == "CANCEL":
                continue
            warnings.append(
                WarningSummary(
                    statement_code=statement_code,
                    subtype=subtype,
                    name=str(item.get("name", statement_code)),
                    warning_type=item.get("type"),
                    action_code=str(item.get("actionCode", "ISSUE")),
                    issue_time=str(item.get("issueTime", item.get("updateTime", ""))),
                    update_time=str(item.get("updateTime", "")),
                    expire_time=item.get("expireTime"),
                )
            )
        return warnings

    def _parse_warning_info(self, payload: dict[str, Any]) -> list[WarningDetail]:
        details: list[WarningDetail] = []
        for item in payload.get("details", []):
            if not isinstance(item, dict):
                continue
            contents = item.get("contents", [])
            if not isinstance(contents, list):
                contents = [str(contents)]
            details.append(
                WarningDetail(
                    statement_code=str(item.get("warningStatementCode", "")),
                    subtype=item.get("subtype"),
                    contents=[str(line) for line in contents],
                    update_time=item.get("updateTime"),
                )
            )
        return details

    def _parse_warnsum_rss(self) -> list[WarningSummary]:
        response = self.session.get(RSS_WARN_SUM_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        warnings: list[WarningSummary] = []
        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", default="", namespaces=ns)
            updated = entry.findtext("atom:updated", default="", namespaces=ns)
            if not title:
                continue
            statement_code, subtype = self._guess_codes_from_title(title)
            warnings.append(
                WarningSummary(
                    statement_code=statement_code,
                    subtype=subtype,
                    name=title,
                    warning_type=None,
                    action_code="ISSUE",
                    issue_time=updated,
                    update_time=updated,
                )
            )
        return warnings

    def _parse_warning_info_rss(self) -> list[WarningDetail]:
        response = self.session.get(RSS_WARN_INFO_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        details: list[WarningDetail] = []
        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", default="", namespaces=ns)
            summary = entry.findtext("atom:summary", default="", namespaces=ns)
            updated = entry.findtext("atom:updated", default="", namespaces=ns)
            statement_code, subtype = self._guess_codes_from_title(title)
            details.append(
                WarningDetail(
                    statement_code=statement_code,
                    subtype=subtype,
                    contents=[summary] if summary else [title],
                    update_time=updated,
                )
            )
        return details

    @staticmethod
    def _guess_codes_from_title(title: str) -> tuple[str, str]:
        """Best-effort mapping from RSS title text to statement/subtype codes."""
        title_lower = title.lower()
        mappings = [
            (("black rain", "黑色暴雨"), ("WRAIN", "WRAINB")),
            (("red rain", "紅色暴雨", "红色暴雨"), ("WRAIN", "WRAINR")),
            (("amber rain", "黃色暴雨", "黄色暴雨"), ("WRAIN", "WRAINA")),
            (("no. 10", "十號", "10号", "10號"), ("WTCSGNL", "TC10")),
            (("no. 9", "九號", "9号", "9號"), ("WTCSGNL", "TC9")),
            (("no. 8 northeast", "八號東北", "8号东北"), ("WTCSGNL", "TC8NE")),
            (("no. 8 northwest", "八號西北", "8号西北"), ("WTCSGNL", "TC8NW")),
            (("no. 8 southeast", "八號東南", "8号东南"), ("WTCSGNL", "TC8SE")),
            (("no. 8 southwest", "八號西南", "8号西南"), ("WTCSGNL", "TC8SW")),
            (("no. 8", "八號", "8号", "8號"), ("WTCSGNL", "TC8NE")),
            (("no. 3", "三號", "3号", "3號"), ("WTCSGNL", "TC3")),
            (("no. 1", "一號", "1号", "1號"), ("WTCSGNL", "TC1")),
            (("thunderstorm", "雷暴"), ("WTS", "WTS")),
            (("landslip", "山泥"), ("WL", "WL")),
            (("cold weather", "寒冷"), ("WCOLD", "WCOLD")),
            (("very hot", "酷熱", "酷热"), ("WHOT", "WHOT")),
            (("monsoon", "季候風", "季候风"), ("WMSGNL", "WMSGNL")),
        ]
        for keywords, codes in mappings:
            if any(keyword in title_lower or keyword in title for keyword in keywords):
                return codes
        return ("UNKNOWN", title[:40].upper().replace(" ", "_"))
