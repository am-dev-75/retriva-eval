"""Email ingestion test suite — registration."""

import os
from retriva_eval.core.suite import BaseSuite
from retriva_eval.core.registry import register_suite


@register_suite("email_ingestion")
class EmailIngestionSuite(BaseSuite):
    """Suite that sends emails via swaks and verifies ingestion."""

    def prepare(self, settings, run_id, dry_run, portion=1.0, seed=None):
        from suites.email_ingestion.prepare import do_prepare
        do_prepare(self.name, settings, run_id, dry_run, portion=portion, seed=seed)

    def ingest(self, settings, run_id, dry_run, portion=1.0, seed=None):
        from suites.email_ingestion.ingest import do_ingest
        do_ingest(self.name, settings, run_id, dry_run, portion=portion, seed=seed)

    def run(self, settings, run_id, dry_run, portion=1.0, seed=None):
        from suites.email_ingestion.run import do_run
        do_run(self.name, settings, run_id, dry_run, portion=portion, seed=seed)

    def evaluate(self, settings, run_id, dry_run, portion=1.0, seed=None):
        from suites.email_ingestion.evaluate import do_evaluate
        do_evaluate(self.name, settings, run_id, dry_run, portion=portion, seed=seed)

    def report(self, settings, run_id, dry_run, portion=1.0, seed=None):
        from suites.email_ingestion.report import do_report
        do_report(self.name, settings, run_id, dry_run, portion=portion, seed=seed)
