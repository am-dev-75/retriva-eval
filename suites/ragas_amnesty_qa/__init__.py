from retriva_eval.core.suite import BaseSuite
from retriva_eval.core.registry import register_suite
from retriva_eval.core.config import Settings

from .prepare import do_prepare
from .ingest import do_ingest
from .run import do_run
from .evaluate import do_evaluate

@register_suite("ragas_amnesty_qa")
class RagasAmnestyQASuite(BaseSuite):
    
    def prepare(self, settings: Settings, run_id: str, dry_run: bool) -> None:
        do_prepare(self.name, settings, run_id, dry_run)
        
    def ingest(self, settings: Settings, run_id: str, dry_run: bool) -> None:
        do_ingest(self.name, settings, run_id, dry_run)
        
    def run(self, settings: Settings, run_id: str, dry_run: bool) -> None:
        do_run(self.name, settings, run_id, dry_run)
        
    def evaluate(self, settings: Settings, run_id: str, dry_run: bool) -> None:
        do_evaluate(self.name, settings, run_id, dry_run)
        
    def report(self, settings: Settings, run_id: str, dry_run: bool) -> None:
        pass
