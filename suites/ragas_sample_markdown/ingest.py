import os
from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import CorpusRecord
from retriva_eval.adapters.retriva_client import get_retriva_client
from retriva_eval.utils.io import read_jsonl
from retriva_eval.utils.logging import get_logger

logger = get_logger("ragas_suite_ingest")

def do_ingest(suite_name: str, settings: Settings, run_id: str, dry_run: bool) -> None:
    corpus_path = os.path.join(settings.eval_reports_dir, run_id, suite_name, "corpus.jsonl")
    corpus = read_jsonl(corpus_path, CorpusRecord)
    
    if dry_run:
        logger.info(f"[Dry Run] Skipping Retriva ingestion of {len(corpus)} records.")
        return
        
    client = get_retriva_client(settings)
    logger.info(f"Ingesting documents via {settings.retriva_adapter} into KB '{settings.eval_knowledge_base}'")
    
    # For MVP stub, we'll write a dummy markdown file and ingest it
    dummy_md = os.path.join(settings.eval_reports_dir, run_id, suite_name, "dummy.md")
    with open(dummy_md, "w", encoding="utf-8") as f:
        f.write("# Dummy Document\n\n")
        for record in corpus:
            f.write(f"{record.text}\n\n")
            
    client.ingest_document(dummy_md, document_id="dummy_doc_1", run_id=run_id)

