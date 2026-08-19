"""Bark push notification backend."""

from __future__ import annotations

import logging
import os
from typing import Sequence

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
        payload = {
            "title": title,
            "body": body,
            "group": group,
            "level": level,
        }
        response = requests.post(
            f"{self.base_url}/{self.device_key}",
            data=payload,
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
        detail_map = self._build_detail_map(details or [])
        for warning in warnings:
            body_lines.append(f"{get_warning_label(warning)}")
            body_lines.append(f"发出时间：{warning.issue_time}")
            detail = detail_map.get(warning.statement_code)
            if detail and detail.contents:
                body_lines.append(detail.contents[0])
            body_lines.append("")
        body_lines.append("数据来源：香港天文台")
        self.send(title, "\n".join(body_lines).strip(), group="stormwatch-immediate")

    def send_daily_summary(
        self,
        warnings: Sequence[WarningSummary],
        details: Sequence[WarningDetail] | None = None,
        immediate_active: Sequence[WarningSummary] | None = None,
    ) -> None:
        title = "StormWatch 每日预警汇总"
        body_lines = ["09:30 HKT 汇总", ""]
        if immediate_active:
            body_lines.append("紧急预警（当前生效）:")
            for warning in immediate_active:
                body_lines.append(f"- {get_warning_label(warning)}")
            body_lines.append("")
        detail_map = self._build_detail_map(details or [])
        if warnings:
            body_lines.append("其他警告:")
            for warning in warnings:
                body_lines.append(f"- {get_warning_label(warning)}")
                detail = detail_map.get(warning.statement_code)
                if detail and detail.contents:
                    body_lines.append(f"  {detail.contents[0][:120]}")
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

