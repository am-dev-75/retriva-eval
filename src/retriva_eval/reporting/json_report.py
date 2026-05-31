import os
from typing import List

from retriva_eval.core.schemas import MetricsRecord
from retriva_eval.utils.io import write_json

def generate_json_summary(reports_dir: str, run_id: str, metrics: List[MetricsRecord]) -> str:
    summary_path = os.path.join(reports_dir, run_id, "summary.json")
    
    data = {
        "run_id": run_id,
        "suites": [m.model_dump() for m in metrics],
        "global_status": "pass" if all(m.status == "pass" for m in metrics) else "fail"
    }
    
    write_json(summary_path, data)
    return summary_path
