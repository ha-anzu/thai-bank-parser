from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from .categorized import CATEGORIZED_COLUMNS, convert_to_categorized
from .io import read_csv, write_csv
from .ocr import render_table_pages, run_ocr
from .registry import get_template, list_templates
from .templates.krungsri import KrungsriTemplate
from .validation import validate_rows


app = typer.Typer(
    add_completion=False,
    rich_markup_mode="rich",
    help="[bold red]Thai Bank Parser[/bold red] turns scanned Thai bank statements into clean CSV.",
)
console = Console()


def banner() -> None:
    title = Text("THAI BANK PARSER", style="bold yellow")
    subtitle = Text("local OCR -> bank template -> verified CSV", style="red")
    console.print(Panel.fit(Text.assemble(title, "\n", subtitle), border_style="red"))


def print_validation(result) -> None:
    table = Table(title="Validation", border_style="yellow", header_style="bold red")
    table.add_column("Check")
    table.add_column("Value", justify="right")
    table.add_row("Rows", str(result.rows))
    table.add_row("Deposits / in", str(result.deposits))
    table.add_row("Withdrawals / out", str(result.withdrawals))
    table.add_row("Missing times", str(result.missing_times))
    table.add_row("Missing ISO datetimes", str(result.missing_iso_datetimes))
    table.add_row("Missing amounts", str(result.missing_amounts))
    table.add_row("Bad balance deltas", str(result.bad_balance_deltas))
    console.print(table)
    if result.ok:
        console.print("[bold green]PASS[/bold green] CSV is internally consistent.")
    else:
        console.print("[bold red]FAIL[/bold red] Review missing fields or balance mismatches.")


@app.command("templates")
def templates_command() -> None:
    """List available bank templates."""
    banner()
    table = Table(title="Templates", border_style="yellow", header_style="bold red")
    table.add_column("Key", style="bold yellow")
    table.add_column("Bank")
    table.add_column("Status")
    table.add_column("Description")
    for template in list_templates():
        info = template.info
        status_style = "green" if info.status == "implemented" else "dim"
        table.add_row(info.key, info.bank, f"[{status_style}]{info.status}[/{status_style}]", info.description)
    console.print(table)


@app.command("convert")
def convert_command(
    input_pdf: Path = typer.Option(..., "--input", "-i", exists=True, readable=True, help="Input statement PDF."),
    output_csv: Path = typer.Option(..., "--output", "-o", help="Output CSV path."),
    template_key: str = typer.Option("krungsri", "--template", "-t", help="Bank template key."),
    work_dir: Optional[Path] = typer.Option(None, "--work-dir", help="Local OCR/render cache directory."),
    force_ocr: bool = typer.Option(False, "--force-ocr", help="Ignore cached OCR and run OCR again."),
    debug_json: Optional[Path] = typer.Option(None, "--debug-json", help="Write OCR boxes for local debugging."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only print final result."),
) -> None:
    """Convert a scanned statement PDF into normalized CSV."""
    template = get_template(template_key)
    if not isinstance(template, KrungsriTemplate):
        raise typer.BadParameter(f"Template '{template_key}' is listed but not implemented yet.")
    local_work_dir = work_dir or output_csv.parent / ".thai-bank-parser-work" / input_pdf.stem

    if not quiet:
        banner()
        console.print(f"[dim]Template:[/dim] [bold yellow]{template.info.key}[/bold yellow]  [dim]Input:[/dim] {input_pdf}")

    if quiet:
        image_paths = render_table_pages(input_pdf, local_work_dir, template.table_crop, template.render_scale)
        boxes = run_ocr(image_paths, local_work_dir / "ocr_boxes.json", force_ocr, debug_json)
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold red]{task.description}"),
            BarColumn(bar_width=36),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            render_task = progress.add_task("Rendering pages", total=1)

            def render_progress(_stage: str, current: int, total: int) -> None:
                progress.update(render_task, total=total, completed=current)

            image_paths = render_table_pages(input_pdf, local_work_dir, template.table_crop, template.render_scale, render_progress)
            ocr_task = progress.add_task("Reading statement", total=len(image_paths))

            def ocr_progress(_stage: str, current: int, total: int) -> None:
                progress.update(ocr_task, total=total, completed=current)

            boxes = run_ocr(image_paths, local_work_dir / "ocr_boxes.json", force_ocr, debug_json, ocr_progress)

    rows = template.parse(boxes, input_pdf)
    write_csv(rows, output_csv)
    result = validate_rows(rows)

    if quiet:
        console.print(f"{output_csv} rows={result.rows} missing_times={result.missing_times} missing_amounts={result.missing_amounts} bad_balance_deltas={result.bad_balance_deltas}")
    else:
        print_validation(result)
        console.print(f"[bold green]Wrote[/bold green] {output_csv}")

    if not result.ok:
        raise typer.Exit(code=2)


@app.command("validate")
def validate_command(
    csv_path: Path = typer.Option(..., "--csv", "-c", exists=True, readable=True, help="CSV generated by this tool."),
) -> None:
    """Validate an exported CSV for missing fields and balance deltas."""
    banner()
    rows = read_csv(csv_path)
    result = validate_rows(rows)
    print_validation(result)
    if not result.ok:
        raise typer.Exit(code=2)


@app.command("categorize")
def categorize_command(
    input_csv: Path = typer.Option(..., "--input", "-i", exists=True, readable=True, help="Normalized parser CSV."),
    output_csv: Path = typer.Option(..., "--output", "-o", help="Categorized CSV output path."),
    account_label: str = typer.Option("Account", "--account-label", help="Label for the account owner side."),
    additional_info: str = typer.Option("", "--additional-info", help="Static Additional_Info value."),
) -> None:
    """Convert normalized CSV into the categorized sheet schema."""
    banner()
    rows = convert_to_categorized(input_csv, output_csv, account_label, additional_info)
    table = Table(title="Categorized Export", border_style="yellow", header_style="bold red")
    table.add_column("Output")
    table.add_column("Rows", justify="right")
    table.add_column("Schema", justify="right")
    table.add_row(str(output_csv), str(len(rows)), f"{len(CATEGORIZED_COLUMNS)} columns")
    console.print(table)
    console.print("[bold green]Wrote categorized sheet[/bold green]")


if __name__ == "__main__":
    app()
