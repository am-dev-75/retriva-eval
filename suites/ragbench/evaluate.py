# Copyright (C) 2026 Andrea Marson (am.dev.75@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from typing import Dict, List

import yaml

from retriva_eval.adapters.ragbench_judge import RAGBENCH_METRICS, RagbenchJudge
from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import MetricsRecord, PredictionRecord, QueryRecord
from retriva_eval.logger import get_logger
from retriva_eval.utils.io import read_jsonl, write_json

logger = get_logger("ragbench_evaluate")

_SUITE_DIR = os.path.dirname(__file__)


def _load_suite_yaml() -> dict:
    path = os.path.join(_SUITE_DIR, "suite.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _aggregate_by_subset(per_sample: List[dict]) -> Dict[str, Dict[str, float]]:
    """Group per-sample scores by ``subset`` and average them."""
    buckets: Dict[str, List[dict]] = {}
    for row in per_sample:
        key = row.get("subset") or "_unknown"
        buckets.setdefault(key, []).append(row)

    out: Dict[str, Dict[str, float]] = {}
    for subset, rows in buckets.items():
        n = len(rows)
        out[subset] = {
            metric: float(sum(r[metric] for r in rows) / n) for metric in RAGBENCH_METRICS
        }
        out[subset]["sample_count"] = float(n)
    return out


def do_evaluate(
    suite_name: str, settings: Settings, run_id: str, dry_run: bool
) -> MetricsRecord:
    reports_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    queries = read_jsonl(os.path.join(reports_dir, "queries.jsonl"), QueryRecord)
    predictions = read_jsonl(
        os.path.join(reports_dir, "predictions.jsonl"), PredictionRecord
    )

    suite_cfg = _load_suite_yaml()
    metrics_list = list(suite_cfg.get("metrics") or RAGBENCH_METRICS)
    thresholds = dict(suite_cfg.get("thresholds") or {})

    if dry_run:
        logger.info("[Dry Run] Mocking RAGBench LLM-as-judge metrics.")
        metrics = {m: 0.80 for m in metrics_list}
        per_subset = {"mock": {m: 0.80 for m in metrics_list}}
        per_subset["mock"]["sample_count"] = float(len(predictions))
    else:
        judge = RagbenchJudge(settings)
        result = judge.evaluate(predictions, queries)
        metrics = {m: result["metrics"].get(m, 0.0) for m in metrics_list}
        per_subset = _aggregate_by_subset(result["per_sample"])

        # Persist per-sample and per-subset breakdowns alongside the standard
        # metrics.json so users can drill down by RAGBench subset.
        write_json(
            os.path.join(reports_dir, "metrics_by_subset.json"),
            {"per_subset": per_subset, "per_sample": result["per_sample"]},
        )

    # Status: fail if any metric drops below its threshold.
    status = "pass"
    for m, val in metrics.items():
        thr = thresholds.get(m)
        if thr is not None and val < thr:
            status = "fail"
            break

    metrics_record = MetricsRecord(
        suite=suite_name,
        run_id=run_id,
        sample_count=len(predictions),
        metrics=metrics,
        thresholds=thresholds,
        status=status,
    )

    write_json(os.path.join(reports_dir, "metrics.json"), metrics_record)

    # Concise per-subset log line for quick visibility in the pipeline log.
    if per_subset:
        logger.info("Per-subset RAGBench metrics:")
        for subset, scores in sorted(per_subset.items()):
            scores_fmt = ", ".join(
                f"{m}={scores.get(m, 0.0):.3f}" for m in RAGBENCH_METRICS
            )
            logger.info(
                f"  [{subset}] n={int(scores.get('sample_count', 0))} {scores_fmt}"
            )

    logger.info(f"Evaluation complete. Status: {status}")
    return metrics_record
