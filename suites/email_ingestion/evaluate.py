"""Evaluate stage: compute metrics from verification results."""

import json
import os
from typing import Optional

import yaml

from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import MetricsRecord
from retriva_eval.logger import get_logger
from retriva_eval.utils.io import write_json

logger = get_logger("email_ingestion.evaluate")


def _load_suite_config() -> dict:
    path = os.path.join("suites", "email_ingestion", "suite.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def do_evaluate(
    suite_name: str,
    settings: Settings,
    run_id: str,
    dry_run: bool,
    portion: float = 1.0,
    seed: Optional[int] = None,
):
    """Compute ingestion success rate and address decode accuracy."""
    report_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    verification_path = os.path.join(report_dir, "verification_results.jsonl")

    if not os.path.exists(verification_path):
        raise FileNotFoundError(
            f"Verification results not found: {verification_path}. Run stage first."
        )

    results = []
    with open(verification_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))

    suite_cfg = _load_suite_config()
    thresholds = suite_cfg.get("thresholds", {})

    total = len(results)
    if total == 0:
        logger.warning("No verification results to evaluate.")
        metrics_values = {
            "emails_sent": 0,
            "emails_ingested": 0,
            "ingestion_success_rate": 0.0,
            "address_decode_accuracy": 0.0,
            "queries_answered": 0,
            "query_answer_rate": 0.0,
            "query_relevance_rate": 0.0,
        }
    else:
        emails_ingested = sum(1 for r in results if r.get("ingested", False))
        queries_answered = sum(1 for r in results if r.get("answered", False))
        answers_relevant = sum(1 for r in results if r.get("answer_relevant", False))

        # Address decode accuracy: tags and kb must match expected values
        decode_correct = sum(
            1 for r in results
            if r.get("ingested", False)
            and r.get("tags_match", False)
            and r.get("kb_match", False)
        )

        ingestion_success_rate = emails_ingested / total
        address_decode_accuracy = decode_correct / total if total > 0 else 0.0
        query_answer_rate = queries_answered / total if total > 0 else 0.0
        query_relevance_rate = answers_relevant / total if total > 0 else 0.0

        metrics_values = {
            "emails_sent": total,
            "emails_ingested": emails_ingested,
            "ingestion_success_rate": round(ingestion_success_rate, 4),
            "address_decode_accuracy": round(address_decode_accuracy, 4),
            "queries_answered": queries_answered,
            "query_answer_rate": round(query_answer_rate, 4),
            "query_relevance_rate": round(query_relevance_rate, 4),
        }

    # Determine pass/fail
    threshold_success = thresholds.get("ingestion_success_rate", 0.95)
    threshold_decode = thresholds.get("address_decode_accuracy", 0.95)
    threshold_query = thresholds.get("query_answer_rate", 0.90)
    threshold_relevance = thresholds.get("query_relevance_rate", 0.80)
    status = "pass"
    if metrics_values["ingestion_success_rate"] < threshold_success:
        status = "fail"
    if metrics_values["address_decode_accuracy"] < threshold_decode:
        status = "fail"
    if metrics_values["query_answer_rate"] < threshold_query:
        status = "fail"
    if metrics_values["query_relevance_rate"] < threshold_relevance:
        status = "fail"

    # Per-pattern breakdown
    from collections import defaultdict
    pattern_stats = defaultdict(lambda: {
        "total": 0, "ingested": 0, "tags_ok": 0,
        "answered": 0, "relevant": 0,
    })
    for r in results:
        pattern = r.get("address_pattern", "unknown")
        pattern_stats[pattern]["total"] += 1
        if r.get("ingested", False):
            pattern_stats[pattern]["ingested"] += 1
            if r.get("tags_match", False) and r.get("kb_match", False):
                pattern_stats[pattern]["tags_ok"] += 1
        if r.get("answered", False):
            pattern_stats[pattern]["answered"] += 1
        if r.get("answer_relevant", False):
            pattern_stats[pattern]["relevant"] += 1

    per_pattern = {}
    for pattern, stats in sorted(pattern_stats.items()):
        per_pattern[pattern] = {
            "total": stats["total"],
            "ingested": stats["ingested"],
            "ingestion_rate": round(stats["ingested"] / stats["total"], 4) if stats["total"] else 0.0,
            "decode_accuracy": round(stats["tags_ok"] / stats["total"], 4) if stats["total"] else 0.0,
            "answered": stats["answered"],
            "answer_rate": round(stats["answered"] / stats["total"], 4) if stats["total"] else 0.0,
            "relevance_rate": round(stats["relevant"] / stats["total"], 4) if stats["total"] else 0.0,
        }

    # Write per-pattern breakdown
    breakdown_path = os.path.join(report_dir, "metrics_by_pattern.json")
    write_json(breakdown_path, {"per_pattern": per_pattern})

    # Write metrics.json
    metrics_record = MetricsRecord(
        suite=suite_name,
        run_id=run_id,
        sample_count=total,
        metrics=metrics_values,
        thresholds={
            "ingestion_success_rate": threshold_success,
            "address_decode_accuracy": threshold_decode,
            "query_answer_rate": threshold_query,
            "query_relevance_rate": threshold_relevance,
        },
        status=status,
    )

    metrics_path = os.path.join(report_dir, "metrics.json")
    write_json(metrics_path, metrics_record.model_dump())

    logger.info(f"Metrics: {metrics_values} (status={status})")
    logger.info(f"Per-pattern breakdown → {breakdown_path}")

    if status == "fail":
        logger.warning(
            f"Suite FAILED: ingestion_success_rate={metrics_values['ingestion_success_rate']} "
            f"(threshold={threshold_success}), "
            f"address_decode_accuracy={metrics_values['address_decode_accuracy']} "
            f"(threshold={threshold_decode}), "
            f"query_answer_rate={metrics_values['query_answer_rate']} "
            f"(threshold={threshold_query}), "
            f"query_relevance_rate={metrics_values['query_relevance_rate']} "
            f"(threshold={threshold_relevance})"
        )
        # Log failing patterns
        for pattern, stats in per_pattern.items():
            if (stats["ingestion_rate"] < 1.0 or stats["decode_accuracy"] < 1.0
                    or stats["answer_rate"] < 1.0 or stats["relevance_rate"] < 1.0):
                logger.warning(
                    f"  Pattern '{pattern}': ingestion={stats['ingestion_rate']}, "
                    f"decode={stats['decode_accuracy']}, "
                    f"answer={stats['answer_rate']}, "
                    f"relevance={stats['relevance_rate']} "
                    f"({stats['ingested']}/{stats['total']})"
                )
