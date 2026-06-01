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

from retriva_eval.core.config import settings, VERSION
from retriva_eval.logger import setup_logging
from retriva_eval.core.registry import get_all_suite_names, get_suite
from retriva_eval.core.runner import run_suite_lifecycle, execute_pipeline
from retriva_eval.utils.time import generate_run_id

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
    suite_name: str = typer.Argument(..., help="Name of the suite to run"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run without live API calls"),
):
    """Runs one suite through the full lifecycle."""
    suite = get_suite(suite_name)
    run_id = generate_run_id()
    run_suite_lifecycle(suite, settings, run_id, dry_run)

@app.command()
def run_cycle(
    pipeline_path: str = typer.Argument(..., help="Path to pipeline YAML file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run without live API calls"),
):
    """Runs all enabled suites in a pipeline file."""
    run_id = execute_pipeline(pipeline_path, settings, dry_run)
    
    summary_path = os.path.join(settings.eval_reports_dir, run_id, "summary.md")
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            content = f.read()
        console.print("\n")
        console.print(Markdown(content))
        console.print("\n")

if __name__ == "__main__":
    app()
