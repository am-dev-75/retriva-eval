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
import threading
from concurrent.futures import ThreadPoolExecutor

from retriva_eval.adapters.retriva_client import get_retriva_client
from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import (
    PredictionRecord,
    QueryRecord,
    RetrievedContext,
    TokenUsage,
)
from retriva_eval.logger import get_logger
from retriva_eval.utils.io import read_jsonl, write_jsonl

logger = get_logger("ragbench_run")


def do_run(suite_name: str, settings: Settings, run_id: str, dry_run: bool) -> None:
    reports_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    queries_path = os.path.join(reports_dir, "queries.jsonl")
    predictions_path = os.path.join(reports_dir, "predictions.jsonl")

    queries = read_jsonl(queries_path, QueryRecord)
    retriva = get_retriva_client(settings)
    total = len(queries)

    def _predict(q: QueryRecord) -> PredictionRecord:
        if dry_run:
            logger.info(f"[Dry Run] Mocking Retriva call for query: {q.id}")
            return PredictionRecord(
                query_id=q.id,
                suite=suite_name,
                question=q.question,
                answer=f"Mock answer for {q.question}",
                retrieved_contexts=[
                    RetrievedContext(id=ctx_id, text=f"Context {ctx_id}", score=0.9, rank=1)
                    for ctx_id in q.reference_context_ids
                ],
                latency_ms=120,
                tokens=TokenUsage(prompt=10, completion=20, total=30),
            )
        return retriva.query(q, run_id)

    # The `run` stage hits the full Retriva retrieval+generation pipeline, which
    # is heavier than ingestion/judging, so it gets its own (lower) concurrency
    # knob. Each retriva.query call builds its own httpx.Client, so concurrent
    # invocations are thread-safe. Results are placed back by index to preserve
    # the original query ordering regardless of completion order.
    max_workers = max(1, settings.eval_run_concurrency)
    predictions: list = [None] * total
    completed = 0
    progress_lock = threading.Lock()

    def _run_index(i: int) -> None:
        nonlocal completed
        predictions[i] = _predict(queries[i])
        with progress_lock:
            completed += 1
            if completed % 10 == 0 or completed == total:
                logger.info(f"  Run progress: {completed}/{total} queries")

    logger.info(f"Running {total} queries with concurrency={max_workers}...")
    if max_workers == 1:
        for i in range(total):
            _run_index(i)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # list() forces consumption so exceptions (if any) surface here.
            list(executor.map(_run_index, range(total)))

    write_jsonl(predictions_path, predictions)
    logger.info(f"Wrote {len(predictions)} predictions to {predictions_path}")
