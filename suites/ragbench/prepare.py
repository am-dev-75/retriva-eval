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

"""Prepare stage for the RAGBench suite.

Downloads each of the 12 RAGBench subsets from ``galileo-ai/ragbench`` on
HuggingFace (formerly ``rungalileo/ragbench``, which now redirects there),
optionally sub-samples each subset by ``portion`` using a reproducible RNG
seeded from CLI or ``suite.yaml``, and writes the canonical ``corpus.jsonl``
and ``queries.jsonl`` artifacts for downstream stages.

The repository id is read from ``suite.yaml`` (``dataset.repo``) and falls
back to ``galileo-ai/ragbench`` if unset.

Each ``QueryRecord`` carries ``metadata = {"subset": <subset_name>}`` so the
evaluation stage can produce per-subset breakdowns.
"""

import hashlib
import os
import random
from typing import Optional

import yaml
from datasets import load_dataset

from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import CorpusRecord, QueryRecord
from retriva_eval.utils.io import write_jsonl
from retriva_eval.logger import get_logger

logger = get_logger("ragbench_prepare")

# Canonical HuggingFace repo id. The older ``rungalileo/ragbench`` id now
# redirects here; we target the canonical id to avoid relying on the redirect.
_DEFAULT_REPO = "galileo-ai/ragbench"
_SUITE_DIR = os.path.dirname(__file__)


def _load_suite_yaml() -> dict:
    path = os.path.join(_SUITE_DIR, "suite.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_seed(cli_seed: Optional[int], suite_cfg: dict) -> int:
    """CLI seed wins over the suite default; fall back to 42 if neither set."""
    if cli_seed is not None:
        return int(cli_seed)
    return int((suite_cfg.get("sampling") or {}).get("seed", 42))


def _row_documents(row: dict) -> list:
    """Best-effort extraction of context documents from a RAGBench row.

    The RAGBench dataset on HuggingFace uses ``documents`` (List[str]) for the
    retrieved passages associated with each example. A few legacy subsets
    expose them as ``contexts``; we accept either.
    """
    docs = row.get("documents")
    if docs is None:
        docs = row.get("contexts")
    if docs is None:
        return []
    if isinstance(docs, str):
        return [docs]
    return list(docs)


def _row_response(row: dict) -> str:
    """Extract the gold answer string."""
    for key in ("response", "answer", "ground_truth"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def _row_question(row: dict) -> str:
    for key in ("question", "query"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def do_prepare(
    suite_name: str,
    settings: Settings,
    run_id: str,
    dry_run: bool,
    portion: float = 1.0,
    seed: Optional[int] = None,
) -> None:
    reports_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    os.makedirs(reports_dir, exist_ok=True)

    corpus_path = os.path.join(reports_dir, "corpus.jsonl")
    queries_path = os.path.join(reports_dir, "queries.jsonl")

    suite_cfg = _load_suite_yaml()
    dataset_cfg = suite_cfg.get("dataset") or {}
    repo = dataset_cfg.get("repo") or _DEFAULT_REPO
    subsets = dataset_cfg.get("subsets") or []
    split = dataset_cfg.get("split", "test")
    effective_seed = _resolve_seed(seed, suite_cfg)

    if dry_run:
        logger.info("[Dry Run] Generating a tiny mock RAGBench dataset.")
        corpus = [
            CorpusRecord(
                id="ragbench_mock_doc_1",
                suite=suite_name,
                document_id="ragbench_mock_doc_1",
                text="Mock RAGBench context.",
                metadata={"subset": "mock"},
            )
        ]
        queries = [
            QueryRecord(
                id="ragbench_mock_q1",
                suite=suite_name,
                question="What is RAGBench?",
                reference_answer="A benchmark for RAG systems.",
                reference_context_ids=["ragbench_mock_doc_1"],
                metadata={"subset": "mock"},
            )
        ]
        write_jsonl(corpus_path, corpus)
        write_jsonl(queries_path, queries)
        return

    if not subsets:
        raise ValueError("suite.yaml is missing `dataset.subsets` for ragbench.")

    logger.info(
        f"Preparing RAGBench from '{repo}': {len(subsets)} subsets, split='{split}', "
        f"portion={portion}, seed={effective_seed}"
    )

    corpus_records: list = []
    query_records: list = []
    unique_doc_ids: dict = {}  # md5(text) -> doc_id, for global dedup

    rng = random.Random(effective_seed)

    for subset in subsets:
        logger.info(f"Loading subset '{subset}'...")
        try:
            ds = load_dataset(repo, subset)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to load RAGBench subset '{subset}': {exc}")
            raise

        if split in ds:
            split_ds = ds[split]
        else:
            # Fall back to whatever split is available; warn loudly.
            fallback = next(iter(ds.keys()))
            logger.warning(
                f"Subset '{subset}' has no split '{split}'; falling back to '{fallback}'."
            )
            split_ds = ds[fallback]

        total = len(split_ds)
        if portion < 1.0:
            n = max(1, int(round(total * portion)))
            # Derive a per-subset seed deterministically from the master seed so
            # that adding/removing subsets does not perturb the sampling of the
            # others.
            subset_seed = rng.randint(0, 2**31 - 1)
            sub_rng = random.Random(subset_seed)
            indices = sorted(sub_rng.sample(range(total), n))
            split_ds = split_ds.select(indices)
            logger.info(
                f"  Sampled {n}/{total} rows from '{subset}' (subset_seed={subset_seed})."
            )
        else:
            logger.info(f"  Using full split: {total} rows from '{subset}'.")

        for i, row in enumerate(split_ds):
            row = dict(row)
            question = _row_question(row)
            reference_answer = _row_response(row)
            documents = _row_documents(row)

            if not question or not documents:
                # Skip malformed rows defensively.
                continue

            ctx_ids: list = []
            for doc_text in documents:
                if not isinstance(doc_text, str) or not doc_text.strip():
                    continue
                ctx_hash = hashlib.md5(doc_text.encode("utf-8")).hexdigest()
                if ctx_hash not in unique_doc_ids:
                    doc_id = f"ragbench_{subset}_{ctx_hash}"
                    unique_doc_ids[ctx_hash] = doc_id
                    corpus_records.append(
                        CorpusRecord(
                            id=doc_id,
                            suite=suite_name,
                            document_id=doc_id,
                            text=doc_text,
                            metadata={"subset": subset},
                        )
                    )
                ctx_ids.append(unique_doc_ids[ctx_hash])

            original_id = row.get("id") if isinstance(row.get("id"), str) else None
            qid_suffix = original_id or f"{i:06d}"
            query_records.append(
                QueryRecord(
                    id=f"ragbench_{subset}_{qid_suffix}",
                    suite=suite_name,
                    question=question,
                    reference_answer=reference_answer,
                    reference_context_ids=ctx_ids,
                    metadata={"subset": subset, "ragbench_id": original_id},
                )
            )

    write_jsonl(corpus_path, corpus_records)
    write_jsonl(queries_path, query_records)
    logger.info(
        f"Wrote {len(corpus_records)} unique corpus records to {corpus_path}"
    )
    logger.info(f"Wrote {len(query_records)} queries to {queries_path}")
