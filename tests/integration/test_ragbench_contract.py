from retriva_eval.core.suite import BaseSuite
from retriva_eval.core.registry import get_suite


def test_ragbench_registered():
    suite = get_suite("ragbench")
    assert isinstance(suite, BaseSuite)
    assert suite.name == "ragbench"


def test_ragbench_suite_yaml_has_12_subsets():
    suite = get_suite("ragbench")
    cfg = suite.load_suite_config()
    subsets = (cfg.get("dataset") or {}).get("subsets") or []
    assert len(subsets) == 12, f"Expected 12 RAGBench subsets, got {len(subsets)}: {subsets}"


def test_ragbench_default_seed_in_yaml():
    suite = get_suite("ragbench")
    cfg = suite.load_suite_config()
    assert (cfg.get("sampling") or {}).get("seed") == 42
