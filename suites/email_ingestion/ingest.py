"""Ingest stage: send emails to the retriva-email-agent-connector via swaks."""

import json
import os
import shutil
import subprocess
import time
from typing import Optional

import yaml

from retriva_eval.core.config import Settings
from retriva_eval.logger import get_logger

logger = get_logger("email_ingestion.ingest")


def _load_suite_config() -> dict:
    path = os.path.join("suites", "email_ingestion", "suite.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_smtp_config(suite_cfg: dict) -> tuple[str, int, str]:
    """Resolve SMTP host/port/from from env vars or suite config."""
    smtp_cfg = suite_cfg.get("smtp", {})
    host = os.environ.get("EMAIL_EVAL_SMTP_HOST", smtp_cfg.get("host", "127.0.0.1"))
    port = int(os.environ.get("EMAIL_EVAL_SMTP_PORT", smtp_cfg.get("port", 8025)))
    from_addr = smtp_cfg.get("from_address", "eval@retriva-eval.local")
    return host, port, from_addr


def _send_email_swaks(smtp_host: str, smtp_port: int, from_addr: str,
                      to_addr: str, subject: str, body: str,
                      message_id: str, date_str: str,
                      timeout: int = 180) -> bool:
    """Send a single email via swaks. Returns True on success.

    The timeout must be long enough to accommodate the connector's
    wait_for_job polling (default 120s) plus upload overhead.
    """
    swaks = shutil.which("swaks")
    if not swaks:
        logger.error("swaks not found in PATH. Install with: sudo apt install swaks")
        return False

    cmd = [
        swaks,
        "--server", f"{smtp_host}:{smtp_port}",
        "--from", from_addr,
        "--to", to_addr,
        "--header", f"Subject: {subject}",
        "--h-Message-Id", message_id,
        "--header", f"Date: {date_str}",
        "--body", body,
        "--timeout", str(timeout),
    ]

    logger.debug(f"Executing: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10,  # subprocess timeout > swaks timeout
        )
        if result.returncode == 0:
            return True
        else:
            logger.error(
                f"swaks failed for {message_id}: rc={result.returncode}\n"
                f"stderr: {result.stderr[:500]}"
            )
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"swaks timed out for {message_id} (after {timeout+10}s)")
        return False
    except Exception as e:
        logger.error(f"swaks error for {message_id}: {e}")
        return False


def do_ingest(
    suite_name: str,
    settings: Settings,
    run_id: str,
    dry_run: bool,
    portion: float = 1.0,
    seed: Optional[int] = None,
):
    """Send all selected emails via swaks to the email-agent-connector."""
    report_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    selected_path = os.path.join(report_dir, "selected_emails.jsonl")

    if not os.path.exists(selected_path):
        raise FileNotFoundError(
            f"Selected emails not found: {selected_path}. Run prepare stage first."
        )

    messages = []
    with open(selected_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                messages.append(json.loads(line))

    suite_cfg = _load_suite_config()
    smtp_host, smtp_port, from_addr = _resolve_smtp_config(suite_cfg)

    logger.info(
        f"Sending {len(messages)} emails to {smtp_host}:{smtp_port} via swaks..."
    )

    sent_results = []
    sent_count = 0
    failed_count = 0

    for i, msg in enumerate(messages):
        if dry_run:
            logger.debug(
                f"[dry-run] Email {i+1}/{len(messages)}:\n"
                f"  Message-ID: {msg['message_id']}\n"
                f"  From: {from_addr}\n"
                f"  To: {msg['to']}\n"
                f"  Subject: {msg['subject']}\n"
                f"  Date: {msg['date']}\n"
                f"  Field: {msg.get('field', '?')}\n"
                f"  Address pattern: {msg.get('address_pattern', '?')}\n"
                f"  Expected tags: {msg.get('expected_tags', {})}\n"
                f"  Expected KB: {msg.get('expected_kb', '')}\n"
                f"  Question: {msg.get('question', '')}\n"
                f"  Expected answer: {msg.get('expected_answer', '')}\n"
                f"  Body:\n{msg['body']}"
            )
            logger.info(f"[dry-run] Would send email {i+1}/{len(messages)}: {msg['subject']!r}")
            sent_results.append({
                "id": msg["id"],
                "message_id": msg["message_id"],
                "to": msg["to"],
                "subject": msg["subject"],
                "sent": True,
                "dry_run": True,
                "address_pattern": msg["address_pattern"],
                "expected_tags": msg["expected_tags"],
                "expected_kb": msg.get("expected_kb", ""),
            })
            sent_count += 1
            continue

        # Log full message details at DEBUG level
        logger.debug(
            f"Sending email {i+1}/{len(messages)}:\n"
            f"  Message-ID: {msg['message_id']}\n"
            f"  From: {from_addr}\n"
            f"  To: {msg['to']}\n"
            f"  Subject: {msg['subject']}\n"
            f"  Date: {msg['date']}\n"
            f"  Field: {msg.get('field', '?')}\n"
            f"  Address pattern: {msg.get('address_pattern', '?')}\n"
            f"  Expected tags: {msg.get('expected_tags', {})}\n"
            f"  Expected KB: {msg.get('expected_kb', '')}\n"
            f"  Question: {msg.get('question', '')}\n"
            f"  Expected answer: {msg.get('expected_answer', '')}\n"
            f"  Body:\n{msg['body']}"
        )

        success = _send_email_swaks(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            from_addr=from_addr,
            to_addr=msg["to"],
            subject=msg["subject"],
            body=msg["body"],
            message_id=msg["message_id"],
            date_str=msg["date"],
        )

        if success:
            logger.info(f"  ✓ Email {i+1}/{len(messages)} sent: {msg['subject']!r}")
        else:
            logger.error(f"  ✗ Email {i+1}/{len(messages)} failed: {msg['subject']!r}")

        sent_results.append({
            "id": msg["id"],
            "message_id": msg["message_id"],
            "to": msg["to"],
            "subject": msg["subject"],
            "sent": success,
            "address_pattern": msg["address_pattern"],
            "expected_tags": msg["expected_tags"],
            "expected_kb": msg.get("expected_kb", ""),
        })

        if success:
            sent_count += 1
        else:
            failed_count += 1

        if (i + 1) % 10 == 0:
            logger.info(f"  Progress: {i+1}/{len(messages)} sent ({sent_count} ok, {failed_count} failed)")

        # Small delay to avoid overwhelming the SMTP server
        time.sleep(0.1)

    # Write send results
    results_path = os.path.join(report_dir, "send_results.jsonl")
    with open(results_path, "w", encoding="utf-8") as f:
        for r in sent_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    logger.info(
        f"Ingest complete: {sent_count}/{len(messages)} emails sent successfully "
        f"({failed_count} failed) → {results_path}"
    )
