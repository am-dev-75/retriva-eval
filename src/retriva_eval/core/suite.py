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
