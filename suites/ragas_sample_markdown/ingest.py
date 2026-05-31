import os
from retriva_eval.core.config import AppConfig
from retriva_eval.core.schemas import CorpusRecord
from retriva_eval.adapters.qdrant_store import QdrantAdapter
from retriva_eval.utils.io import read_jsonl
from retriva_eval.utils.logging import get_logger

logger = get_logger("ragas_suite_ingest")

def do_ingest(suite_name: str, app_config: AppConfig, run_id: str, dry_run: bool) -> None:
    corpus_path = os.path.join(app_config.evaluation.reports_dir, run_id, suite_name, "corpus.jsonl")
    corpus = read_jsonl(corpus_path, CorpusRecord)
    
    qdrant = QdrantAdapter(app_config.qdrant)
    
    if dry_run:
        logger.info(f"[Dry Run] Skipping Qdrant ingestion of {len(corpus)} records.")
        return
        
    qdrant.verify_collection()
    logger.info(f"Would ingest {len(corpus)} records into Qdrant collection '{app_config.qdrant.collection_name}'.")
    # Real implementation would embed the corpus records and upsert.
