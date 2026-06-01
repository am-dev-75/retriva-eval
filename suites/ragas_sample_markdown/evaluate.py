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
from typing import Dict
from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import QueryRecord, PredictionRecord, MetricsRecord
from retriva_eval.adapters.ragas_eval import RagasAdapter
from retriva_eval.utils.io import read_jsonl, write_json
from retriva_eval.logger import get_logger

logger = get_logger("ragas_suite_evaluate")

def do_evaluate(suite_name: str, settings: Settings, run_id: str, dry_run: bool) -> MetricsRecord:
    reports_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    queries = read_jsonl(os.path.join(reports_dir, "queries.jsonl"), QueryRecord)
    predictions = read_jsonl(os.path.join(reports_dir, "predictions.jsonl"), PredictionRecord)
    
    # Read metrics to run from config or assume defaults
    # In a real scenario, this comes from suite.yaml
    metrics_list = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    thresholds = {"faithfulness": 0.75, "answer_relevancy": 0.70, "context_precision": 0.70, "context_recall": 0.70}
    
    if dry_run:
        logger.info("[Dry Run] Mocking Ragas evaluation metrics.")
        metrics = {m: 0.80 for m in metrics_list}
    else:
        ragas = RagasAdapter(settings, metrics_list)
        metrics = ragas.evaluate(predictions, queries)
        
    # Calculate status based on thresholds
    status = "pass"
    for m, val in metrics.items():
        if m in thresholds and val < thresholds[m]:
            status = "fail"
            break
            
    metrics_record = MetricsRecord(
        suite=suite_name,
        run_id=run_id,
        sample_count=len(predictions),
        metrics=metrics,
        thresholds=thresholds,
        status=status
    )
    
    write_json(os.path.join(reports_dir, "metrics.json"), metrics_record)
    logger.info(f"Evaluation complete. Status: {status}")
    return metrics_record
