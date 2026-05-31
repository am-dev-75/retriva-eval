# Functional Requirements

## FR-001 CLI

The repository shall expose a CLI named `retriva-eval`.

Required commands:

```bash
retriva-eval list-suites
retriva-eval run-suite <suite-name> --config <config-path>
retriva-eval run-cycle <pipeline-path>
```

## FR-002 Suite Lifecycle

Every suite shall implement:

- `prepare`
- `ingest`
- `run`
- `evaluate`
- `report`

## FR-003 First Suite

The first suite shall be named `ragas_sample_markdown`.

It shall:

- Use Markdown documents as source corpus.
- Generate or load a Ragas-compatible testset.
- Query Retriva for answers.
- Evaluate generated answers with Ragas metrics.

## FR-004 Qdrant Evaluation Collection

The MVP shall use an existing Qdrant collection configured by name.

The code shall:

- Verify that the configured collection exists.
- Fail fast with a clear error if it does not exist.
- Upsert suite documents/chunks into that collection.
- Avoid deleting the collection in MVP.

## FR-005 Future Collection Lifecycle

The architecture shall include a disabled-by-default configuration option for future collection lifecycle automation:

```yaml
qdrant:
  collection_lifecycle:
    mode: manual_existing # future: create_per_suite
    delete_on_completion: false
```

## FR-006 Outputs

Each run shall create:

```text
reports/<run_id>/summary.json
reports/<run_id>/summary.md
reports/<run_id>/<suite-name>/corpus.jsonl
reports/<run_id>/<suite-name>/queries.jsonl
reports/<run_id>/<suite-name>/predictions.jsonl
reports/<run_id>/<suite-name>/metrics.json
```
