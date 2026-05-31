# Qdrant Strategy SDD

Retriva uses Qdrant as its vector database.

## MVP Strategy

For the first implementation, the user manually creates a dedicated Qdrant collection for evaluation.

The evaluation framework shall receive this collection name through configuration:

```yaml
qdrant:
  url: http://localhost:6333
  api_key_env: QDRANT_API_KEY
  collection_name: retriva_eval_manual
  vector_size: 1536
  distance: cosine
  collection_lifecycle:
    mode: manual_existing
    delete_on_completion: false
```

## Required MVP Behavior

The Qdrant adapter shall:

1. Connect to Qdrant using URL and optional API key.
2. Check that `collection_name` exists.
3. Validate vector size if practical.
4. Upsert evaluation chunks with suite/run metadata.
5. Never delete the collection in MVP.

## Payload Metadata

Each upserted point should include:

```json
{
  "suite": "ragas_sample_markdown",
  "run_id": "20260531T090000Z",
  "document_id": "doc_001",
  "chunk_id": "doc_001_chunk_0001",
  "source_file": "...",
  "text": "..."
}
```

## Future Strategy

Add support for suite-scoped ephemeral collections:

```yaml
qdrant:
  collection_lifecycle:
    mode: create_per_suite
    name_template: "retriva_eval_{suite}_{run_id}"
    delete_on_completion: true
```

Future behavior:

```text
for each suite:
  create collection
  ingest suite corpus
  run evaluation
  delete collection if delete_on_completion = true
```

## Safety Rules

- Never delete a collection unless `collection_lifecycle.mode == create_per_suite`.
- Never delete a collection whose name was supplied manually by the user.
- Require an explicit config flag before deletion.
- Log the collection lifecycle decision at the beginning and end of every suite run.
