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

from typing import Optional, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

VERSION = "0.1.0"

class Settings(BaseSettings):
    # Retriva Client
    retriva_adapter: str = "gateway_http"
    retriva_timeout_seconds: int = 120
    retriva_default_top_k: int = 5
    
    # Gateway
    gateway_base_url: str = "http://localhost:8080"
    gateway_chat_path: str = "/gateway/chat"
    gateway_ingestion_path: str = "/gateway/ingestion"
    gateway_kbs_path: str = "/gateway/kbs"
    
    # Core
    core_chat_base_url: str = "http://localhost:8001"
    core_ingestion_base_url: str = "http://localhost:8000"
    core_chat_path: str = "/v1/chat/completions"
    core_ingestion_path: str = "/api/v2/documents/upload"
    
    # Evaluation
    eval_knowledge_base: str = "eval-ragas-sample-markdown"
    eval_metadata: str = '{"retriva_eval": "true", "suite": "ragas_sample_markdown"}'
    eval_metadata_filtering_mode: str = "hard"
    eval_reports_dir: str = "reports"
    eval_fail_on_threshold_breach: bool = True
    
    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_collection_name: str = "retriva_eval_manual"
    qdrant_vector_size: int = 1536
    qdrant_distance: str = "cosine"
    qdrant_lifecycle_mode: str = "manual_existing"
    qdrant_delete_on_completion: bool = False
    
    # LLM
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    
    # Embeddings
    embedding_api_key: Optional[str] = None
    embedding_base_url: Optional[str] = None
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def parsed_eval_metadata(self) -> Dict[str, str]:
        try:
            return json.loads(self.eval_metadata)
        except json.JSONDecodeError:
            return {}

settings = Settings()
