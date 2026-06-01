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
from typing import List

from retriva_eval.core.schemas import MetricsRecord, APIEndpointStats, PipelineRunSummary
from retriva_eval.utils.io import write_json

def generate_json_summary(reports_dir: str, run_id: str, metrics: List[MetricsRecord], total_time_ms: int, api_stats: List[APIEndpointStats]) -> str:
    summary_path = os.path.join(reports_dir, run_id, "summary.json")
    
    global_status = "pass" if all(m.status == "pass" for m in metrics) else "fail"
    summary = PipelineRunSummary(
        run_id=run_id,
        global_status=global_status,
        total_execution_time_ms=total_time_ms,
        api_stats=api_stats,
        suites=metrics
    )
    
    write_json(summary_path, summary.model_dump())
    return summary_path
