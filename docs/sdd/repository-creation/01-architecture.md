# Architecture SDD

## High-Level Architecture

```text
retriva-eval
  ├─ CLI / Runner
  ├─ Suite Registry
  ├─ Suite Implementations
  │   └─ ragas_sample_markdown
  ├─ Retriva Client Adapter
  ├─ Qdrant Adapter
  ├─ Ragas Evaluator Adapter
  └─ Reporting Layer
```

## Evaluation Lifecycle

Every suite follows the same lifecycle:

```text
prepare -> ingest -> run -> evaluate -> report
```

### prepare

Downloads or materializes suite data into a local workspace.

### ingest

Indexes corpus chunks into the evaluation Qdrant collection. In the MVP, the collection already exists and is supplied via configuration.

### run

Executes questions against Retriva and stores normalized predictions.

### evaluate

Computes metrics using Ragas and internal operational metrics.

### report

Writes JSON, Markdown, and optional JUnit report files.

## MVP Runtime Flow

```text
1. Load pipeline YAML.
2. Load Retriva target configuration.
3. Resolve enabled suites.
4. For ragas_sample_markdown:
   a. Load/sample Markdown documents.
   b. Generate or load testset.
   c. Upsert corpus chunks into configured Qdrant eval collection.
   d. Query Retriva for each question.
   e. Save predictions.jsonl.
   f. Evaluate with Ragas.
   g. Save metrics.json and summary.md.
5. Aggregate suite results into reports/latest/summary.json and summary.md.
```

## Key Design Constraint

`retriva-eval` is Retriva-specific, but suite contracts should remain generic enough to evaluate alternative RAG clients in the future.
