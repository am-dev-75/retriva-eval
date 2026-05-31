from retriva_eval.core.suite import BaseSuite
from retriva_eval.core.registry import register_suite
from retriva_eval.core.config import AppConfig

from .prepare import do_prepare
from .ingest import do_ingest
from .run import do_run
from .evaluate import do_evaluate

@register_suite("ragas_sample_markdown")
class RagasSampleMarkdownSuite(BaseSuite):
    
    def prepare(self, app_config: AppConfig, run_id: str, dry_run: bool) -> None:
        do_prepare(self.name, app_config, run_id, dry_run)
        
    def ingest(self, app_config: AppConfig, run_id: str, dry_run: bool) -> None:
        do_ingest(self.name, app_config, run_id, dry_run)
        
    def run(self, app_config: AppConfig, run_id: str, dry_run: bool) -> None:
        do_run(self.name, app_config, run_id, dry_run)
        
    def evaluate(self, app_config: AppConfig, run_id: str, dry_run: bool) -> None:
        # We need to save the metrics so the global report can aggregate them.
        # But global report needs a way to fetch them. For now, the runner could
        # just assume they are written to disk. But let's keep it simple.
        do_evaluate(self.name, app_config, run_id, dry_run)
        
    def report(self, app_config: AppConfig, run_id: str, dry_run: bool) -> None:
        # Suite-specific report could go here.
        pass
