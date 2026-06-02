from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import (
    PredictionRecord,
    QueryRecord,
    RetrievedContext,
)
from retriva_eval.adapters.ragbench_judge import RAGBENCH_METRICS, RagbenchJudge


def _make_inputs(n: int):
    queries = []
    predictions = []
    for i in range(n):
        qid = f"q_{i}"
        queries.append(
            QueryRecord(
                id=qid,
                suite="ragbench",
                question=f"Question {i}?",
                reference_answer=f"Reference {i}",
                reference_context_ids=[f"d_{i}"],
                metadata={"subset": "subset_a" if i % 2 == 0 else "subset_b"},
            )
        )
        predictions.append(
            PredictionRecord(
                query_id=qid,
                suite="ragbench",
                question=f"Question {i}?",
                answer=f"Answer {i}",
                retrieved_contexts=[
                    RetrievedContext(id=f"d_{i}", text=f"Context {i}", score=0.9, rank=1)
                ],
                latency_ms=10,
            )
        )
    return predictions, queries


def test_scores_from_judgement_normal():
    contexts = ["a", "b", "c", "d"]
    judgement = {
        "relevant_chunk_indices": [0, 1],
        "utilized_chunk_indices": [0],
        "completeness": 0.5,
        "adherence": True,
    }
    scores = RagbenchJudge._scores_from_judgement(judgement, contexts)
    assert scores["context_relevance"] == 0.5  # 2 of 4 relevant
    assert scores["context_utilization"] == 0.5  # 1 of 2 relevant utilized
    assert scores["completeness"] == 0.5
    assert scores["adherence"] == 1.0


def test_scores_from_judgement_none_is_zero():
    scores = RagbenchJudge._scores_from_judgement(None, ["a"])
    assert scores == {m: 0.0 for m in RAGBENCH_METRICS}


def test_scores_from_judgement_clamps_and_filters():
    contexts = ["a", "b"]
    judgement = {
        "relevant_chunk_indices": [0, 99],  # 99 out of range -> filtered
        "utilized_chunk_indices": [5],  # out of range -> filtered
        "completeness": 2.5,  # clamped to 1.0
        "adherence": False,
    }
    scores = RagbenchJudge._scores_from_judgement(judgement, contexts)
    assert scores["context_relevance"] == 0.5  # only index 0 valid, of 2 ctx
    assert scores["context_utilization"] == 0.0  # nothing valid utilized
    assert scores["completeness"] == 1.0
    assert scores["adherence"] == 0.0


def test_evaluate_concurrent_preserves_order_and_aggregates(monkeypatch):
    """The concurrent judge path must preserve prediction ordering and produce
    correct aggregates. We stub the network call with a deterministic fake."""
    predictions, queries = _make_inputs(10)

    settings = Settings()
    settings.eval_judge_concurrency = 4  # force the concurrent branch
    judge = RagbenchJudge(settings)

    # Avoid real client init.
    monkeypatch.setattr(judge, "_get_client", lambda: object())

    def fake_judge_one(question, contexts, reference_answer, system_answer):
        # Encode the query index into completeness so we can verify ordering.
        idx = int(question.split()[1].rstrip("?"))
        return {
            "relevant_chunk_indices": [0],
            "utilized_chunk_indices": [0],
            "completeness": idx / 10.0,
            "adherence": True,
        }

    monkeypatch.setattr(judge, "_judge_one", fake_judge_one)

    result = judge.evaluate(predictions, queries)
    per_sample = result["per_sample"]

    # Order preserved (q_0 .. q_9)
    assert [s["query_id"] for s in per_sample] == [f"q_{i}" for i in range(10)]
    # Completeness reflects the per-query index, confirming no result crossover
    assert [round(s["completeness"], 3) for s in per_sample] == [
        round(i / 10.0, 3) for i in range(10)
    ]
    # Aggregate completeness is the mean of 0.0..0.9
    assert round(result["metrics"]["completeness"], 4) == round(
        sum(i / 10.0 for i in range(10)) / 10.0, 4
    )
    assert result["metrics"]["adherence"] == 1.0
