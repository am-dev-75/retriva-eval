# Workflow: Implement retriva-eval MVP

Goal: Create the initial `retriva-eval` repository with the `ragas_sample_markdown` suite.

## Step 1: Plan

Read all SDD files in this pack. Produce a short implementation plan and list files to create.

## Step 2: Scaffold

Create the repository structure from `02-repository-structure.md`.

## Step 3: Core Package

Implement:

- CLI
- config loader
- suite interface
- suite registry
- runner
- data schemas
- JSONL utilities

## Step 4: Adapters

Implement:

- Retriva HTTP adapter
- Qdrant adapter using manual-existing collection mode
- Ragas evaluator adapter

## Step 5: First Suite

Implement `suites/ragas_sample_markdown`:

- prepare
- ingest
- run
- evaluate

Include dry-run support.

## Step 6: Tests

Add unit and integration tests.

## Step 7: Verify

Run:

```bash
pip install -e .[dev]
pytest
retriva-eval list-suites
retriva-eval run-cycle pipelines/smoke.yaml --dry-run
```

## Step 8: Report

Provide a final artifact containing:

- implementation summary
- files changed
- commands run
- test results
- known limitations
- next recommended step
