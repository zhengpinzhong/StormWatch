"""StormWatch entry point for immediate and daily notification jobs."""

from __future__ import annotations

import argparse
import logging
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from src.hko_client import HKOClient
from src.notifiers.sendgrid_mail import SendGridNotifier
from src.notifiers.smtp_mail import SMTPNotifier
from src.rules import filter_daily_warnings, filter_immediate_alerts, is_immediate_alert
from src.state import AppState, load_state, save_state

HKT = timezone(timedelta(hours=8))
logger = logging.getLogger(__name__)


def build_notifier():
    """
    Choose email backend.

    Default is SMTP (so project still works even if SendGrid onboarding is blocked).
    Set EMAIL_BACKEND=sendgrid to force SendGrid.
    """

    backend = os.environ.get("EMAIL_BACKEND", "smtp").strip().lower()
    if backend == "sendgrid":
        return SendGridNotifier()
    return SMTPNotifier()


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def run_immediate(state_path: Path, lang: str, dry_run: bool = False) -> int:
    """Check for immediate alerts and send notifications for new events."""
    client = HKOClient(lang=lang)
    state = load_state(state_path)
    warnings = client.fetch_warning_summary()
    immediate = filter_immediate_alerts(warnings)

    new_alerts = [
        warning
        for warning in immediate
        if not state.has_notified(warning.dedupe_key)
    ]

    if not new_alerts:
        logger.info("No new immediate alerts to notify.")
        save_state(state, state_path)
        return 0

    logger.info(
        "Found %d new immediate alert(s): %s",
        len(new_alerts),
        ", ".join(warning.subtype for warning in new_alerts),
    )

    if dry_run:
        for warning in new_alerts:
            logger.info("DRY RUN would notify: %s", warning.dedupe_key)
        return 0

    details = client.fetch_warning_info()
    notifier = build_notifier()
    notifier.send_immediate_alert(new_alerts, details)

    for warning in new_alerts:
        state.mark_notified(warning.dedupe_key)

    save_state(state, state_path)
    return 0


def run_daily(state_path: Path, lang: str, dry_run: bool = False) -> int:
    """Send daily summary of non-immediate active warnings at 09:30 HKT."""
    today = datetime.now(HKT).strftime("%Y-%m-%d")
    client = HKOClient(lang=lang)
    state = load_state(state_path)

    if state.last_daily_sent == today:
        logger.info("Daily summary already sent for %s.", today)
        return 0

    warnings = client.fetch_warning_summary()
    daily_warnings = filter_daily_warnings(warnings)
    immediate_active = [w for w in warnings if is_immediate_alert(w)]

    logger.info(
        "Daily summary: %d other warning(s), %d immediate active.",
        len(daily_warnings),
        len(immediate_active),
    )

    if dry_run:
        logger.info("DRY RUN would send daily summary for %s.", today)
        return 0

    details = client.fetch_warning_info()
    notifier = build_notifier()
    notifier.send_daily_summary(daily_warnings, details, immediate_active)

    state.last_daily_sent = today
    save_state(state, state_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="StormWatch: HKO weather warning monitor",
    )
    parser.add_argument(
        "mode",
        choices=["immediate", "daily"],
        help="Run mode: immediate alert check or daily summary",
    )
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("data/state.json"),
        help="Path to state file (default: data/state.json)",
    )
    parser.add_argument(
        "--lang",
        default="tc",
        choices=["en", "tc", "sc"],
        help="HKO API language (default: tc)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and evaluate without sending emails or updating state",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    try:
        if args.mode == "immediate":
            return run_immediate(args.state_path, args.lang, args.dry_run)
        return run_daily(args.state_path, args.lang, args.dry_run)
    except Exception:
        logger.exception("StormWatch job failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
