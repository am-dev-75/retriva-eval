import os
from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import CorpusRecord
from retriva_eval.adapters.retriva_client import get_retriva_client
from retriva_eval.utils.io import read_jsonl
from retriva_eval.logger import get_logger

logger = get_logger("ragas_amnesty_qa_ingest")

def do_ingest(suite_name: str, settings: Settings, run_id: str, dry_run: bool) -> None:
    reports_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    corpus_path = os.path.join(reports_dir, "corpus.jsonl")
    corpus = read_jsonl(corpus_path, CorpusRecord)
    
    if dry_run:
        logger.info(f"[Dry Run] Skipping ingestion of {len(corpus)} records.")
        return
        
    client = get_retriva_client(settings)
    logger.info(f"Ingesting {len(corpus)} documents into KB '{settings.eval_knowledge_base}'...")
    
    data_dir = os.path.join(reports_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    for record in corpus:
        # Create a physical markdown file for the gateway to upload
        file_path = os.path.join(data_dir, f"{record.document_id}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(record.text)
            
        client.ingest_document(file_path, document_id=record.document_id, run_id=run_id, suite_name=suite_name)
        
    logger.info("Ingestion complete.")
