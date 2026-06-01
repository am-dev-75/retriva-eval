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
from retriva_eval.core.config import Settings
from retriva_eval.core.schemas import CorpusRecord, QueryRecord
from retriva_eval.utils.io import write_jsonl
from retriva_eval.logger import get_logger

logger = get_logger("ragas_suite_prepare")

def do_prepare(suite_name: str, settings: Settings, run_id: str, dry_run: bool) -> None:
    reports_dir = os.path.join(settings.eval_reports_dir, run_id, suite_name)
    os.makedirs(reports_dir, exist_ok=True)
    
    corpus_path = os.path.join(reports_dir, "corpus.jsonl")
    queries_path = os.path.join(reports_dir, "queries.jsonl")
    
    logger.info("Generating meaningful sample markdown corpus and queries.")
    corpus = [
        CorpusRecord(
            id="doc_1_chunk_1", 
            suite=suite_name, 
            document_id="platypus_doc", 
            text="## The Platypus\nThe **platypus** is a semiaquatic, egg-laying mammal endemic to eastern Australia. It is one of the five extant species of monotremes, the only mammals that lay eggs instead of giving birth to live young."
        ),
        CorpusRecord(
            id="doc_1_chunk_2", 
            suite=suite_name, 
            document_id="platypus_doc", 
            text="### Venom\nUnlike most mammals, male platypuses are venomous. They have a spur on the hind foot that delivers a venom capable of causing severe pain to humans."
        ),
    ]
    queries = [
        QueryRecord(
            id="q_1", 
            suite=suite_name, 
            question="What kind of mammal is the platypus?",
            reference_answer="The platypus is a semiaquatic, egg-laying mammal (a monotreme).", 
            reference_context_ids=["doc_1_chunk_1"]
        ),
        QueryRecord(
            id="q_2", 
            suite=suite_name, 
            question="Are platypuses venomous to humans?",
            reference_answer="Yes, male platypuses have a spur on their hind foot that can deliver venom causing severe pain to humans.", 
            reference_context_ids=["doc_1_chunk_2"]
        )
    ]
        
    write_jsonl(corpus_path, corpus)
    write_jsonl(queries_path, queries)
    logger.info(f"Wrote {len(corpus)} corpus records to {corpus_path}")
    logger.info(f"Wrote {len(queries)} queries to {queries_path}")
