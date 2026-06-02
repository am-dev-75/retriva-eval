from retriva_eval.core.config import Settings
from retriva_eval.core.runner import run_suite_lifecycle
from retriva_eval.core.suite import BaseSuite

class DummySuite(BaseSuite):
    def __init__(self, name):
        super().__init__(name)
        self.calls = []

    def prepare(self, c, r, d, portion=1.0, seed=None):
        self.calls.append(("prepare", portion, seed))
    def ingest(self, c, r, d, portion=1.0, seed=None):
        self.calls.append(("ingest", portion, seed))
    def run(self, c, r, d, portion=1.0, seed=None):
        self.calls.append(("run", portion, seed))
    def evaluate(self, c, r, d, portion=1.0, seed=None):
        self.calls.append(("evaluate", portion, seed))
    def report(self, c, r, d, portion=1.0, seed=None):
        self.calls.append(("report", portion, seed))

def test_runner_lifecycle():
    suite = DummySuite("dummy")
    settings = Settings()
    
    # Should not raise exception
    run_suite_lifecycle(suite, settings, "test_run_1", dry_run=True)
    assert [c[0] for c in suite.calls] == ["prepare", "ingest", "run", "evaluate", "report"]
    # Default portion/seed propagated
    assert all(c[1] == 1.0 and c[2] is None for c in suite.calls)


def test_runner_lifecycle_with_portion_and_seed():
    suite = DummySuite("dummy")
    settings = Settings()
    
    run_suite_lifecycle(suite, settings, "test_run_2", dry_run=True, portion=0.25, seed=123)
    assert all(c[1] == 0.25 and c[2] == 123 for c in suite.calls)
