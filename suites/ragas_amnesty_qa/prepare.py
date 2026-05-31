import os
import hashlib
from datasets import load_dataset
from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import CorpusRecord, QueryRecord
from retriva_eval.utils.io import write_jsonl
from retriva_eval.logger import get_logger

logger = get_logger("ragas_amnesty_qa_prepare")

def do_prepare(suite_name: str, settings: Settings, run_id: str, dry_run: bool) -> None:
    reports_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    os.makedirs(reports_dir, exist_ok=True)
    
    corpus_path = os.path.join(reports_dir, "corpus.jsonl")
    queries_path = os.path.join(reports_dir, "queries.jsonl")
    
    if dry_run:
        logger.info("[Dry Run] Generating mock corpus and queries.")
        corpus = [CorpusRecord(id="doc_1", suite=suite_name, document_id="doc_1", text="Mock context")]
        queries = [QueryRecord(id="q1", suite=suite_name, question="What is mock?", reference_answer="Mock context", reference_context_ids=["doc_1"])]
        write_jsonl(corpus_path, corpus)
        write_jsonl(queries_path, queries)
        return

    logger.info("Downloading explodinggradients/amnesty_qa dataset from HuggingFace...")
    try:
        ds = load_dataset('explodinggradients/amnesty_qa', 'english_v2')
        eval_ds = ds['eval']
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        raise

    corpus_records = []
    query_records = []
    
    # We will hash contexts to keep track of unique documents
    unique_contexts = {}
    
    logger.info("Processing dataset and extracting unique contexts...")
    for i, row in enumerate(eval_ds):
        q_id = f"q_{i}"
        question = row['question']
        ground_truth = row['ground_truth']
        contexts = row['contexts']
        
        ctx_ids = []
        for ctx_text in contexts:
            # Hash text to avoid duplicates
            ctx_hash = hashlib.md5(ctx_text.encode('utf-8')).hexdigest()
            doc_id = f"amnesty_{ctx_hash}"
            
            if doc_id not in unique_contexts:
                unique_contexts[doc_id] = ctx_text
                corpus_records.append(CorpusRecord(
                    id=doc_id,
                    suite=suite_name,
                    document_id=doc_id,
                    text=ctx_text
                ))
            ctx_ids.append(doc_id)
            
        query_records.append(QueryRecord(
            id=q_id,
            suite=suite_name,
            question=question,
            reference_answer=ground_truth,
            reference_context_ids=ctx_ids
        ))
        
    write_jsonl(corpus_path, corpus_records)
    write_jsonl(queries_path, query_records)
    logger.info(f"Wrote {len(corpus_records)} unique corpus records to {corpus_path}")
    logger.info(f"Wrote {len(query_records)} queries to {queries_path}")
