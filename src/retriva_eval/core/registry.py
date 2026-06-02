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

import os
import inspect
import importlib.util
from typing import Dict, List, Optional, Type
from retriva_eval.core.suite import BaseSuite
from retriva_eval.core.config import Settings

_REGISTRY: Dict[str, Type[BaseSuite]] = {}

def register_suite(name: str):
    def decorator(cls: Type[BaseSuite]):
        _REGISTRY[name] = cls
        return cls
    return decorator

class DynamicSuite(BaseSuite):
    def _call_stage(self, stage: str, settings: Settings, run_id: str, dry_run: bool, portion: float = 1.0, seed: Optional[int] = None):
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
            # Support both legacy (suite_name, settings, run_id, dry_run) and
            # extended (suite_name, settings, run_id, dry_run, portion, seed)
            # signatures so older suites keep working without modification.
            sig = inspect.signature(func)
            kwargs = {}
            if "portion" in sig.parameters:
                kwargs["portion"] = portion
            if "seed" in sig.parameters:
                kwargs["seed"] = seed
            func(self.name, settings, run_id, dry_run, **kwargs)
        else:
            raise AttributeError(f"{path} must define '{func_name}'")

    def prepare(self, settings: Settings, run_id: str, dry_run: bool, portion: float = 1.0, seed: Optional[int] = None) -> None:
        self._call_stage("prepare", settings, run_id, dry_run, portion, seed)

    def ingest(self, settings: Settings, run_id: str, dry_run: bool, portion: float = 1.0, seed: Optional[int] = None) -> None:
        self._call_stage("ingest", settings, run_id, dry_run, portion, seed)

    def run(self, settings: Settings, run_id: str, dry_run: bool, portion: float = 1.0, seed: Optional[int] = None) -> None:
        self._call_stage("run", settings, run_id, dry_run, portion, seed)

    def evaluate(self, settings: Settings, run_id: str, dry_run: bool, portion: float = 1.0, seed: Optional[int] = None) -> None:
        self._call_stage("evaluate", settings, run_id, dry_run, portion, seed)

    def report(self, settings: Settings, run_id: str, dry_run: bool, portion: float = 1.0, seed: Optional[int] = None) -> None:
        self._call_stage("report", settings, run_id, dry_run, portion, seed)

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
