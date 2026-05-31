import os
from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import CorpusRecord, QueryRecord
from retriva_eval.utils.io import write_jsonl
from retriva_eval.utils.logging import get_logger

logger = get_logger("ragas_suite_prepare")

def do_prepare(suite_name: str, settings: Settings, run_id: str, dry_run: bool) -> None:
    reports_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    os.makedirs(reports_dir, exist_ok=True)
    
    corpus_path = os.path.join(reports_dir, "corpus.jsonl")
    queries_path = os.path.join(reports_dir, "queries.jsonl")
    
    if dry_run:
        logger.info("[Dry Run] Generating mock corpus and queries.")
        corpus = [
            CorpusRecord(id="doc_1_chunk_1", suite=suite_name, document_id="doc_1", text="Mock context 1"),
            CorpusRecord(id="doc_1_chunk_2", suite=suite_name, document_id="doc_1", text="Mock context 2"),
        ]
        queries = [
            QueryRecord(
                id="q_1", suite=suite_name, question="What is mock 1?",
                reference_answer="It is mock context 1", reference_context_ids=["doc_1_chunk_1"]
            )
        ]
    else:
        # In a real scenario, this would clone the huggingface repo, chunk the markdown,
        # generate a Ragas testset if missing, and output the jsonl.
        logger.warning("Real prepare not fully implemented for MVP beyond dry-run stubs.")
        # We will write out dummy records anyway for MVP to prevent breaking the pipeline.
        corpus = [CorpusRecord(id="d1", suite=suite_name, document_id="d1", text="Real context")]
        queries = [QueryRecord(id="q1", suite=suite_name, question="Real query", reference_answer="answer", reference_context_ids=["d1"])]
        
    write_jsonl(corpus_path, corpus)
    write_jsonl(queries_path, queries)
    logger.info(f"Wrote {len(corpus)} corpus records to {corpus_path}")
    logger.info(f"Wrote {len(queries)} queries to {queries_path}")
