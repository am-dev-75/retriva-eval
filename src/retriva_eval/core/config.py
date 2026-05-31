import os
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseModel

class RetrivaConfig(BaseModel):
    adapter: str = "http"
    endpoint_env: str = "RETRIVA_ENDPOINT"
    timeout_seconds: int = 60
    default_top_k: int = 5
    
    @property
    def endpoint(self) -> str:
        return os.getenv(self.endpoint_env, "http://localhost:8080/query")

class QdrantLifecycleConfig(BaseModel):
    mode: str = "manual_existing"
    delete_on_completion: bool = False

class QdrantConfig(BaseModel):
    url_env: str = "QDRANT_URL"
    api_key_env: str = "QDRANT_API_KEY"
    collection_name: str = "retriva_eval_manual"
    vector_size: int = 1536
    distance: str = "cosine"
    collection_lifecycle: QdrantLifecycleConfig = QdrantLifecycleConfig()
    
    @property
    def url(self) -> str:
        return os.getenv(self.url_env, "http://localhost:6333")
    
    @property
    def api_key(self) -> Optional[str]:
        return os.getenv(self.api_key_env)

class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o-mini"

class EvaluationConfig(BaseModel):
    reports_dir: str = "reports"
    fail_on_threshold_breach: bool = True

class AppConfig(BaseModel):
    retriva: RetrivaConfig = RetrivaConfig()
    qdrant: QdrantConfig = QdrantConfig()
    llm: LLMConfig = LLMConfig()
    evaluation: EvaluationConfig = EvaluationConfig()

def load_config(config_path: Optional[str] = None) -> AppConfig:
    data: Dict[str, Any] = {}
    default_path = "configs/default.yaml"
    
    if os.path.exists(default_path):
        with open(default_path, "r", encoding="utf-8") as f:
            data.update(yaml.safe_load(f) or {})
            
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            override_data = yaml.safe_load(f) or {}
            # Deep merge (simplified for now)
            for k, v in override_data.items():
                if isinstance(v, dict) and k in data and isinstance(data[k], dict):
                    data[k].update(v)
                else:
                    data[k] = v
                    
    return AppConfig(**data)
