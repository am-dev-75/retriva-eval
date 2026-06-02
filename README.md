# retriva-eval

`retriva-eval` is the continuous evaluation and regression-testing framework for [Retriva](https://github.com/am-dev-75/retriva-eval).

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

Ensure `RETRIVA_ENDPOINT` and `QDRANT_API_KEY` are correctly set. See [.env.example](.env.example) for more information.

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

## Architecture

```
┌───────────────────────────┐
│ retriva-eval CLI          │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ Pipeline Config           │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ Evaluation Coordinator    │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│         Stages            │
│ ┌─────────┬─────────┐   │
│ │ Ingest  │  Run    │   │
│ │         │         │   │
│ └─────────┴─────────┘   │
└─────────────┬───────────┘
              │
              ▼
┌───────────────────────────┐
│  Reporting                │
│ ┌─────────┬─────────┐   │
│ │ Markdown│  JSON   │   │
│ │         │         │   │
│ └─────────┴─────────┘   │
└───────────────────────────┘
```

The `Pipeline Config` is loaded from a YAML file, which defines the evaluation parameters, suites, and metrics to use. It also defines the `Evaluation Coordinator`, which is the main entry point for the evaluation process. The `Coordinator` is responsible for executing the evaluation in `stages`, which are: `Ingest`, `Run`, and `Reporting`. 

## Available Suites

### ragas

Ragas metrics over a Markdown document dataset.

### ragbench

The `ragbench` suite is designed to test the Retriva pipeline against the [RAGBench](https://huggingface.co/datasets/galileo-ai/ragbench) dataset.

It integrates into `retriva-eval`'s four-stage lifecycle:
1. **Prepare**: Downloads the 12 RAGBench dataset subsets, deduplicates contexts, formats them into `corpus.jsonl` and `queries.jsonl`, and attaches subset metadata to each query.
2. **Ingest**: Ingests the parsed contexts into the vector database (Qdrant).
3. **Run**: Runs the queries against the Retriva chat APIs.
4. **Evaluate**: Uses an LLM-as-judge (`RagbenchJudge`) to compute native RAGBench metrics, outputting reports with a per-subset breakdown.

You can run the `ragbench` suite with:

```bash
retriva-eval run-suite ragbench [OPTIONS]
```

**Options:**
- `--dry-run`: Tests the pipeline locally without live API calls (generates a tiny mock dataset during the `prepare` stage).
- `--portion FLOAT`: Controls the fraction of the dataset to use, from `0.0` (exclusive) to `1.0` (inclusive). Useful for sub-sampled evaluations. Default is `1.0`.
- `--seed INTEGER`: Random seed for reproducible sub-sampling when using `--portion`. Overrides the suite's default seed.

### Execution Reports

All suites store their execution results and evaluation artifacts in the `reports/<run_id>/<suite_name>/` directory (configurable via `EVAL_REPORTS_DIR`). 

These results follow a standardized format across all suites:
- **`corpus.jsonl`**: The normalized context documents used for the evaluation.
- **`queries.jsonl`**: The dataset containing questions, reference answers, and metadata.
- **`predictions.jsonl`**: The generated answers and retrieved contexts produced by testing the Retriva APIs.
- **`metrics.json`**: The final computed metrics (including per-subset breakdowns, if applicable).
- **Markdown summaries**: Automatically generated human-readable reports of the evaluation run.

## Licensing

This project, including all source code, agentic specifications, and documentation, is licensed under the Apache License 2.0. See the LICENSE file for details.