"""SendGrid email notification backend."""

from __future__ import annotations

import logging
import os
from typing import Sequence

import requests

from src.hko_client import WarningDetail, WarningSummary
from src.rules import get_warning_label

logger = logging.getLogger(__name__)

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


class SendGridNotifier:
    """Send emails via SendGrid HTTP API."""

    def __init__(
        self,
        api_key: str | None = None,
        mail_from: str | None = None,
        mail_to: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ["SENDGRID_API_KEY"]
        self.mail_from = mail_from or os.environ["MAIL_FROM"]
        self.mail_to = mail_to or os.environ["MAIL_TO"]

    def send(self, subject: str, body: str) -> None:
        payload = {
            "personalizations": [{"to": [{"email": self.mail_to}]}],
            "from": {"email": self.mail_from},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }
        response = requests.post(
            SENDGRID_API_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"SendGrid API error {response.status_code}: {response.text}"
            )
        logger.info("Email sent to %s: %s", self.mail_to, subject)

    def send_immediate_alert(
        self,
        warnings: Sequence[WarningSummary],
        details: Sequence[WarningDetail] | None = None,
    ) -> None:
        labels = [get_warning_label(warning) for warning in warnings]
        subject = f"[StormWatch] HKO 緊急預警：{', '.join(labels)}"
        body_lines = [
            "香港天文台已發出以下緊急天氣警告，請留意安全：",
            "",
        ]
        detail_map = self._build_detail_map(details or [])
        for warning in warnings:
            body_lines.append(f"▸ {get_warning_label(warning)}")
            body_lines.append(f"  發出時間：{warning.issue_time}")
            body_lines.append(f"  動作：{warning.action_code}")
            detail = detail_map.get(warning.statement_code)
            if detail and detail.contents:
                body_lines.append("  詳情：")
                for line in detail.contents[:5]:
                    body_lines.append(f"    {line}")
            body_lines.append("")
        body_lines.extend(
            [
                "---",
                "此郵件由 StormWatch 自動發送。",
                "資料來源：香港天文台開放數據 API",
            ]
        )
        self.send(subject, "\n".join(body_lines))

    def send_daily_summary(
        self,
        warnings: Sequence[WarningSummary],
        details: Sequence[WarningDetail] | None = None,
        immediate_active: Sequence[WarningSummary] | None = None,
    ) -> None:
        subject = "[StormWatch] HKO 每日天氣預警匯總 (09:30)"
        body_lines = [
            "香港天文台每日天氣預警匯總（09:30 HKT）",
            "",
        ]
        if immediate_active:
            body_lines.append("【緊急預警（現正生效）】")
            for warning in immediate_active:
                body_lines.append(
                    f"  ▸ {get_warning_label(warning)}（{warning.issue_time}）"
                )
            body_lines.append("")
        detail_map = self._build_detail_map(details or [])
        if warnings:
            body_lines.append("【其他生效中的警告】")
            for warning in warnings:
                body_lines.append(f"  ▸ {get_warning_label(warning)}")
                body_lines.append(f"    發出時間：{warning.issue_time}")
                detail = detail_map.get(warning.statement_code)
                if detail and detail.contents:
                    body_lines.append(f"    {detail.contents[0][:200]}")
            body_lines.append("")
        else:
            body_lines.append("目前沒有其他生效中的天氣警告。")
            body_lines.append("")
        body_lines.extend(
            [
                "---",
                "此郵件由 StormWatch 自動發送。",
                "資料來源：香港天文台開放數據 API",
            ]
        )
        self.send(subject, "\n".join(body_lines))

    @staticmethod
    def _build_detail_map(
        details: Sequence[WarningDetail],
    ) -> dict[str, WarningDetail]:
        detail_map: dict[str, WarningDetail] = {}
        for detail in details:
            detail_map[detail.statement_code] = detail
        return detail_map
