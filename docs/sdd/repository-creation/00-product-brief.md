# Product Brief: retriva-eval

`retriva-eval` is the continuous evaluation and regression-testing framework for Retriva, Andrea Marson's Retrieval-Augmented Generation system.

The repository shall provide a common runner for multiple RAG evaluation suites. The MVP implements one suite named `ragas_sample_markdown`, based on Ragas synthetic testset generation over a public sample Markdown dataset.

## Goals

- Evaluate Retriva continuously and automatically.
- Normalize evaluation inputs and outputs across suites.
- Keep suite implementations isolated.
- Produce machine-readable reports suitable for CI/CD quality gates.
- Start with a manually-created Qdrant collection for evaluation.
- Prepare the architecture for future suite-scoped Qdrant collection lifecycle management.

## Non-goals for MVP

- No automatic Qdrant collection creation/deletion yet.
- No UI/dashboard.
- No multiple benchmark suites yet.
- No vendor-specific lock-in beyond configurable LLM/embedding providers used by Ragas.
