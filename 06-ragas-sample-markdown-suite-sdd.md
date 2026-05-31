# Suite SDD: ragas_sample_markdown

## Purpose

The `ragas_sample_markdown` suite validates the end-to-end Retriva RAG pipeline using a small Markdown corpus and Ragas evaluation metrics.

## Dataset

Use a public sample Markdown dataset compatible with the Ragas testset generation guide.

## Suite Configuration

```yaml
name: ragas_sample_markdown
version: 0.1.0

dataset:
  source: huggingface_git
  repo: https://huggingface.co/datasets/vibrantlabsai/Sample_Docs_Markdown
  local_dir: suites/ragas_sample_markdown/data/Sample_Docs_Markdown
  glob: "**/*.md"

chunking:
  chunk_size: 800
  chunk_overlap: 120

testset:
  mode: generate_if_missing
  size: 25
  output_path: suites/ragas_sample_markdown/data/testset.jsonl

retrieval:
  top_k: 5

metrics:
  - faithfulness
  - answer_relevancy
  - context_precision
  - context_recall

thresholds:
  faithfulness: 0.75
  answer_relevancy: 0.70
  context_precision: 0.70
  context_recall: 0.70
```

## Implementation Notes

### prepare.py

Responsibilities:

- Ensure dataset directory exists.
- Clone or pull the Markdown dataset if missing.
- Load Markdown documents.
- Generate testset using Ragas if no cached testset exists.
- Write normalized `queries.jsonl` and `corpus.jsonl`.

### ingest.py

Responsibilities:

- Read `corpus.jsonl`.
- Embed chunks using configured embedding provider.
- Upsert points into configured Qdrant collection.

### run.py

Responsibilities:

- Read `queries.jsonl`.
- Call Retriva using configured adapter.
- Capture answer, retrieved contexts, latency, errors.
- Write `predictions.jsonl`.

### evaluate.py

Responsibilities:

- Convert predictions into Ragas evaluation dataset.
- Compute configured Ragas metrics.
- Compute operational metrics.
- Write `metrics.json`.

## Acceptance Criteria

- Running the suite produces all required output files.
- The suite fails fast when the Qdrant collection does not exist.
- The suite does not delete any Qdrant collection.
- A small smoke run with 3 to 5 samples works locally.
