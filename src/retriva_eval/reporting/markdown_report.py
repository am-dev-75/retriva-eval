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

import json
import os
from typing import List, Optional

from retriva_eval.core.schemas import MetricsRecord, APIEndpointStats


def _load_per_subset(reports_dir: str, run_id: str, suite: str) -> Optional[dict]:
    """Load a suite's optional per-subset breakdown if it wrote one.

    Returns the ``per_subset`` mapping (subset -> metric scores) or ``None``
    when the suite did not produce a ``metrics_by_subset.json`` artifact.
    """
    path = os.path.join(reports_dir, run_id, suite, "metrics_by_subset.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("per_subset") or None
    except (json.JSONDecodeError, OSError):
        return None


def generate_markdown_summary(reports_dir: str, run_id: str, metrics: List[MetricsRecord], total_time_ms: int, api_stats: List[APIEndpointStats]) -> str:
    summary_path = os.path.join(reports_dir, run_id, "summary.md")
    
    global_status = "pass" if all(m.status == "pass" for m in metrics) else "fail"
    total_time_str = f"{total_time_ms / 1000.0:.2f}s"
    
    lines = [
        f"# Evaluation Summary ({run_id})",
        "",
        f"**Global Status:** `{global_status.upper()}`",
        f"**Total Execution Time:** `{total_time_str}`",
        ""
    ]
    
    if api_stats:
        lines.append("## API Profiling")
        lines.append("| Endpoint | Invocations | Avg Latency (ms) |")
        lines.append("|---|---|---|")
        for stat in api_stats:
            lines.append(f"| `{stat.endpoint}` | {stat.invocations} | {stat.avg_latency_ms:.2f} |")
        lines.append("")
    
    for m in metrics:
        lines.append(f"## Suite: {m.suite}")
        lines.append(f"- **Status:** `{m.status.upper()}`")
        lines.append(f"- **Samples:** {m.sample_count}")
        lines.append("")
        lines.append("### Metrics")
        lines.append("| Metric | Score | Threshold | Pass |")
        lines.append("|---|---|---|---|")
        
        for k, v in m.metrics.items():
            threshold = m.thresholds.get(k)
            if threshold is not None:
                passed = "✅" if v >= threshold else "❌"
                lines.append(f"| {k} | {v:.4f} | {threshold:.4f} | {passed} |")
            else:
                lines.append(f"| {k} | {v:.4f} | N/A | ℹ️ |")
        lines.append("")

        # Optional per-subset breakdown (e.g. RAGBench's 12 domains).
        per_subset = _load_per_subset(reports_dir, run_id, m.suite)
        if per_subset:
            metric_keys = list(m.metrics.keys())
            header = "| Subset | Samples | " + " | ".join(metric_keys) + " |"
            divider = "|---|---|" + "|".join(["---"] * len(metric_keys)) + "|"
            lines.append("### Per-Subset Breakdown")
            lines.append(header)
            lines.append(divider)
            for subset in sorted(per_subset.keys()):
                scores = per_subset[subset]
                sample_count = int(scores.get("sample_count", 0))
                cells = []
                for k in metric_keys:
                    val = scores.get(k)
                    cells.append(f"{val:.4f}" if isinstance(val, (int, float)) else "N/A")
                lines.append(f"| {subset} | {sample_count} | " + " | ".join(cells) + " |")
            lines.append("")
        
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    return summary_path
