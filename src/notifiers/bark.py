"""Bark push notification backend."""

from __future__ import annotations

import logging
import os
from typing import Sequence
from urllib.parse import quote

import requests

from src.hko_client import WarningDetail, WarningSummary
from src.rules import get_warning_label

logger = logging.getLogger(__name__)


class BarkNotifier:
    """Send notifications through Bark HTTP API."""

    def __init__(
        self,
        device_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.device_key = str(device_key or os.environ["BARK_DEVICE_KEY"]).strip().strip("/")
        self.base_url = str(
            base_url or os.environ.get("BARK_BASE_URL", "https://api.day.app")
        ).strip().rstrip("/")

    def send(self, title: str, body: str, group: str, level: str = "active") -> None:
        compact_body = " | ".join(line.strip() for line in body.splitlines() if line.strip())
        compact_body = compact_body[:60]
        encoded_title = quote(title, safe="")
        encoded_body = quote(compact_body, safe="")
        response = requests.get(
            f"{self.base_url}/{self.device_key}/{encoded_title}/{encoded_body}",
            timeout=30,
        )
        response.raise_for_status()
        logger.info("Bark notification sent: %s", title)

    def send_immediate_alert(
        self,
        warnings: Sequence[WarningSummary],
        details: Sequence[WarningDetail] | None = None,
    ) -> None:
        labels = [get_warning_label(warning) for warning in warnings]
        title = f"StormWatch 紧急预警：{', '.join(labels)}"
        body_lines = []
        for warning in warnings:
            body_lines.append(f"{get_warning_label(warning)}，时间：{warning.issue_time}")
        self.send(title, "\n".join(body_lines).strip(), group="stormwatch-immediate")

    def send_daily_summary(
        self,
        warnings: Sequence[WarningSummary],
        details: Sequence[WarningDetail] | None = None,
        immediate_active: Sequence[WarningSummary] | None = None,
    ) -> None:
        title = "StormWatch 每日预警汇总"
        body_lines = ["09:30 HKT 汇总"]
        if immediate_active:
            body_lines.append(f"紧急预警 {len(immediate_active)} 条")
            for warning in immediate_active:
                body_lines.append(get_warning_label(warning))
        if warnings:
            body_lines.append(f"其他警告 {len(warnings)} 条")
            for warning in warnings:
                body_lines.append(get_warning_label(warning))
        else:
            body_lines.append("当前没有其他生效中的天气警告。")
        self.send(title, "\n".join(body_lines).strip(), group="stormwatch-daily", level="timeSensitive")

    @staticmethod
    def _build_detail_map(
        details: Sequence[WarningDetail],
    ) -> dict[str, WarningDetail]:
        detail_map: dict[str, WarningDetail] = {}
        for detail in details:
            detail_map[detail.statement_code] = detail
        return detail_map

