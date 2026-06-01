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

from abc import ABC, abstractmethod
from typing import List
import time
import json
import httpx
import os

from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import QueryRecord, PredictionRecord, RetrievedContext, TokenUsage
from retriva_eval.core.profiler import APIProfiler
from retriva_eval.logger import get_logger

logger = get_logger("retriva_client")

class BaseRetrivaClient(ABC):
    def __init__(self, settings: Settings):
        self.settings = settings

    @abstractmethod
    def query(self, query_record: QueryRecord, run_id: str) -> PredictionRecord:
        pass

    @abstractmethod
    def ingest_document(self, file_path: str, document_id: str, run_id: str, suite_name: str) -> None:
        pass

class GatewayHttpClient(BaseRetrivaClient):
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.base_url = self.settings.gateway_base_url
        self.chat_url = f"{self.base_url.rstrip('/')}{self.settings.gateway_chat_path}"
        # Gateway ingestion uses a batch-based workflow under /gateway/ingestion/batches
        self.ingestion_base = f"{self.base_url.rstrip('/')}{self.settings.gateway_ingestion_path}"

    def query(self, query_record: QueryRecord, run_id: str) -> PredictionRecord:
        start_time = time.time()
        error_msg = None
        answer = ""
        retrieved_contexts: List[RetrievedContext] = []
        tokens = TokenUsage()
        
        try:
            with httpx.Client(timeout=self.settings.retriva_timeout_seconds) as client:
                payload = {
                    "message": query_record.question,
                    "kb_ids": [self.settings.eval_knowledge_base],
                    "filters": {
                        "run_id": run_id,
                        "suite": query_record.suite
                    },
                    "metadata_filter_mode": self.settings.eval_metadata_filtering_mode,
                    "stream": False
                }
                
                
                t_start = time.time()
                response = client.post(self.chat_url, json=payload)
                t_end = time.time()
                APIProfiler.get_instance().record_call(self.settings.gateway_chat_path, int((t_end - t_start) * 1000))
                
                response.raise_for_status()
                data = response.json()
                
                answer = data.get("content", "")
                for idx, ctx in enumerate(data.get("citations", [])):
                    retrieved_contexts.append(
                        RetrievedContext(
                            id=ctx.get("id", f"ctx_{idx}"),
                            text=ctx.get("text", ""),
                            score=ctx.get("score", 0.0),
                            rank=idx + 1
                        )
                    )
                usage = data.get("usage", {})
                tokens.prompt = usage.get("prompt_tokens")
                tokens.completion = usage.get("completion_tokens")
                tokens.total = usage.get("total_tokens")
                
        except Exception as e:
            logger.error(f"Gateway HTTP Error querying Retriva for {query_record.id}: {e}")
            error_msg = str(e)
            
        latency_ms = int((time.time() - start_time) * 1000)
        
        return PredictionRecord(
            query_id=query_record.id,
            suite=query_record.suite,
            question=query_record.question,
            answer=answer,
            retrieved_contexts=retrieved_contexts,
            latency_ms=latency_ms,
            tokens=tokens,
            error=error_msg
        )

    def ingest_document(self, file_path: str, document_id: str, run_id: str, suite_name: str) -> None:
        """Ingest a document via the Gateway batch-based ingestion workflow.
        
        Steps:
          1. POST /gateway/ingestion/batches  -> creates a batch, returns batch_id
          2. POST /gateway/ingestion/batches/{batch_id}/files  -> uploads the file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        metadata = self.settings.parsed_eval_metadata.copy()
        metadata["run_id"] = run_id
        metadata["document_id"] = document_id
        metadata["suite"] = suite_name
        
        try:
            with httpx.Client(timeout=self.settings.retriva_timeout_seconds) as client:
                # Step 1: Create a batch
                batch_url = f"{self.ingestion_base}/batches"
                batch_payload = {"metadata": metadata}
                
                t_start = time.time()
                resp = client.post(batch_url, json=batch_payload)
                t_end = time.time()
                APIProfiler.get_instance().record_call(f"{self.settings.gateway_ingestion_path}/batches", int((t_end - t_start) * 1000))
                
                resp.raise_for_status()
                batch_id = resp.json()["batch_id"]
                logger.debug(f"Created ingestion batch {batch_id}")
                
                # Step 2: Upload the file into the batch
                upload_url = f"{self.ingestion_base}/batches/{batch_id}/files"
                with open(file_path, "rb") as f:
                    files = {"file": (os.path.basename(file_path), f, "text/markdown")}
                    data = {
                        "source_path": file_path,
                        "user_metadata": json.dumps(metadata),
                        "kb_id": self.settings.eval_knowledge_base,
                    }
                    
                    t_start = time.time()
                    resp = client.post(upload_url, files=files, data=data)
                    t_end = time.time()
                    APIProfiler.get_instance().record_call(f"{self.settings.gateway_ingestion_path}/batches/{{id}}/files", int((t_end - t_start) * 1000))
                    
                    resp.raise_for_status()
                    
                # Step 3: Wait for ingestion to complete
                batch_status_url = f"{self.ingestion_base}/batches/{batch_id}"
                for _ in range(30):
                    t_start = time.time()
                    resp = client.get(batch_status_url)
                    t_end = time.time()
                    APIProfiler.get_instance().record_call(f"{self.settings.gateway_ingestion_path}/batches/{{id}}", int((t_end - t_start) * 1000))
                    
                    resp.raise_for_status()
                    batch_data = resp.json()
                    
                    files_list = batch_data.get("files", [])
                    if not files_list:
                        break
                        
                    all_done = True
                    for f in files_list:
                        if f.get("status") not in ["completed", "failed", "error"]:
                            all_done = False
                            break
                            
                    if all_done:
                        break
                        
                    time.sleep(2.0)
                    
                logger.info(f"Successfully ingested {file_path} via Gateway (batch {batch_id}).")
        except Exception as e:
            logger.error(f"Gateway HTTP Error ingesting {file_path}: {e}")
            raise


class CoreOpenAIClient(BaseRetrivaClient):
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.chat_base_url = self.settings.core_chat_base_url
        self.ingest_base_url = self.settings.core_ingestion_base_url
        self.chat_url = f"{self.chat_base_url.rstrip('/')}{self.settings.core_chat_path}"
        self.ingest_url = f"{self.ingest_base_url.rstrip('/')}{self.settings.core_ingestion_path}"

    def query(self, query_record: QueryRecord, run_id: str) -> PredictionRecord:
        start_time = time.time()
        error_msg = None
        answer = ""
        retrieved_contexts: List[RetrievedContext] = []
        tokens = TokenUsage()
        
        try:
            with httpx.Client(timeout=self.settings.retriva_timeout_seconds) as client:
                payload = {
                    "messages": [{"role": "user", "content": query_record.question}],
                    "metadata_filter": {
                        "run_id": run_id,
                        "suite": query_record.suite
                    }
                }
                
                t_start = time.time()
                response = client.post(self.chat_url, json=payload)
                t_end = time.time()
                APIProfiler.get_instance().record_call(self.settings.core_chat_path, int((t_end - t_start) * 1000))
                
                response.raise_for_status()
                data = response.json()
                
                choices = data.get("choices", [])
                if choices:
                    answer = choices[0].get("message", {}).get("content", "")
                    
                retriva_extra = data.get("retriva", {})
                for idx, ctx in enumerate(retriva_extra.get("contexts", [])):
                    retrieved_contexts.append(
                        RetrievedContext(
                            id=ctx.get("id", f"ctx_{idx}"),
                            text=ctx.get("text", ""),
                            score=ctx.get("score", 0.0),
                            rank=idx + 1
                        )
                    )
                usage = data.get("usage", {})
                tokens.prompt = usage.get("prompt_tokens")
                tokens.completion = usage.get("completion_tokens")
                tokens.total = usage.get("total_tokens")
                
        except Exception as e:
            logger.error(f"Core OpenAI Error querying Retriva for {query_record.id}: {e}")
            error_msg = str(e)
            
        latency_ms = int((time.time() - start_time) * 1000)
        
        return PredictionRecord(
            query_id=query_record.id,
            suite=query_record.suite,
            question=query_record.question,
            answer=answer,
            retrieved_contexts=retrieved_contexts,
            latency_ms=latency_ms,
            tokens=tokens,
            error=error_msg
        )

    def ingest_document(self, file_path: str, document_id: str, run_id: str, suite_name: str) -> None:
        """Ingest a document directly via Core v2 upload endpoint.
        
        POST /api/v2/documents/upload with multipart file, source_path, and user_metadata.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        metadata = self.settings.parsed_eval_metadata.copy()
        metadata["run_id"] = run_id
        metadata["document_id"] = document_id
        metadata["suite"] = suite_name
        
        try:
            with httpx.Client(timeout=self.settings.retriva_timeout_seconds) as client:
                with open(file_path, "rb") as f:
                    files = {"file": (os.path.basename(file_path), f, "text/markdown")}
                    data = {
                        "source_path": file_path,
                        "user_metadata": json.dumps(metadata),
                        "kb_id": self.settings.eval_knowledge_base,
                    }
                    
                    t_start = time.time()
                    response = client.post(self.ingest_url, files=files, data=data)
                    t_end = time.time()
                    APIProfiler.get_instance().record_call(self.settings.core_ingestion_path, int((t_end - t_start) * 1000))
                    
                    response.raise_for_status()
                    
                    job_id = response.json().get("job_id")
                    if job_id:
                        job_status_url = f"{self.ingest_base_url.rstrip('/')}/api/v2/jobs/{job_id}"
                        for _ in range(30):
                            t_start = time.time()
                            resp = client.get(job_status_url)
                            t_end = time.time()
                            APIProfiler.get_instance().record_call("/api/v2/jobs/{id}", int((t_end - t_start) * 1000))
                            
                            resp.raise_for_status()
                            if resp.json().get("status") in ["completed", "failed", "error"]:
                                break
                            time.sleep(2.0)
                            
                    logger.info(f"Successfully ingested {file_path} via Core.")
        except Exception as e:
            logger.error(f"Core OpenAI Error ingesting {file_path}: {e}")
            raise


def get_retriva_client(settings: Settings) -> BaseRetrivaClient:
    if settings.retriva_adapter == "gateway_http":
        return GatewayHttpClient(settings)
    elif settings.retriva_adapter == "core_openai_chat":
        return CoreOpenAIClient(settings)
    else:
        raise ValueError(f"Unknown Retriva adapter: {settings.retriva_adapter}")
