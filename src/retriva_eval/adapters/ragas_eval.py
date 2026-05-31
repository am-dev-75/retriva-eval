from typing import List, Dict, Any
from datasets import Dataset

try:
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False

from retriva_eval.core.schemas import PredictionRecord, QueryRecord
from retriva_eval.logger import get_logger

logger = get_logger("ragas_adapter")

class RagasAdapter:
    def __init__(self, metrics: List[str]):
        self.metrics_names = metrics
        
    def _get_ragas_metrics(self) -> List[Any]:
        if not RAGAS_AVAILABLE:
            raise ImportError("Ragas is not installed. Run `pip install ragas`.")
            
        metric_map = {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_precision": context_precision,
            "context_recall": context_recall,
        }
        
        return [metric_map[m] for m in self.metrics_names if m in metric_map]

    def evaluate(self, predictions: List[PredictionRecord], queries: List[QueryRecord]) -> Dict[str, float]:
        if not RAGAS_AVAILABLE:
            logger.warning("Ragas is not available. Skipping true evaluation.")
            return {m: 0.0 for m in self.metrics_names}
            
        if not predictions:
            return {m: 0.0 for m in self.metrics_names}
            
        # Map queries for easy lookup
        query_map = {q.id: q for q in queries}
        
        # Prepare HuggingFace Dataset
        data = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": []
        }
        
        for p in predictions:
            q = query_map.get(p.query_id)
            if not q:
                continue
            data["question"].append(p.question)
            data["answer"].append(p.answer)
            data["contexts"].append([c.text for c in p.retrieved_contexts])
            data["ground_truth"].append(q.reference_answer)
            
        dataset = Dataset.from_dict(data)
        
        metrics = self._get_ragas_metrics()
        
        # Run evaluation
        logger.info(f"Running Ragas evaluation with metrics: {self.metrics_names}")
        result = evaluate(dataset, metrics=metrics)
        
        return {k: float(v) for k, v in result.items()}
