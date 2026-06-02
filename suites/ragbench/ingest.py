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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

import httpx

from retriva_eval.adapters.retriva_client import get_retriva_client
from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import CorpusRecord
from retriva_eval.logger import get_logger
from retriva_eval.utils.io import read_jsonl

logger = get_logger("ragbench_ingest")


def do_ingest(suite_name: str, settings: Settings, run_id: str, dry_run: bool) -> None:
    reports_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    corpus_path = os.path.join(reports_dir, "corpus.jsonl")
    corpus = read_jsonl(corpus_path, CorpusRecord)

    if dry_run:
        logger.info(f"[Dry Run] Skipping ingestion of {len(corpus)} records.")
        return

    client = get_retriva_client(settings)
    logger.info(
        f"Ingesting {len(corpus)} documents into KB '{settings.eval_knowledge_base}'..."
    )

    # Auto-create the knowledge base if it doesn't exist.
    kb_id = settings.eval_knowledge_base
    core_url = settings.core_ingestion_base_url.rstrip("/")
    try:
        with httpx.Client(timeout=10.0) as http:
            resp = http.post(
                f"{core_url}/api/v2/kbs",
                json={
                    "kb_id": kb_id,
                    "name": kb_id,
                    "description": "Auto-created for eval (ragbench)",
                },
            )
            if resp.status_code not in (201, 409):
                logger.warning(
                    f"Failed to auto-create KB {kb_id}: {resp.status_code} {resp.text}"
                )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Could not reach Core API to auto-create KB: {exc}")

    data_dir = os.path.join(reports_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    # Materialize all markdown files up front (cheap, local I/O).
    documents = []  # list of (file_path, document_id)
    for record in corpus:
        file_path = os.path.join(data_dir, f"{record.document_id}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(record.text)
        documents.append((file_path, record.document_id))

    total = len(documents)

    # Two-level speedup over naive one-doc-per-batch ingestion:
    #   1. Group many files into a single Gateway batch (eval_ingest_batch_size)
    #      so we poll status once per *batch* instead of once per *document*.
    #   2. Submit multiple batches concurrently (eval_ingest_concurrency).
    batch_size = max(1, settings.eval_ingest_batch_size)
    max_workers = max(1, settings.eval_ingest_concurrency)
    groups = [documents[i : i + batch_size] for i in range(0, total, batch_size)]
    logger.info(
        f"Uploading {total} documents in {len(groups)} batch(es) of up to "
        f"{batch_size}, with batch-concurrency={max_workers}..."
    )

    def _ingest_group(group):
        # ingest_documents on the Gateway client creates one batch and polls
        # it once for the whole group. The default base implementation falls
        # back to per-document ingestion for adapters without batch support.
        client.ingest_documents(group, run_id=run_id, suite_name=suite_name)
        return len(group)

    done_docs = 0
    done_groups = 0
    failures = 0
    total_groups = len(groups)

    def _log_progress(group: List[Tuple[str, str]]) -> None:
        nonlocal done_docs, done_groups
        done_docs += len(group)
        done_groups += 1
        logger.info(
            f"  Ingest progress: {done_groups}/{total_groups} batches "
            f"({done_docs}/{total} docs)"
        )

    if max_workers == 1:
        for group in groups:
            try:
                _ingest_group(group)
            except Exception as exc:  # noqa: BLE001
                failures += 1
                logger.error(f"Failed to ingest a batch of {len(group)} docs: {exc}")
            _log_progress(group)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_group = {
                executor.submit(_ingest_group, group): group for group in groups
            }
            for future in as_completed(future_to_group):
                group = future_to_group[future]
                try:
                    future.result()
                except Exception as exc:  # noqa: BLE001
                    failures += 1
                    logger.error(
                        f"Failed to ingest a batch of {len(group)} docs: {exc}"
                    )
                _log_progress(group)

    if failures:
        logger.warning(
            f"Ingestion finished with {failures}/{total_groups} failed batch(es)."
        )
    else:
        logger.info("Ingestion complete.")
