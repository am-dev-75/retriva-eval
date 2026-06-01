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
from retriva_eval.core.schemas import CorpusRecord
from retriva_eval.adapters.retriva_client import get_retriva_client
from retriva_eval.utils.io import read_jsonl
from retriva_eval.logger import get_logger

logger = get_logger("ragas_amnesty_qa_ingest")

def do_ingest(suite_name: str, settings: Settings, run_id: str, dry_run: bool) -> None:
    reports_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    corpus_path = os.path.join(reports_dir, "corpus.jsonl")
    corpus = read_jsonl(corpus_path, CorpusRecord)
    
    if dry_run:
        logger.info(f"[Dry Run] Skipping ingestion of {len(corpus)} records.")
        return
        
    client = get_retriva_client(settings)
    logger.info(f"Ingesting {len(corpus)} documents into KB '{settings.eval_knowledge_base}'...")
    
    import httpx
    # Auto-create the knowledge base if it doesn't exist
    kb_id = settings.eval_knowledge_base
    core_url = settings.core_ingestion_base_url.rstrip("/")
    try:
        with httpx.Client(timeout=10.0) as http:
            resp = http.post(
                f"{core_url}/api/v2/kbs",
                json={"kb_id": kb_id, "name": kb_id, "description": "Auto-created for eval"}
            )
            if resp.status_code not in (201, 409):
                logger.warning(f"Failed to auto-create KB {kb_id}: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.warning(f"Could not reach Core API to auto-create KB: {e}")

    data_dir = os.path.join(reports_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    for record in corpus:
        # Create a physical markdown file for the gateway to upload
        file_path = os.path.join(data_dir, f"{record.document_id}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(record.text)
            
        client.ingest_document(file_path, document_id=record.document_id, run_id=run_id, suite_name=suite_name)
        
    logger.info("Ingestion complete.")
