# Testing Strategy

## Unit Tests

Required tests:

- JSONL read/write utilities.
- Config loading and precedence.
- Schema validation for corpus, query, prediction, and metrics records.
- Threshold pass/fail calculation.
- Qdrant lifecycle safety logic.

## Integration Tests

Required tests:

- Suite contract test for `ragas_sample_markdown`.
- Dry-run mode that does not call external LLMs.
- Qdrant adapter test using local/in-memory mode where practical.

## Smoke Test

Command:

```bash
retriva-eval run-cycle pipelines/smoke.yaml
```

Expected:

- Creates a timestamped report directory.
- Runs at most 5 samples.
- Writes summary files.
- Does not delete Qdrant collection.

## CI Recommendation

Initial CI should run:

```bash
pytest
ruff check .
retriva-eval list-suites
```

Do not run LLM-dependent evaluation in PR CI unless credentials and cost controls are configured.
