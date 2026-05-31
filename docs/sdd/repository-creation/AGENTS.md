# Agent Instructions for retriva-eval

You are building `retriva-eval`, the continuous evaluation harness for Retriva.

Follow these rules:

1. Keep the framework modular and suite-driven.
2. Implement the first suite only: `ragas_sample_markdown`.
3. Do not implement programmatic Qdrant collection creation/deletion in MVP.
4. Do implement safe abstractions so future collection lifecycle automation is easy.
5. Never delete a manually configured Qdrant collection.
6. Prefer clear, testable Python code.
7. All outputs must be deterministic in dry-run mode.
8. Add tests before or together with implementation.
9. Produce useful Markdown and JSON reports.
10. Keep secrets in environment variables, never in code.
