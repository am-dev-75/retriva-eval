# CLI and Configuration SDD

## CLI Commands

### list-suites

```bash
retriva-eval list-suites
```

Print available suites and their enabled/disabled status.

### run-suite

```bash
retriva-eval run-suite ragas_sample_markdown --config configs/local.yaml
```

Runs one suite through the full lifecycle.

### run-cycle

```bash
retriva-eval run-cycle pipelines/smoke.yaml
```

Runs all enabled suites in a pipeline file.

## Config Precedence

1. CLI flags
2. Pipeline YAML
3. Config YAML
4. Environment variables
5. Built-in defaults

## Environment Variables

```bash
RETRIVA_ENDPOINT=http://localhost:8080/query
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
OPENAI_API_KEY=
AZURE_OPENAI_API_KEY=
```

## Example configs/local.yaml

```yaml
retriva:
  adapter: http
  endpoint_env: RETRIVA_ENDPOINT
  timeout_seconds: 60
  default_top_k: 5

qdrant:
  url_env: QDRANT_URL
  api_key_env: QDRANT_API_KEY
  collection_name: retriva_eval_manual
  vector_size: 1536
  distance: cosine
  collection_lifecycle:
    mode: manual_existing
    delete_on_completion: false

llm:
  provider: openai
  model: gpt-4o-mini

evaluation:
  reports_dir: reports
  fail_on_threshold_breach: true
```

## Example pipelines/smoke.yaml

```yaml
name: smoke
max_samples: 5

suites:
  - name: ragas_sample_markdown
    enabled: true
    max_samples: 5
```
