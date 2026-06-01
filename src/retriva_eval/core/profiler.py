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

import threading
from typing import Dict

class APIEndpointStats:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.invocations = 0
        self.total_latency_ms = 0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.invocations if self.invocations > 0 else 0.0

class APIProfiler:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(APIProfiler, cls).__new__(cls)
                cls._instance._stats = {}
                cls._instance._stats_lock = threading.Lock()
            return cls._instance

    @classmethod
    def get_instance(cls) -> "APIProfiler":
        return cls()

    def record_call(self, endpoint: str, latency_ms: int):
        with self._stats_lock:
            if endpoint not in self._stats:
                self._stats[endpoint] = APIEndpointStats(endpoint)
            self._stats[endpoint].invocations += 1
            self._stats[endpoint].total_latency_ms += latency_ms

    def get_statistics(self) -> list[Dict]:
        with self._stats_lock:
            stats_list = []
            for ep, stats in self._stats.items():
                stats_list.append({
                    "endpoint": ep,
                    "invocations": stats.invocations,
                    "avg_latency_ms": stats.avg_latency_ms
                })
            return sorted(stats_list, key=lambda x: x["endpoint"])
