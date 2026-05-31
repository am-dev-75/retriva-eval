import time
import httpx
from typing import Dict, Any, List

from retriva_eval.core.config import RetrivaConfig
from retriva_eval.core.schemas import QueryRecord, PredictionRecord, RetrievedContext, TokenUsage
from retriva_eval.utils.logging import get_logger

logger = get_logger("retriva_adapter")

class RetrivaAdapter:
    def __init__(self, config: RetrivaConfig):
        self.config = config
        self.endpoint = config.endpoint
        
    def query(self, query_record: QueryRecord, run_id: str) -> PredictionRecord:
        start_time = time.time()
        error_msg = None
        answer = ""
        retrieved_contexts: List[RetrievedContext] = []
        tokens = TokenUsage()
        
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                payload = {
                    "query": query_record.question,
                    "top_k": self.config.default_top_k,
                    "metadata_filter": {
                        "run_id": run_id,
                        "suite": query_record.suite
                    }
                }
                
                response = client.post(self.endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
                
                answer = data.get("answer", "")
                
                for idx, ctx in enumerate(data.get("contexts", [])):
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
            logger.error(f"Error querying Retriva for query {query_record.id}: {e}")
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
