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
import json
import time
import yaml
from typing import Dict, Any, List, Optional, Tuple

from retriva_eval.core.config import Settings
from retriva_eval.core.suite import BaseSuite
from retriva_eval.core.registry import get_suite
from retriva_eval.core.schemas import MetricsRecord, APIEndpointStats
from retriva_eval.core.profiler import APIProfiler
from retriva_eval.logger import get_logger
from retriva_eval.utils.time import generate_run_id
from retriva_eval.utils.io import read_jsonl, read_json
from retriva_eval.reporting.json_report import generate_json_summary
from retriva_eval.reporting.markdown_report import generate_markdown_summary

logger = get_logger("runner")


def _aggregate_and_report(
    settings: Settings, run_id: str, total_time_ms: int
) -> Tuple[List[MetricsRecord], str]:
    """Collect per-suite metrics.json files for a run, then write the global
    JSON and Markdown summaries.

    Returns the list of :class:`MetricsRecord` and the path to ``summary.md``.
    Shared by both the single-suite (`run-suite`) and pipeline (`run-cycle`)
    entry points so that both always produce a summary.
    """
    metrics: List[MetricsRecord] = []
    reports_dir = os.path.join(settings.eval_reports_dir, run_id)
    if os.path.exists(reports_dir):
        for suite_dir in sorted(os.listdir(reports_dir)):
            metrics_path = os.path.join(reports_dir, suite_dir, "metrics.json")
            if os.path.exists(metrics_path):
                with open(metrics_path, "r", encoding="utf-8") as f:
                    metrics.append(MetricsRecord(**json.load(f)))

    api_stats_raw = APIProfiler.get_instance().get_statistics()
    api_stats = [APIEndpointStats(**stat) for stat in api_stats_raw]

    generate_json_summary(settings.eval_reports_dir, run_id, metrics, total_time_ms, api_stats)
    summary_path = generate_markdown_summary(
        settings.eval_reports_dir, run_id, metrics, total_time_ms, api_stats
    )
    return metrics, summary_path

def run_suite_lifecycle(
    suite: BaseSuite,
    settings: Settings,
    run_id: str,
    dry_run: bool,
    portion: float = 1.0,
    seed: Optional[int] = None,
    generate_summary: bool = True,
) -> Optional[str]:
    """Run a single suite through its full lifecycle.

    When ``generate_summary`` is True (the default, used by the ``run-suite``
    command), the global JSON/Markdown summaries are produced at the end and
    the path to ``summary.md`` is returned. The pipeline runner passes
    ``generate_summary=False`` because it aggregates across all suites itself.
    """
    start_time = time.time()
    logger.info(
        f"Starting suite: {suite.name} (run_id: {run_id}, dry_run: {dry_run}, "
        f"portion: {portion}, seed: {seed if seed is not None else 'suite-default'})"
    )
    
    logger.info(f"[{suite.name}] Stage: prepare")
    suite.prepare(settings, run_id, dry_run, portion=portion, seed=seed)
    
    logger.info(f"[{suite.name}] Stage: ingest")
    suite.ingest(settings, run_id, dry_run, portion=portion, seed=seed)
    
    logger.info(f"[{suite.name}] Stage: run")
    suite.run(settings, run_id, dry_run, portion=portion, seed=seed)
    
    logger.info(f"[{suite.name}] Stage: evaluate")
    suite.evaluate(settings, run_id, dry_run, portion=portion, seed=seed)
    
    logger.info(f"[{suite.name}] Stage: report")
    suite.report(settings, run_id, dry_run, portion=portion, seed=seed)
    
    logger.info(f"Finished suite: {suite.name}")

    summary_path = None
    if generate_summary:
        total_time_ms = int((time.time() - start_time) * 1000)
        _, summary_path = _aggregate_and_report(settings, run_id, total_time_ms)
        logger.info(f"Wrote run summary to {summary_path}")
    return summary_path

def execute_pipeline(
    pipeline_path: str,
    settings: Settings,
    dry_run: bool,
    portion: float = 1.0,
    seed: Optional[int] = None,
):
    start_time = time.time()
    
    if not os.path.exists(pipeline_path):
        logger.error(f"Pipeline file not found: {pipeline_path}")
        raise FileNotFoundError(f"Pipeline file not found: {pipeline_path}")
        
    with open(pipeline_path, "r", encoding="utf-8") as f:
        pipeline = yaml.safe_load(f) or {}
        
    run_id = generate_run_id()
    logger.info(f"Starting pipeline '{pipeline.get('name', 'unnamed')}' with run_id {run_id}")
    
    suites = pipeline.get("suites", [])
    for suite_def in suites:
        name = suite_def.get("name")
        if not suite_def.get("enabled", True):
            logger.info(f"Skipping disabled suite: {name}")
            continue
            
        suite = get_suite(name)
        # The pipeline aggregates across all suites itself, so suppress the
        # per-suite summary generation inside the lifecycle.
        run_suite_lifecycle(
            suite, settings, run_id, dry_run, portion=portion, seed=seed,
            generate_summary=False,
        )
        
    total_time_ms = int((time.time() - start_time) * 1000)
    _aggregate_and_report(settings, run_id, total_time_ms)
    logger.info(f"Pipeline execution complete. Run ID: {run_id}")
    return run_id
