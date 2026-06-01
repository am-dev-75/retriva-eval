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

import sys
from types import ModuleType

# --- MONKEY PATCH FOR RAGAS 0.4.x ---
# Ragas 0.4.x has a broken import to deprecated langchain_community.chat_models.vertexai
# We stub it out here before importing ragas to allow it to load successfully.
stub = ModuleType('langchain_community.chat_models.vertexai')
class ChatVertexAI: pass
stub.ChatVertexAI = ChatVertexAI
sys.modules['langchain_community.chat_models.vertexai'] = stub
stub2 = ModuleType('langchain_community.llms')
class VertexAI: pass
stub2.VertexAI = VertexAI
sys.modules['langchain_community.llms'] = stub2
# ------------------------------------

from typing import List, Dict, Any

try:
    from ragas import evaluate
    from datasets import Dataset
    from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall
    from ragas.llms import llm_factory
    from ragas.embeddings.base import embedding_factory
    from openai import OpenAI
    RAGAS_AVAILABLE = True
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"Ragas import failed: {e}")
    RAGAS_AVAILABLE = False

from retriva_eval.core.schemas import PredictionRecord, QueryRecord
from retriva_eval.core.config import Settings
from retriva_eval.logger import get_logger

logger = get_logger("ragas_adapter")

class RagasAdapter:
    def __init__(self, settings: Settings, metrics: List[str]):
        self.settings = settings
        self.metrics_names = metrics
        self.evaluator_llm = None
        
        if RAGAS_AVAILABLE and not self.settings.openai_api_key:
            logger.warning("Ragas is available but OPENAI_API_KEY is not set. Real evaluation will fail.")
            
    def _get_ragas_metrics(self) -> List[Any]:
        if not RAGAS_AVAILABLE:
            raise ImportError("Ragas is not installed correctly or has missing dependencies.")
            
        if not self.evaluator_llm:
            if not self.settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required for Ragas evaluation.")
            client_kwargs = {
                "api_key": self.settings.openai_api_key, 
            }
            if self.settings.openai_base_url:
                client_kwargs["base_url"] = self.settings.openai_base_url
            
            client = OpenAI(**client_kwargs)
            self.evaluator_llm = llm_factory(model=self.settings.llm_model, provider=self.settings.llm_provider, client=client)
            
            embed_api_key = self.settings.embedding_api_key or self.settings.openai_api_key
            embed_kwargs = {"api_key": embed_api_key}
            if self.settings.embedding_base_url:
                embed_kwargs["base_url"] = self.settings.embedding_base_url
            
            embed_client = OpenAI(**embed_kwargs)
            self.evaluator_embeddings = embedding_factory(
                provider=self.settings.embedding_provider, 
                model=self.settings.embedding_model, 
                client=embed_client
            )
            
            # --- MONKEY PATCH FOR RAGAS 0.4.x EMBEDDINGS BUG ---
            # Ragas 0.4.x OpenAIEmbeddings uses 'embed_text' but AnswerRelevancy calls 'embed_query'
            if not hasattr(self.evaluator_embeddings, "embed_query") and hasattr(self.evaluator_embeddings, "embed_text"):
                self.evaluator_embeddings.embed_query = self.evaluator_embeddings.embed_text
            if not hasattr(self.evaluator_embeddings, "embed_documents") and hasattr(self.evaluator_embeddings, "embed_texts"):
                self.evaluator_embeddings.embed_documents = self.evaluator_embeddings.embed_texts
            if not hasattr(self.evaluator_embeddings, "aembed_query") and hasattr(self.evaluator_embeddings, "aembed_text"):
                self.evaluator_embeddings.aembed_query = self.evaluator_embeddings.aembed_text
            if not hasattr(self.evaluator_embeddings, "aembed_documents") and hasattr(self.evaluator_embeddings, "aembed_texts"):
                self.evaluator_embeddings.aembed_documents = self.evaluator_embeddings.aembed_texts
            # ---------------------------------------------------
            
        metric_map = {
            "faithfulness": Faithfulness(llm=self.evaluator_llm),
            "answer_relevancy": AnswerRelevancy(llm=self.evaluator_llm, embeddings=self.evaluator_embeddings),
            "context_precision": ContextPrecision(llm=self.evaluator_llm),
            "context_recall": ContextRecall(llm=self.evaluator_llm),
        }
        
        return [metric_map[m] for m in self.metrics_names if m in metric_map]

    def evaluate(self, predictions: List[PredictionRecord], queries: List[QueryRecord]) -> Dict[str, float]:
        if not RAGAS_AVAILABLE or not self.settings.openai_api_key:
            logger.warning("Ragas is not fully configured (missing API key or library). Skipping true evaluation.")
            return {m: 0.0 for m in self.metrics_names}
            
        if not predictions:
            return {m: 0.0 for m in self.metrics_names}
            
        # Map queries for easy lookup
        query_map = {q.id: q for q in queries}
        
        # Prepare HuggingFace Dataset
        data = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": []
        }
        
        for p in predictions:
            q = query_map.get(p.query_id)
            if not q:
                continue
            
            data["question"].append(p.question)
            data["answer"].append(p.answer)
            data["contexts"].append([c.text for c in p.retrieved_contexts])
            data["ground_truth"].append(q.reference_answer)
            
        dataset = Dataset.from_dict(data)
        metrics = self._get_ragas_metrics()
        
        # Run evaluation
        logger.info(f"Running real Ragas evaluation with metrics: {self.metrics_names} using model: {self.settings.llm_model}")
        try:
            # Ragas 0.4 evaluate returns an EvaluationResult object
            result = evaluate(dataset=dataset, metrics=metrics, llm=self.evaluator_llm)
            
            final_scores = {}
            for m in self.metrics_names:
                try:
                    # __getitem__ returns a list of floats (one per row)
                    scores = result[m]
                    valid_scores = [s for s in scores if s is not None and str(s).lower() != 'nan']
                    final_scores[m] = float(sum(valid_scores) / len(valid_scores)) if valid_scores else 0.0
                except Exception as e:
                    logger.warning(f"Could not extract score for {m}: {e}")
                    final_scores[m] = 0.0
            return final_scores
        except Exception as e:
            logger.error(f"Ragas evaluation failed: {e}")
            return {m: 0.0 for m in self.metrics_names}
