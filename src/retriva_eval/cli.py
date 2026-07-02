# Copyright (C) 2026 Andrea Marson (am.dev.75@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import typer
from rich.console import Console
from rich.markdown import Markdown
import os
from typing import Optional

from retriva_eval.core.config import settings, VERSION
from retriva_eval.logger import setup_logging
from retriva_eval.core.registry import get_all_suite_names, get_suite
from retriva_eval.core.runner import run_suite_lifecycle, execute_pipeline
from retriva_eval.utils.time import generate_run_id


def _validate_portion(value: float) -> float:
    if not (0.0 < value <= 1.0):
        raise typer.BadParameter("--portion must be in the half-open interval (0.0, 1.0].")
    return value

setup_logging()

app = typer.Typer(help="retriva-eval: Continuous evaluation framework for Retriva")
console = Console()

@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        pass
    else:
        print(f"##### Retriva Eval ({VERSION}) #####\n")
        print("Active settings:")
        print(f"  Adapter:              {settings.retriva_adapter}")
        print(f"  Eval KB:              {settings.eval_knowledge_base}")
        print(f"  Metadata Filter Mode: {settings.eval_metadata_filtering_mode}")
        print(f"  Gateway Base URL:     {settings.gateway_base_url}")
        print(f"  Core Chat URL:        {settings.core_chat_base_url}")
        print(f"  LLM Provider:         {settings.llm_provider} ({settings.llm_model})")
        print(f"  Embedding Provider:   {settings.embedding_provider} ({settings.embedding_model})")
        print(
            f"  Concurrency:          ingest={settings.eval_ingest_concurrency} "
            f"(batch_size={settings.eval_ingest_batch_size}), "
            f"run={settings.eval_run_concurrency}, "
            f"judge={settings.eval_judge_concurrency}"
        )
        print()

@app.command()
def list_suites():
    """Print available suites and their status."""
    suites = get_all_suite_names()
    if not suites:
        console.print("No suites registered.")
        return
    for name in suites:
        console.print(f"- [green]{name}[/green]")

@app.command()
def run_suite(
    suite_name: str = typer.Argument(..., help="Name of the suite to run (e.g., 'email_ingestion')."),
    dry_run: bool = typer.Option(
        False, 
        "--dry-run", 
        help="Run the evaluation suite in dry-run mode. This skips all live API calls (no emails sent, no ingestion, no QA queries) and only simulates the process. Useful for verifying dataset parsing and configuration without mutating the database or using LLM tokens."
    ),
    portion: float = typer.Option(
        1.0,
        "--portion",
        help="Fraction of the dataset to randomly sample for this run. Must be a float strictly greater than 0.0 and up to 1.0. For example, 0.05 will randomly select 5% of the total dataset. Defaults to 1.0 (evaluates the full dataset).",
        callback=_validate_portion,
    ),
    seed: Optional[int] = typer.Option(
        None,
        "--seed",
        help="Optional random seed used to initialize the sub-sampling generator. Providing a seed ensures that the exact same random subset of the dataset is chosen across multiple runs, which is crucial for reproducing specific test failures. If not provided, it falls back to the suite's default configuration.",
    ),
    kb_id: Optional[str] = typer.Option(
        None,
        "--kb-id",
        help="Explicitly sets the Knowledge Base (KB) identifier that the evaluation suite will query during the verification stage. This overrides the default EVAL_KNOWLEDGE_BASE environment variable. Note: this does NOT rewrite the destination of the ingested files (for email ingestion routing, use --target-kb instead).",
    ),
    target_kb: Optional[str] = typer.Option(
        None,
        "--target-kb",
        help="Specifically designed for the email ingestion suite. This dynamically rewrites the 'KB' segment within the test email addresses (e.g., retriva+emails+<kb>+tags@domain) before they are sent. This guarantees the test emails land in the exact KB partition you specify. It automatically also sets --kb-id to the same value so the QA phase searches the correct partition.",
    ),
):
    """Runs one suite through the full lifecycle."""
    if target_kb:
        settings.email_target_kb = target_kb
        settings.eval_knowledge_base = target_kb
        print(f"  Target KB:             {target_kb} (from --target-kb)\n")
    if kb_id:
        settings.eval_knowledge_base = kb_id
        print(f"  KB Override:           {kb_id} (from --kb-id)\n")
    suite = get_suite(suite_name)
    run_id = generate_run_id()
    summary_path = run_suite_lifecycle(
        suite, settings, run_id, dry_run, portion=portion, seed=seed
    )

    if summary_path and os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            content = f.read()
        console.print("\n")
        console.print(Markdown(content))
        console.print("\n")

@app.command()
def run_cycle(
    pipeline_path: str = typer.Argument(..., help="Path to pipeline YAML file"),
    dry_run: bool = typer.Option(
        False, 
        "--dry-run", 
        help="Run the evaluation suite in dry-run mode. This skips all live API calls (no emails sent, no ingestion, no QA queries) and only simulates the process. Useful for verifying dataset parsing and configuration without mutating the database or using LLM tokens."
    ),
    portion: float = typer.Option(
        1.0,
        "--portion",
        help="Fraction of the dataset to randomly sample for this run. Must be a float strictly greater than 0.0 and up to 1.0. For example, 0.05 will randomly select 5% of the total dataset. Defaults to 1.0 (evaluates the full dataset).",
        callback=_validate_portion,
    ),
    seed: Optional[int] = typer.Option(
        None,
        "--seed",
        help="Optional random seed used to initialize the sub-sampling generator. Providing a seed ensures that the exact same random subset of the dataset is chosen across multiple runs, which is crucial for reproducing specific test failures. If not provided, it falls back to the suite's default configuration.",
    ),
    kb_id: Optional[str] = typer.Option(
        None,
        "--kb-id",
        help="Explicitly sets the Knowledge Base (KB) identifier that the evaluation suite will query during the verification stage. This overrides the default EVAL_KNOWLEDGE_BASE environment variable. Note: this does NOT rewrite the destination of the ingested files (for email ingestion routing, use --target-kb instead).",
    ),
    target_kb: Optional[str] = typer.Option(
        None,
        "--target-kb",
        help="Specifically designed for the email ingestion suite. This dynamically rewrites the 'KB' segment within the test email addresses (e.g., retriva+emails+<kb>+tags@domain) before they are sent. This guarantees the test emails land in the exact KB partition you specify. It automatically also sets --kb-id to the same value so the QA phase searches the correct partition.",
    ),
):
    """Runs all enabled suites in a pipeline file."""
    if target_kb:
        settings.email_target_kb = target_kb
        settings.eval_knowledge_base = target_kb
        print(f"  Target KB:             {target_kb} (from --target-kb)\n")
    if kb_id:
        settings.eval_knowledge_base = kb_id
        print(f"  KB Override:           {kb_id} (from --kb-id)\n")
    run_id = execute_pipeline(pipeline_path, settings, dry_run, portion=portion, seed=seed)
    
    summary_path = os.path.join(settings.eval_reports_dir, run_id, "summary.md")
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            content = f.read()
        console.print("\n")
        console.print(Markdown(content))
        console.print("\n")

if __name__ == "__main__":
    app()
