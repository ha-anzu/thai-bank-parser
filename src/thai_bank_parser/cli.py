from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from .categorized import CATEGORIZED_COLUMNS, convert_to_categorized
from .io import read_csv, write_csv
from .ocr import OCR_DEVICE_CHOICES, render_table_pages, run_ocr
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
    mascot = Text(
        r"""
   /\_/\
  ( o.o )  red panda clerk
   > ^ <   scan -> sort -> verify
""",
        style="bold red",
    )
    title = Text("TBP // THAI BANK PARSER", style="bold yellow")
    subtitle = Text("playful local OCR for serious CSV cleanup", style="red")
    console.print(Panel.fit(Text.assemble(mascot, "\n", title, "\n", subtitle), border_style="red", box=box.ROUNDED))


def progress_columns() -> tuple:
    return (
        SpinnerColumn(spinner_name="dots12", style="bold red"),
        TextColumn("[bold red]{task.description}"),
        BarColumn(bar_width=36, complete_style="yellow", finished_style="green"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    )


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
    ocr_device: str = typer.Option(
        "auto",
        "--ocr-device",
        case_sensitive=False,
        help="OCR execution preference: auto, cpu, cuda, or dml.",
    ),
    debug_json: Optional[Path] = typer.Option(None, "--debug-json", help="Write OCR boxes for local debugging."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only print final result."),
) -> None:
    """Convert a scanned statement PDF into normalized CSV."""
    if ocr_device.lower() not in OCR_DEVICE_CHOICES:
        raise typer.BadParameter(f"OCR device must be one of: {', '.join(OCR_DEVICE_CHOICES)}")
    template = get_template(template_key)
    if not isinstance(template, KrungsriTemplate):
        raise typer.BadParameter(f"Template '{template_key}' is listed but not implemented yet.")
    local_work_dir = work_dir or output_csv.parent / ".thai-bank-parser-work" / input_pdf.stem

    if not quiet:
        banner()
        console.print(f"[dim]Template:[/dim] [bold yellow]{template.info.key}[/bold yellow]  [dim]Input:[/dim] {input_pdf}")

    def device_notice(active_device: str, fallback_reason: str, providers: list[str]) -> None:
        if quiet:
            return
        provider_text = ", ".join(providers) if providers else "none"
        if fallback_reason:
            console.print(f"[yellow]OCR device:[/yellow] {active_device}  [dim]({fallback_reason})[/dim]")
        else:
            console.print(f"[green]OCR device:[/green] {active_device}")
        console.print(f"[dim]ONNX providers: {provider_text}[/dim]")

    if quiet:
        image_paths = render_table_pages(input_pdf, local_work_dir, template.table_crop, template.render_scale)
        boxes = run_ocr(image_paths, local_work_dir / "ocr_boxes.json", force_ocr, debug_json, ocr_device)
    else:
        with Progress(*progress_columns(), console=console) as progress:
            render_task = progress.add_task("Rendering pages", total=1)

            def render_progress(_stage: str, current: int, total: int) -> None:
                progress.update(render_task, total=total, completed=current)

            image_paths = render_table_pages(input_pdf, local_work_dir, template.table_crop, template.render_scale, render_progress)
            ocr_task = progress.add_task("Reading statement", total=len(image_paths))

            def ocr_progress(_stage: str, current: int, total: int) -> None:
                progress.update(ocr_task, total=total, completed=current)

            boxes = run_ocr(
                image_paths,
                local_work_dir / "ocr_boxes.json",
                force_ocr,
                debug_json,
                ocr_device,
                device_notice,
                ocr_progress,
            )

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
    with console.status("[bold red]Red panda is reshaping the sheet...[/bold red]", spinner="dots12"):
        rows = convert_to_categorized(input_csv, output_csv, account_label, additional_info)
    table = Table(title="Categorized Export", border_style="yellow", header_style="bold red")
    table.add_column("Output")
    table.add_column("Rows", justify="right")
    table.add_column("Schema", justify="right")
    table.add_row(str(output_csv), str(len(rows)), f"{len(CATEGORIZED_COLUMNS)} columns")
    console.print(table)
    console.print("[bold green]Wrote categorized sheet[/bold green]")


def ask_path(label: str, default: str = "") -> Path:
    value = Prompt.ask(f"[bold yellow]{label}[/bold yellow]", default=default if default else None)
    return Path(value.strip('"'))


def choose_template() -> str:
    implemented = [template.info.key for template in list_templates() if template.info.status == "implemented"]
    default = implemented[0] if implemented else "krungsri"
    answer = Prompt.ask(
        "[bold yellow]Bank template[/bold yellow]",
        choices=implemented,
        default=default,
        show_choices=True,
    )
    return answer


@app.command("wizard")
def wizard_command() -> None:
    """Run an interactive step-by-step guide."""
    banner()
    console.print("[bold yellow]Choose a path:[/bold yellow]")
    console.print("  [red]1[/red] Convert PDF -> normalized CSV")
    console.print("  [red]2[/red] Categorize normalized CSV -> categorized sheet")
    console.print("  [red]3[/red] Convert PDF -> normalized CSV -> categorized sheet")
    choice = Prompt.ask("Mode", choices=["1", "2", "3"], default="3")

    normalized_csv: Path | None = None
    if choice in {"1", "3"}:
        template_key = choose_template()
        input_pdf = ask_path("Input PDF path")
        default_output = str(input_pdf.with_suffix(".csv")) if input_pdf.suffix else "statement.csv"
        output_csv = ask_path("Normalized CSV output path", default_output)
        default_work = str(output_csv.parent / ".thai-bank-parser-work" / input_pdf.stem)
        work_dir = ask_path("Local work/cache folder", default_work)
        force_ocr = Confirm.ask("Force OCR instead of using cache?", default=False)
        ocr_device = Prompt.ask(
            "OCR device preference",
            choices=list(OCR_DEVICE_CHOICES),
            default="auto",
            show_choices=True,
        )

        convert_command(
            input_pdf=input_pdf,
            output_csv=output_csv,
            template_key=template_key,
            work_dir=work_dir,
            force_ocr=force_ocr,
            ocr_device=ocr_device,
            debug_json=None,
            quiet=False,
        )
        normalized_csv = output_csv

    if choice in {"2", "3"}:
        input_csv = normalized_csv or ask_path("Normalized CSV input path")
        default_categorized = str(input_csv.with_name(f"{input_csv.stem}_categorized.csv"))
        output_csv = ask_path("Categorized CSV output path", default_categorized)
        account_label = Prompt.ask("Account label for From/To", default="Account")
        additional_info = Prompt.ask("Additional_Info value", default="Converted by Thai Bank Parser")
        categorize_command(input_csv=input_csv, output_csv=output_csv, account_label=account_label, additional_info=additional_info)


@app.command("start")
def start_command() -> None:
    """Alias for the interactive wizard."""
    wizard_command()


if __name__ == "__main__":
    app()
