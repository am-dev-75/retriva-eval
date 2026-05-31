from retriva_eval.core.suite import BaseSuite
from retriva_eval.core.registry import get_suite

def test_ragas_sample_markdown_registered():
    suite = get_suite("ragas_sample_markdown")
    assert isinstance(suite, BaseSuite)
    assert suite.name == "ragas_sample_markdown"
