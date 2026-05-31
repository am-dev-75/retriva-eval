from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class CorpusRecord(BaseModel):
    id: str
    suite: str
    document_id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class QueryRecord(BaseModel):
    id: str
    suite: str
    question: str
    reference_answer: str
    reference_context_ids: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TokenUsage(BaseModel):
    prompt: Optional[int] = None
    completion: Optional[int] = None
    total: Optional[int] = None

class RetrievedContext(BaseModel):
    id: str
    text: str
    score: float
    rank: int

class PredictionRecord(BaseModel):
    query_id: str
    suite: str
    question: str
    answer: str
    retrieved_contexts: List[RetrievedContext]
    latency_ms: int
    tokens: TokenUsage = Field(default_factory=TokenUsage)
    error: Optional[str] = None

class MetricsRecord(BaseModel):
    suite: str
    run_id: str
    sample_count: int
    metrics: Dict[str, float]
    thresholds: Dict[str, float]
    status: str
