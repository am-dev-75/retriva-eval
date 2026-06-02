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

from typing import Optional

from retriva_eval.core.suite import BaseSuite
from retriva_eval.core.registry import register_suite
from retriva_eval.core.config import Settings

from .prepare import do_prepare
from .ingest import do_ingest
from .run import do_run
from .evaluate import do_evaluate


@register_suite("ragbench")
class RagbenchSuite(BaseSuite):

    def prepare(self, settings: Settings, run_id: str, dry_run: bool, portion: float = 1.0, seed: Optional[int] = None) -> None:
        do_prepare(self.name, settings, run_id, dry_run, portion=portion, seed=seed)

    def ingest(self, settings: Settings, run_id: str, dry_run: bool, portion: float = 1.0, seed: Optional[int] = None) -> None:
        do_ingest(self.name, settings, run_id, dry_run)

    def run(self, settings: Settings, run_id: str, dry_run: bool, portion: float = 1.0, seed: Optional[int] = None) -> None:
        do_run(self.name, settings, run_id, dry_run)

    def evaluate(self, settings: Settings, run_id: str, dry_run: bool, portion: float = 1.0, seed: Optional[int] = None) -> None:
        do_evaluate(self.name, settings, run_id, dry_run)

    def report(self, settings: Settings, run_id: str, dry_run: bool, portion: float = 1.0, seed: Optional[int] = None) -> None:
        # Per-subset breakdown is written by `evaluate.py`; nothing extra here.
        pass
