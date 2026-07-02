"""Prepare stage: load the email dataset and sub-sample it."""

import json
import os
import random
from typing import Optional

from retriva_eval.core.config import Settings
from retriva_eval.logger import get_logger

logger = get_logger("email_ingestion.prepare")

_DEFAULT_SEED = 42
_DATASET_PATH = os.path.join("suites", "email_ingestion", "data", "emails.jsonl")


def _load_dataset() -> list[dict]:
    """Load the full 100-message dataset from JSONL."""
    if not os.path.exists(_DATASET_PATH):
        raise FileNotFoundError(
            f"Email dataset not found at {_DATASET_PATH}. "
            f"Run: python suites/email_ingestion/generate_dataset.py"
        )
    messages = []
    with open(_DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                messages.append(json.loads(line))
    logger.info(f"Loaded {len(messages)} messages from {_DATASET_PATH}")
    return messages


def _rewrite_kb_in_address(address: str, old_kb: str, new_kb: str) -> str:
    """Replace the KB segment in a plus-addressed email.

    The address format is:
        retriva+collection+kb+tag1+tag2@domain

    Only replaces when ``old_kb`` appears as the KB segment (position 2
    after the prefix).  Addresses without a KB segment are returned as-is.
    """
    if not old_kb or old_kb not in address:
        return address
    local, sep, domain = address.rpartition("@")
    if not sep:
        return address
    # Split local-part on the first '+' to get prefix and rest.
    prefix, plus, rest = local.partition("+")
    if not plus:
        return address
    # Segments: [collection, kb, tag1, ...]
    segments = rest.split("+")
    # KB is segment index 1 (second segment after prefix).
    if len(segments) >= 2 and segments[1] == old_kb:
        segments[1] = new_kb
    return f"{prefix}+{'+'.join(segments)}@{domain}"


def do_prepare(
    suite_name: str,
    settings: Settings,
    run_id: str,
    dry_run: bool,
    portion: float = 1.0,
    seed: Optional[int] = None,
):
    """Load the dataset, sub-sample based on portion/seed, write selected.jsonl."""
    effective_seed = seed if seed is not None else _DEFAULT_SEED
    messages = _load_dataset()

    if portion < 1.0:
        n = max(1, int(round(len(messages) * portion)))
        rng = random.Random(effective_seed)
        indices = sorted(rng.sample(range(len(messages)), n))
        messages = [messages[i] for i in indices]

    # When --target-kb is set, rewrite the KB segment in each email address
    # so the connector routes ingestion to the requested KB.
    target_kb = settings.email_target_kb
    if target_kb:
        rewritten = 0
        for msg in messages:
            old_kb = msg.get("expected_kb", "")
            if old_kb and old_kb != target_kb:
                msg["to"] = _rewrite_kb_in_address(msg["to"], old_kb, target_kb)
                msg["expected_kb"] = target_kb
                rewritten += 1
        if rewritten:
            logger.info(
                f"Rewrote KB segment in {rewritten}/{len(messages)} email "
                f"addresses → target_kb={target_kb}"
            )

    # Write the selected messages to the run's report directory.
    report_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    os.makedirs(report_dir, exist_ok=True)
    output_path = os.path.join(report_dir, "selected_emails.jsonl")
    with open(output_path, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    logger.info(
        f"Prepared {len(messages)} emails for run {run_id} "
        f"(portion={portion}, seed={effective_seed}) → {output_path}"
    )

    if dry_run:
        logger.info("[dry-run] Skipping actual email sending and verification.")

