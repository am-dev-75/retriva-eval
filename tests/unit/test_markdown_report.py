import json
import os

from retriva_eval.core.schemas import MetricsRecord
from retriva_eval.reporting.markdown_report import generate_markdown_summary


def _make_metrics(suite="ragbench"):
    return MetricsRecord(
        suite=suite,
        run_id="RID",
        sample_count=3,
        metrics={
            "context_relevance": 0.50,
            "context_utilization": 0.80,
            "completeness": 0.70,
            "adherence": 0.90,
        },
        thresholds={
            "context_relevance": 0.70,
            "context_utilization": 0.70,
            "completeness": 0.70,
            "adherence": 0.80,
        },
        status="fail",
    )


def test_summary_without_per_subset(tmp_path):
    run_id = "RID"
    os.makedirs(os.path.join(tmp_path, run_id, "ragbench"), exist_ok=True)
    path = generate_markdown_summary(str(tmp_path), run_id, [_make_metrics()], 1234, [])
    content = open(path).read()
    assert "# Evaluation Summary (RID)" in content
    assert "### Metrics" in content
    # No breakdown file -> no per-subset section
    assert "Per-Subset Breakdown" not in content


def test_summary_with_per_subset(tmp_path):
    run_id = "RID"
    suite_dir = os.path.join(tmp_path, run_id, "ragbench")
    os.makedirs(suite_dir, exist_ok=True)

    per_subset = {
        "covidqa": {
            "context_relevance": 0.09,
            "context_utilization": 1.0,
            "completeness": 0.75,
            "adherence": 0.50,
            "sample_count": 2.0,
        },
        "finqa": {
            "context_relevance": 0.20,
            "context_utilization": 0.66,
            "completeness": 0.80,
            "adherence": 1.0,
            "sample_count": 10.0,
        },
    }
    with open(os.path.join(suite_dir, "metrics_by_subset.json"), "w") as f:
        json.dump({"per_subset": per_subset, "per_sample": []}, f)

    path = generate_markdown_summary(str(tmp_path), run_id, [_make_metrics()], 1234, [])
    content = open(path).read()

    assert "### Per-Subset Breakdown" in content
    # Subsets are rendered, sorted alphabetically
    assert content.index("covidqa") < content.index("finqa")
    # Sample counts rendered as ints
    assert "| covidqa | 2 |" in content
    assert "| finqa | 10 |" in content
    # A known score value is formatted to 4 decimals
    assert "0.0900" in content
    # Column header uses the metric keys from the MetricsRecord
    assert "context_relevance" in content
