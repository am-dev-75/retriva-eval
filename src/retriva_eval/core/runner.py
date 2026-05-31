import os
import yaml
from typing import Dict, Any, List

from retriva_eval.core.config import AppConfig
from retriva_eval.core.suite import BaseSuite
from retriva_eval.core.registry import get_suite
from retriva_eval.core.schemas import MetricsRecord
from retriva_eval.utils.logging import get_logger
from retriva_eval.utils.time import generate_run_id
from retriva_eval.utils.io import read_jsonl, read_json
from retriva_eval.reporting.json_report import generate_json_summary
from retriva_eval.reporting.markdown_report import generate_markdown_summary

logger = get_logger("runner")

def run_suite_lifecycle(suite: BaseSuite, app_config: AppConfig, run_id: str, dry_run: bool):
    logger.info(f"Starting suite: {suite.name} (run_id: {run_id}, dry_run: {dry_run})")
    
    logger.info(f"[{suite.name}] Stage: prepare")
    suite.prepare(app_config, run_id, dry_run)
    
    logger.info(f"[{suite.name}] Stage: ingest")
    suite.ingest(app_config, run_id, dry_run)
    
    logger.info(f"[{suite.name}] Stage: run")
    suite.run(app_config, run_id, dry_run)
    
    logger.info(f"[{suite.name}] Stage: evaluate")
    suite.evaluate(app_config, run_id, dry_run)
    
    logger.info(f"[{suite.name}] Stage: report")
    suite.report(app_config, run_id, dry_run)
    
    logger.info(f"Finished suite: {suite.name}")

def execute_pipeline(pipeline_path: str, app_config: AppConfig, dry_run: bool):
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
        run_suite_lifecycle(suite, app_config, run_id, dry_run)
        
    # Aggregate global report
    metrics = []
    reports_dir = os.path.join(app_config.evaluation.reports_dir, run_id)
    if os.path.exists(reports_dir):
        for suite_dir in os.listdir(reports_dir):
            metrics_path = os.path.join(reports_dir, suite_dir, "metrics.json")
            if os.path.exists(metrics_path):
                import json
                with open(metrics_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    metrics.append(MetricsRecord(**data))
                    
    generate_json_summary(app_config.evaluation.reports_dir, run_id, metrics)
    generate_markdown_summary(app_config.evaluation.reports_dir, run_id, metrics)
    logger.info(f"Pipeline execution complete. Run ID: {run_id}")
