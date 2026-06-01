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
from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import QueryRecord, PredictionRecord, RetrievedContext, TokenUsage
from retriva_eval.adapters.retriva_client import get_retriva_client
from retriva_eval.utils.io import read_jsonl, write_jsonl
from retriva_eval.logger import get_logger

logger = get_logger("ragas_suite_run")

def do_run(suite_name: str, settings: Settings, run_id: str, dry_run: bool) -> None:
    reports_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    queries_path = os.path.join(reports_dir, "queries.jsonl")
    predictions_path = os.path.join(reports_dir, "predictions.jsonl")
    
    queries = read_jsonl(queries_path, QueryRecord)
    predictions = []
    
    retriva = get_retriva_client(settings)
    
    for q in queries:
        if dry_run:
            logger.info(f"[Dry Run] Mocking Retriva call for query: {q.id}")
            pred = PredictionRecord(
                query_id=q.id,
                suite=suite_name,
                question=q.question,
                answer=f"Mock answer for {q.question}",
                retrieved_contexts=[
                    RetrievedContext(id=ctx_id, text=f"Context {ctx_id}", score=0.9, rank=1)
                    for ctx_id in q.reference_context_ids
                ],
                latency_ms=120,
                tokens=TokenUsage(prompt=10, completion=20, total=30)
            )
        else:
            pred = retriva.query(q, run_id)
        predictions.append(pred)
        
    write_jsonl(predictions_path, predictions)
    logger.info(f"Wrote {len(predictions)} predictions to {predictions_path}")
