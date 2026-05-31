import os
from typing import List

from retriva_eval.core.schemas import MetricsRecord

def generate_markdown_summary(reports_dir: str, run_id: str, metrics: List[MetricsRecord]) -> str:
    summary_path = os.path.join(reports_dir, run_id, "summary.md")
    
    global_status = "pass" if all(m.status == "pass" for m in metrics) else "fail"
    
    lines = [
        f"# Evaluation Summary ({run_id})",
        "",
        f"**Global Status:** `{global_status.upper()}`",
        ""
    ]
    
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
        
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    return summary_path
