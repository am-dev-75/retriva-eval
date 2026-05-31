from retriva_eval.core.config import AppConfig
from retriva_eval.core.runner import run_suite_lifecycle
from retriva_eval.core.suite import BaseSuite

class DummySuite(BaseSuite):
    def prepare(self, c, r, d): pass
    def ingest(self, c, r, d): pass
    def run(self, c, r, d): pass
    def evaluate(self, c, r, d): pass
    def report(self, c, r, d): pass

def test_runner_lifecycle():
    suite = DummySuite("dummy")
    config = AppConfig()
    
    # Should not raise exception
    run_suite_lifecycle(suite, config, "test_run_1", dry_run=True)
