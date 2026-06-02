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

"""LLM-as-judge implementation of the four native RAGBench metrics.

The metric definitions follow the conventions of the RAGBench paper
(Friel et al., 2024, "RAGBench: Explainable Benchmark for Retrieval-Augmented
Generation Systems"):

* **Context Relevance** -- the fraction of retrieved context chunks that are
  relevant to answering the question (0..1).
* **Context Utilization** -- of the *relevant* retrieved chunks, the fraction
  whose information is actually leveraged by the generated answer (0..1).
* **Completeness** -- the fraction of answer-relevant information available
  in the retrieved contexts that is present in the generated answer (0..1).
* **Adherence** -- whether the generated answer is fully grounded in (i.e.
  does not contradict or add information beyond) the retrieved contexts.
  Per-sample value is binary (0 or 1); the aggregate is the mean.

The judge is an LLM accessed via the OpenAI-compatible API already configured
in :class:`retriva_eval.core.config.Settings`. Each query is judged in a
single structured-JSON call, keeping latency and cost manageable.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import PredictionRecord, QueryRecord
from retriva_eval.logger import get_logger

logger = get_logger("ragbench_judge")


RAGBENCH_METRICS = [
    "context_relevance",
    "context_utilization",
    "completeness",
    "adherence",
]


_JUDGE_SYSTEM_PROMPT = """You are a strict, impartial evaluator for a retrieval-augmented \
generation (RAG) system. You will be given:

* a user question,
* an ordered list of retrieved context chunks (each prefixed with [i]),
* a reference (gold) answer,
* the answer produced by the RAG system under evaluation.

Score the system answer along four dimensions:

1. context_relevance: For each retrieved chunk, decide whether it contains any \
information that helps answer the question. Output the list of indices (0-based) \
of chunks that are relevant.

2. context_utilization: Of the chunks you marked as relevant in (1), list the \
indices of those whose information is actually used (referenced, paraphrased or \
quoted) in the system answer.

3. completeness: Considering the information present across the relevant chunks \
(and the reference answer), what fraction of the information needed to fully \
answer the question is present in the system answer? Output a single float in \
[0, 1] with two decimals.

4. adherence: Is the entire system answer supported by the retrieved chunks \
(no hallucinated, contradicting, or unsupported claims)? Output a boolean.

Return ONLY a JSON object, no prose, with this exact schema:

{
  "relevant_chunk_indices": [int, ...],
  "utilized_chunk_indices": [int, ...],
  "completeness": float,
  "adherence": bool
}
"""


def _build_user_prompt(
    question: str,
    contexts: List[str],
    reference_answer: str,
    system_answer: str,
) -> str:
    ctx_block = "\n\n".join(f"[{i}] {c}" for i, c in enumerate(contexts)) or "[no contexts retrieved]"
    return (
        f"QUESTION:\n{question}\n\n"
        f"RETRIEVED CONTEXTS:\n{ctx_block}\n\n"
        f"REFERENCE ANSWER:\n{reference_answer}\n\n"
        f"SYSTEM ANSWER:\n{system_answer}\n"
    )


class RagbenchJudge:
    """LLM-as-judge that computes the four native RAGBench metrics."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - hard dep
                raise ImportError("openai package is required for the RAGBench judge.") from exc

            if not self.settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required for the RAGBench LLM-as-judge.")

            kwargs: Dict[str, Any] = {"api_key": self.settings.openai_api_key}
            if self.settings.openai_base_url:
                kwargs["base_url"] = self.settings.openai_base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def _judge_one(
        self,
        question: str,
        contexts: List[str],
        reference_answer: str,
        system_answer: str,
    ) -> Optional[Dict[str, Any]]:
        client = self._get_client()
        user_prompt = _build_user_prompt(question, contexts, reference_answer, system_answer)
        try:
            response = client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Judge call failed: {exc}")
            return None

    @staticmethod
    def _scores_from_judgement(
        judgement: Optional[Dict[str, Any]], contexts: List[str]
    ) -> Dict[str, float]:
        """Convert a raw judge JSON response into the four RAGBench scores.

        A ``None`` judgement (failed call) yields all-zero scores so that the
        failure is reflected rather than silently dropped.
        """
        if judgement is None:
            return {m: 0.0 for m in RAGBENCH_METRICS}

        n_ctx = max(1, len(contexts))
        relevant = [
            i for i in judgement.get("relevant_chunk_indices", [])
            if isinstance(i, int) and 0 <= i < len(contexts)
        ]
        utilized = [
            i for i in judgement.get("utilized_chunk_indices", [])
            if isinstance(i, int) and 0 <= i < len(contexts)
        ]
        # Utilization is over the relevant set; if no relevant chunks were
        # retrieved we conventionally report 0.0.
        if relevant:
            utilized_relevant = [i for i in utilized if i in relevant]
            utilization = len(utilized_relevant) / len(relevant)
        else:
            utilization = 0.0

        try:
            completeness = float(judgement.get("completeness", 0.0))
        except (TypeError, ValueError):
            completeness = 0.0
        completeness = max(0.0, min(1.0, completeness))

        adherence = 1.0 if bool(judgement.get("adherence", False)) else 0.0

        return {
            "context_relevance": len(relevant) / n_ctx,
            "context_utilization": utilization,
            "completeness": completeness,
            "adherence": adherence,
        }

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def evaluate(
        self,
        predictions: List[PredictionRecord],
        queries: List[QueryRecord],
    ) -> Dict[str, Any]:
        """Evaluate predictions and return aggregate + per-sample scores.

        Returns a dict with keys:
          * ``metrics``: ``Dict[str, float]`` — mean of each RAGBench metric in [0, 1].
          * ``per_sample``: ``List[Dict[str, Any]]`` — per-query breakdown including
            the ``subset`` taken from the query's metadata when available.
        """
        query_map = {q.id: q for q in queries}

        # Build the list of judgeable items, preserving prediction order so the
        # resulting per_sample list is deterministic regardless of completion
        # order under concurrency.
        items = []
        for pred in predictions:
            query = query_map.get(pred.query_id)
            if query is None:
                continue
            items.append((pred, query, [c.text for c in pred.retrieved_contexts]))

        def _judge_item(item) -> Dict[str, Any]:
            pred, query, contexts = item
            judgement = self._judge_one(
                question=pred.question,
                contexts=contexts,
                reference_answer=query.reference_answer,
                system_answer=pred.answer,
            )
            sample_metrics = self._scores_from_judgement(judgement, contexts)
            subset = (query.metadata or {}).get("subset") if query.metadata else None
            return {"query_id": query.id, "subset": subset, **sample_metrics}

        max_workers = max(1, getattr(self.settings, "eval_judge_concurrency", 1))
        total = len(items)

        per_sample: List[Dict[str, Any]] = []
        if max_workers == 1 or total <= 1:
            logger.info(f"Judging {total} samples sequentially...")
            for item in items:
                per_sample.append(_judge_item(item))
        else:
            logger.info(
                f"Judging {total} samples with concurrency={max_workers}..."
            )
            # Eagerly initialize the shared client before fanning out so the
            # lazy init isn't raced by multiple worker threads.
            self._get_client()
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # executor.map preserves input ordering in its results.
                for result in executor.map(_judge_item, items):
                    per_sample.append(result)

        # Aggregate
        if per_sample:
            aggregate = {
                m: float(sum(s[m] for s in per_sample) / len(per_sample))
                for m in RAGBENCH_METRICS
            }
        else:
            aggregate = {m: 0.0 for m in RAGBENCH_METRICS}

        return {"metrics": aggregate, "per_sample": per_sample}
