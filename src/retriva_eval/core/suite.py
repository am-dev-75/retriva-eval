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

from abc import ABC, abstractmethod
from typing import Dict, Any
import os
import yaml

from retriva_eval.core.config import Settings

class BaseSuite(ABC):
    def __init__(self, name: str):
        self.name = name
        self.config_cache: Dict[str, Any] = {}
        
    def get_suite_dir(self) -> str:
        return os.path.join("suites", self.name)
        
    def load_suite_config(self) -> Dict[str, Any]:
        if not self.config_cache:
            path = os.path.join(self.get_suite_dir(), "suite.yaml")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self.config_cache = yaml.safe_load(f) or {}
        return self.config_cache

    @abstractmethod
    def prepare(self, settings: Settings, run_id: str, dry_run: bool) -> None:
        """Download or materialize suite data."""
        pass

    @abstractmethod
    def ingest(self, settings: Settings, run_id: str, dry_run: bool) -> None:
        """Index chunks into evaluation Qdrant collection."""
        pass

    @abstractmethod
    def run(self, settings: Settings, run_id: str, dry_run: bool) -> None:
        """Execute queries against Retriva."""
        pass

    @abstractmethod
    def evaluate(self, settings: Settings, run_id: str, dry_run: bool) -> None:
        """Compute metrics using Ragas."""
        pass

    @abstractmethod
    def report(self, settings: Settings, run_id: str, dry_run: bool) -> None:
        """Generate optional suite-specific reports before global aggregation."""
        pass
