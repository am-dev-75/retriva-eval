# retriva-eval

`retriva-eval` is the continuous evaluation and regression-testing framework for Retriva.

## Features

- **Suite-driven evaluation**: Isolate evaluation datasets and metrics into self-contained suites (e.g., `ragas_sample_markdown`).
- **Standardized Data Contracts**: Normalized JSONL outputs for corpus, queries, and predictions.
- **Dry-run Capabilities**: Test pipelines locally without invoking live APIs.
- **Safety First**: Manual existing-collection mode for Qdrant prevents accidental deletion.
- **Comprehensive Reporting**: Automatically generates Markdown and JSON summaries.

## Getting Started

### Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### Configuration

Copy the example environment file and configure your credentials:

```bash
cp .env.example .env
```

Ensure `RETRIVA_ENDPOINT` and `QDRANT_API_KEY` are correctly set.

### Running Evaluations

List available suites:

```bash
retriva-eval list-suites
```

Run a dry-run smoke test:

```bash
retriva-eval run-cycle pipelines/smoke.yaml --dry-run
```

Run a specific suite:

```bash
retriva-eval run-suite ragas_sample_markdown
```

## Testing

To run the unit and integration test suite:

```bash
pytest
```
