# Implementation Plan for Antigravity

## Phase 1: Skeleton

- Create package structure.
- Add `pyproject.toml`.
- Add CLI using Typer.
- Add config loading.
- Add suite registry.

## Phase 2: Data Contracts

- Implement Pydantic models or dataclasses for:
  - `CorpusRecord`
  - `QueryRecord`
  - `PredictionRecord`
  - `MetricsRecord`
- Implement JSONL utilities.

## Phase 3: Adapters

- Implement Retriva HTTP client.
- Implement Qdrant adapter with manual-existing collection mode.
- Implement Ragas evaluator wrapper.

## Phase 4: ragas_sample_markdown Suite

- Implement `prepare.py`.
- Implement `ingest.py`.
- Implement `run.py`.
- Implement `evaluate.py`.

## Phase 5: Reports

- Implement JSON summary.
- Implement Markdown summary.
- Add optional JUnit XML placeholder.

## Phase 6: Tests and Documentation

- Add unit tests.
- Add smoke test docs.
- Add README usage instructions.
