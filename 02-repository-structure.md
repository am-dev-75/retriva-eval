# Repository Structure SDD

Create the repository as follows:

```text
retriva-eval/
  README.md
  pyproject.toml
  .env.example
  .gitignore

  configs/
    default.yaml
    local.yaml

  pipelines/
    smoke.yaml
    nightly.yaml

  src/
    retriva_eval/
      __init__.py
      cli.py

      core/
        __init__.py
        suite.py
        runner.py
        registry.py
        schemas.py
        config.py
        result.py

      adapters/
        __init__.py
        retriva_http.py
        qdrant_store.py
        ragas_eval.py

      reporting/
        __init__.py
        json_report.py
        markdown_report.py
        junit_report.py

      utils/
        __init__.py
        io.py
        logging.py
        time.py

  suites/
    ragas_sample_markdown/
      README.md
      suite.yaml
      prepare.py
      ingest.py
      run.py
      evaluate.py
      data/
        .gitkeep

  tests/
    unit/
      test_schemas.py
      test_runner.py
    integration/
      test_ragas_sample_contract.py

  reports/
    .gitkeep
```

## Packaging

Use a modern Python package layout with `src/` and expose a CLI command:

```bash
retriva-eval run-cycle pipelines/smoke.yaml
retriva-eval run-suite ragas_sample_markdown --config configs/local.yaml
retriva-eval list-suites
```
