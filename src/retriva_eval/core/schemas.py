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

class APIEndpointStats(BaseModel):
    endpoint: str
    invocations: int
    avg_latency_ms: float

class PipelineRunSummary(BaseModel):
    run_id: str
    global_status: str
    total_execution_time_ms: int
    api_stats: List[APIEndpointStats]
    suites: List[MetricsRecord]
