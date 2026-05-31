# Acceptance Criteria

The generated repository is accepted when:

1. `pip install -e .[dev]` succeeds.
2. `retriva-eval list-suites` lists `ragas_sample_markdown`.
3. `pytest` passes.
4. `retriva-eval run-cycle pipelines/smoke.yaml` can run in dry-run mode without external LLM credentials.
5. A real run fails fast if the configured Qdrant collection does not exist.
6. A real run does not delete any Qdrant collection.
7. Reports are generated in `reports/<run_id>/`.
8. The first suite is sufficiently isolated to allow adding `ragbench` later without changing core contracts.
