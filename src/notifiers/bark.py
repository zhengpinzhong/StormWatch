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

    def send(self, title: str, body: str, group: str = "stormwatch", level: str = "timeSensitive") -> None:
        # Prefer JSON POST to /push so detailed Chinese bodies are not truncated by URL length.
        payload = {
            "device_key": self.device_key,
            "title": title,
            "body": body,
            "group": group,
            "level": level,
        }
        response = requests.post(
            f"{self.base_url}/push",
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=30,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Bark API error {response.status_code}: {response.text}"
            )
        logger.info("Bark notification sent: %s", title)

    def send_immediate_alert(
        self,
        warnings: Sequence[WarningSummary],
        details: Sequence[WarningDetail] | None = None,
    ) -> None:
        labels = [get_warning_label(warning) for warning in warnings]
        title = f"StormWatch 極端天氣：{', '.join(labels)}"
        detail_map = self._build_detail_map(details or [])
        body_lines = [
            "香港天文台已發出極端天氣警告，請留意安全：",
            "",
        ]
        for warning in warnings:
            body_lines.append(f"▸ {get_warning_label(warning)}")
            body_lines.append(f"  代碼：{warning.subtype}")
            body_lines.append(f"  動作：{warning.action_code}")
            body_lines.append(f"  發出時間：{warning.issue_time}")
            if warning.update_time and warning.update_time != warning.issue_time:
                body_lines.append(f"  更新時間：{warning.update_time}")
            if warning.expire_time:
                body_lines.append(f"  預計結束：{warning.expire_time}")
            if warning.warning_type:
                body_lines.append(f"  類型：{warning.warning_type}")
            detail = detail_map.get(warning.statement_code)
            if detail and detail.contents:
                body_lines.append("  詳情：")
                for line in detail.contents[:8]:
                    text = str(line).strip()
                    if text:
                        body_lines.append(f"    {text}")
            body_lines.append("")
        body_lines.extend(
            [
                "---",
                "資料來源：香港天文台開放數據 API",
                "此通知由 StormWatch 自動發送",
            ]
        )
        self.send(title, "\n".join(body_lines).strip(), group="stormwatch-immediate")

    @staticmethod
    def _build_detail_map(
        details: Sequence[WarningDetail],
    ) -> dict[str, WarningDetail]:
        detail_map: dict[str, WarningDetail] = {}
        for detail in details:
            detail_map[detail.statement_code] = detail
        return detail_map
