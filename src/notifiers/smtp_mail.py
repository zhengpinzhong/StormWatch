"""SMTP email notification backend (for Outlook / Office365 / other SMTP servers)."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Sequence

from src.hko_client import WarningDetail, WarningSummary
from src.rules import get_warning_label

logger = logging.getLogger(__name__)


class SMTPNotifier:
    """Send emails via SMTP."""

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_username: str | None = None,
        smtp_password: str | None = None,
        mail_from: str | None = None,
        mail_to: str | None = None,
    ) -> None:
        self.smtp_host = str(smtp_host or os.environ["SMTP_HOST"]).strip().strip('"').strip("'")
        self.smtp_port = self._parse_port(
            smtp_port or os.environ.get("SMTP_PORT", os.environ.get("SMTP_PORT_STR"))
        )
        self.smtp_username = str(smtp_username or os.environ["SMTP_USERNAME"]).strip()
        self.smtp_password = str(smtp_password or os.environ["SMTP_PASSWORD"])
        self.mail_from = str(mail_from or os.environ["MAIL_FROM"]).strip()
        self.mail_to = str(mail_to or os.environ["MAIL_TO"]).strip()

    @staticmethod
    def _parse_port(raw_port: object | None) -> int:
        """Parse SMTP port, tolerating quoted or whitespace-padded values."""
        if raw_port is None:
            return 587
        port = str(raw_port).strip().strip('"').strip("'")
        if not port:
            return 587
        return int(port)

    def send(self, subject: str, body: str) -> None:
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = self.mail_from
        msg["To"] = self.mail_to

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
            server.ehlo()
            # Outlook 通常 587 需要 STARTTLS
            try:
                server.starttls()
                server.ehlo()
            except smtplib.SMTPException:
                # 如果服务器不要求 STARTTLS，仍允许继续登录/发信
                pass
            server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.mail_from, [self.mail_to], msg.as_string())

        logger.info("Email sent to %s: %s", self.mail_to, subject)

    def send_immediate_alert(
        self,
        warnings: Sequence[WarningSummary],
        details: Sequence[WarningDetail] | None = None,
    ) -> None:
        labels = [get_warning_label(warning) for warning in warnings]
        subject = f"[StormWatch] HKO 極端天氣：{', '.join(labels)}"
        body_lines = [
            "香港天文台已發出極端天氣警告，請留意安全：",
            "",
        ]

        detail_map = self._build_detail_map(details or [])
        for warning in warnings:
            body_lines.append(f"▸ {get_warning_label(warning)}")
            body_lines.append(f"  代碼：{warning.subtype}")
            body_lines.append(f"  動作：{warning.action_code}")
            body_lines.append(f"  發出時間：{warning.issue_time}")
            if warning.update_time and warning.update_time != warning.issue_time:
                body_lines.append(f"  更新時間：{warning.update_time}")
            if warning.expire_time:
                body_lines.append(f"  預計結束：{warning.expire_time}")
            detail = detail_map.get(warning.statement_code)
            if detail and detail.contents:
                body_lines.append("  詳情：")
                for line in detail.contents[:8]:
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

    @staticmethod
    def _build_detail_map(
        details: Sequence[WarningDetail],
    ) -> dict[str, WarningDetail]:
        detail_map: dict[str, WarningDetail] = {}
        for detail in details:
            detail_map[detail.statement_code] = detail
        return detail_map

