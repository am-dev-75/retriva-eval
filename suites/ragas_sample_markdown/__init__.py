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
