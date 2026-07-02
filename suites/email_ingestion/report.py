"""Report stage: write a markdown summary for the email ingestion suite."""

import json
import os
from typing import Optional

from retriva_eval.core.config import Settings
from retriva_eval.logger import get_logger

logger = get_logger("email_ingestion.report")


def do_report(
    suite_name: str,
    settings: Settings,
    run_id: str,
    dry_run: bool,
    portion: float = 1.0,
    seed: Optional[int] = None,
):
    """Write a markdown report for the email ingestion suite."""
    report_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)

    metrics_path = os.path.join(report_dir, "metrics.json")
    breakdown_path = os.path.join(report_dir, "metrics_by_pattern.json")

    if not os.path.exists(metrics_path):
        logger.warning(f"No metrics.json found at {metrics_path}, skipping report.")
        return

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    per_pattern = {}
    if os.path.exists(breakdown_path):
        with open(breakdown_path, "r", encoding="utf-8") as f:
            per_pattern = json.load(f).get("per_pattern", {})

    status_emoji = "✅" if metrics.get("status") == "pass" else "❌"
    m = metrics.get("metrics", {})
    t = metrics.get("thresholds", {})

    def _metric_row(label, key, threshold_key):
        val = m.get(key, 0)
        thresh = t.get(threshold_key, 0)
        # Format as percentage if value is a rate/accuracy (0..1 float)
        is_pct = isinstance(val, float) and 0.0 <= val <= 1.0 and (
            key.endswith("_rate") or key.endswith("_accuracy")
        )
        if is_pct:
            val_str = f"{val:.2%}"
            thresh_str = f"{thresh:.2%}" if isinstance(thresh, float) else str(thresh)
        else:
            val_str = str(val)
            thresh_str = "N/A"
        ok = val >= thresh if threshold_key in t else True
        emoji = "✅" if ok else "❌"
        return f"| {label} | {val_str} | {thresh_str} | {emoji} |"

    lines = [
        f"# Email Ingestion Suite — {status_emoji} {metrics.get('status', 'unknown').upper()}",
        "",
        f"- **Run ID:** {run_id}",
        f"- **Samples:** {metrics.get('sample_count', 0)}",
        f"- **Emails Sent:** {m.get('emails_sent', 0)}",
        f"- **Emails Ingested:** {m.get('emails_ingested', 0)}",
        f"- **Queries Answered:** {m.get('queries_answered', 0)}",
        "",
        "## Metrics",
        "",
        "| Metric | Value | Threshold | Status |",
        "|---|---|---|---|",
        _metric_row("Ingestion Success Rate", "ingestion_success_rate", "ingestion_success_rate"),
        _metric_row("Address Decode Accuracy", "address_decode_accuracy", "address_decode_accuracy"),
        _metric_row("Query Answer Rate", "query_answer_rate", "query_answer_rate"),
        _metric_row("Query Relevance Rate", "query_relevance_rate", "query_relevance_rate"),
        "",
    ]

    if per_pattern:
        lines.extend([
            "## Per-Pattern Breakdown",
            "",
            "| Pattern | Total | Ingested | Ingestion Rate | Decode Accuracy | Answered | Answer Rate | Relevance Rate |",
            "|---|---|---|---|---|---|---|---|",
        ])
        for pattern, stats in sorted(per_pattern.items()):
            lines.append(
                f"| {pattern} | {stats['total']} | {stats['ingested']} | "
                f"{stats['ingestion_rate']:.2%} | {stats['decode_accuracy']:.2%} | "
                f"{stats.get('answered', 0)} | {stats.get('answer_rate', 0):.2%} | "
                f"{stats.get('relevance_rate', 0):.2%} |"
            )
        lines.append("")

    report_path = os.path.join(report_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Report written to {report_path}")
