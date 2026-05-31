import typer
from rich.console import Console

from retriva_eval.core.config import settings
from retriva_eval.logger import setup_logging
from retriva_eval.core.registry import get_all_suite_names, get_suite
from retriva_eval.core.runner import run_suite_lifecycle, execute_pipeline
from retriva_eval.utils.time import generate_run_id

setup_logging()

app = typer.Typer(help="retriva-eval: Continuous evaluation framework for Retriva")
console = Console()

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
    execute_pipeline(pipeline_path, settings, dry_run)

if __name__ == "__main__":
    app()
