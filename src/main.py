"""StormWatch entry point for extreme weather notifications."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from src.hko_client import HKOClient
from src.notifiers.bark import BarkNotifier
from src.notifiers.sendgrid_mail import SendGridNotifier
from src.notifiers.smtp_mail import SMTPNotifier
from src.rules import filter_immediate_alerts
from src.state import load_state, save_state

logger = logging.getLogger(__name__)


def build_notifier():
    """
    Choose notification backend.

    Default is Bark.
    Set EMAIL_BACKEND=bark|smtp|sendgrid to override.
    """
    backend = os.environ.get("EMAIL_BACKEND", "bark").strip().lower()
    if backend == "bark":
        return BarkNotifier()
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
    """Check for extreme weather alerts and send notifications for new events."""
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
        logger.info("No new extreme weather alerts to notify.")
        save_state(state, state_path)
        return 0

    logger.info(
        "Found %d new extreme alert(s): %s",
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="StormWatch: HKO extreme weather alert monitor",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="immediate",
        choices=["immediate"],
        help="Run mode (only immediate is supported)",
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
        help="Fetch and evaluate without sending notifications or updating state",
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
        return run_immediate(args.state_path, args.lang, args.dry_run)
    except Exception:
        logger.exception("StormWatch job failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
