import os
import importlib.util
from typing import Dict, List, Type
from retriva_eval.core.suite import BaseSuite
from retriva_eval.core.config import AppConfig

_REGISTRY: Dict[str, Type[BaseSuite]] = {}

def register_suite(name: str):
    def decorator(cls: Type[BaseSuite]):
        _REGISTRY[name] = cls
        return cls
    return decorator

class DynamicSuite(BaseSuite):
    def _call_stage(self, stage: str, app_config: AppConfig, run_id: str, dry_run: bool):
        path = os.path.join(self.get_suite_dir(), f"{stage}.py")
        if not os.path.exists(path):
            if stage == "report":
                return
            raise FileNotFoundError(f"Suite {self.name} missing {stage}.py")
            
        spec = importlib.util.spec_from_file_location(f"suite_{self.name}_{stage}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        func_name = f"do_{stage}"
        if hasattr(module, func_name):
            func = getattr(module, func_name)
            func(self.name, app_config, run_id, dry_run)
        else:
            raise AttributeError(f"{path} must define '{func_name}'")

    def prepare(self, app_config: AppConfig, run_id: str, dry_run: bool) -> None:
        self._call_stage("prepare", app_config, run_id, dry_run)

    def ingest(self, app_config: AppConfig, run_id: str, dry_run: bool) -> None:
        self._call_stage("ingest", app_config, run_id, dry_run)

    def run(self, app_config: AppConfig, run_id: str, dry_run: bool) -> None:
        self._call_stage("run", app_config, run_id, dry_run)

    def evaluate(self, app_config: AppConfig, run_id: str, dry_run: bool) -> None:
        self._call_stage("evaluate", app_config, run_id, dry_run)

    def report(self, app_config: AppConfig, run_id: str, dry_run: bool) -> None:
        self._call_stage("report", app_config, run_id, dry_run)

def get_suite(name: str) -> BaseSuite:
    if name in _REGISTRY:
        return _REGISTRY[name](name)
        
    suite_dir = os.path.join("suites", name)
    if os.path.isdir(suite_dir) and os.path.exists(os.path.join(suite_dir, "suite.yaml")):
        return DynamicSuite(name)
        
    raise ValueError(f"Suite '{name}' not found in registry or 'suites/' directory.")

def get_all_suite_names() -> List[str]:
    names = list(_REGISTRY.keys())
    if os.path.isdir("suites"):
        for d in os.listdir("suites"):
            if os.path.isdir(os.path.join("suites", d)) and os.path.exists(os.path.join("suites", d, "suite.yaml")):
                if d not in names:
                    names.append(d)
    return names
