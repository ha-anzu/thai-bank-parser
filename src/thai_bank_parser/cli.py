from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.progress import Progress
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .categorized import CATEGORIZED_COLUMNS, convert_to_categorized
from .io import read_csv, write_csv
from .ocr import OCR_DEVICE_CHOICES, render_table_pages, run_ocr
from .registry import get_template, list_templates
from .templates.krungsri import KrungsriTemplate
from .ui import MenuAction, goodbye, menu_panel, pause, progress_columns, splash, step_panel, success_panel, templates_table, validation_panel, make_console
from .validation import validate_rows


app = typer.Typer(
    add_completion=False,
    rich_markup_mode="rich",
    help="[bold red]Thai Bank Parser[/bold red] turns scanned Thai bank statements into clean CSV.",
)
console = make_console()


def banner(animate: bool = False) -> None:
    splash(console, animate=animate)


def print_validation(result) -> None:
    console.print(validation_panel(result))
    if result.ok:
        console.print("[bold green]PASS[/bold green] CSV is internally consistent.")
    else:
        console.print("[bold red]FAIL[/bold red] Review missing fields or balance mismatches.")


@app.command("templates")
def templates_command() -> None:
    """List available bank templates."""
    banner()
    console.print(templates_table(list_templates()))


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
    run_workflow_menu(single_run=True)


def run_convert_flow() -> Path:
    console.print(step_panel(1, "Choose the bank template", "Krungsri is implemented now; the registry is ready for more banks."))
    template_key = choose_template()
    console.print(step_panel(2, "Point to the statement PDF", "Use a local file path. The source PDF stays on this machine."))
    input_pdf = ask_path("Input PDF path")
    default_output = str(input_pdf.with_suffix(".csv")) if input_pdf.suffix else "statement.csv"
    output_csv = ask_path("Normalized CSV output path", default_output)
    default_work = str(output_csv.parent / ".thai-bank-parser-work" / input_pdf.stem)
    work_dir = ask_path("Local work/cache folder", default_work)
    console.print(step_panel(3, "Pick OCR behavior", "Auto tries the best available provider and falls back to CPU when needed."))
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
    return output_csv


def run_categorize_flow(input_csv: Path | None = None) -> Path:
    console.print(step_panel(1, "Choose the normalized CSV", "This should be the CSV created by `tbp convert`."))
    source_csv = input_csv or ask_path("Normalized CSV input path")
    default_categorized = str(source_csv.with_name(f"{source_csv.stem}_categorized.csv"))
    output_csv = ask_path("Categorized CSV output path", default_categorized)
    account_label = Prompt.ask("Account label for From/To", default="Account")
    additional_info = Prompt.ask("Additional_Info value", default="Converted by Thai Bank Parser")
    categorize_command(input_csv=source_csv, output_csv=output_csv, account_label=account_label, additional_info=additional_info)
    return output_csv


def run_validate_flow() -> None:
    console.print(step_panel(1, "Choose the CSV to validate", "The validator checks required fields and balance movement."))
    csv_path = ask_path("CSV path")
    validate_command(csv_path=csv_path)


def run_templates_flow() -> None:
    templates_command()


def run_workflow_menu(single_run: bool = False) -> None:
    banner(animate=True)
    actions = [
        MenuAction("1", "Full pipeline", "PDF -> normalized CSV -> categorized sheet"),
        MenuAction("2", "Convert statement", "PDF -> normalized CSV with OCR validation"),
        MenuAction("3", "Categorize sheet", "Normalized CSV -> sample-style categorized CSV"),
        MenuAction("4", "Validate CSV", "Check times, amounts, ISO datetimes, and balance deltas"),
        MenuAction("5", "Templates", "See implemented and planned bank templates"),
        MenuAction("q", "Quit", "Leave the command deck"),
    ]

    while True:
        console.print(menu_panel(actions))
        choice = Prompt.ask("[bold yellow]Select action[/bold yellow]", choices=["1", "2", "3", "4", "5", "q"], default="1")

        if choice == "1":
            normalized_csv = run_convert_flow()
            run_categorize_flow(normalized_csv)
            console.print(success_panel("Full pipeline complete", [f"Normalized: {normalized_csv}", "Categorized export written."]))
        elif choice == "2":
            output = run_convert_flow()
            console.print(success_panel("Conversion complete", [str(output)]))
        elif choice == "3":
            output = run_categorize_flow()
            console.print(success_panel("Categorized export complete", [str(output)]))
        elif choice == "4":
            run_validate_flow()
        elif choice == "5":
            run_templates_flow()
        else:
            goodbye(console)
            return

        if single_run:
            return
        pause(console)


@app.command("start")
def start_command() -> None:
    """Alias for the interactive wizard."""
    run_workflow_menu(single_run=False)


if __name__ == "__main__":
    app()
