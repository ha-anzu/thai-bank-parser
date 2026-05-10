from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.markup import escape
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text


BRAND_RED = "bold red"
BRAND_YELLOW = "bold yellow"
BRAND_DIM = "dim"

PANDA_FRAMES = [
    r"""
    /\_/\
   ( o.o )  audit mode
    > ^ <   watching columns
""",
    r"""
    /\_/\
   ( -.- )  sniffing OCR
    > ^ <   checking cache
""",
    r"""
    /\_/\
   ( ^.^ )  rows aligned
    > ^ <   CSV ready
""",
]


@dataclass(frozen=True)
class MenuAction:
    key: str
    title: str
    detail: str


def make_console() -> Console:
    return Console()


def brand_panel(*renderables, title: str = "TBP", subtitle: str = "", border_style: str = "red") -> Panel:
    return Panel(
        Group(*renderables),
        title=f"[bold yellow]{title}[/bold yellow]",
        subtitle=f"[dim]{subtitle}[/dim]" if subtitle else "",
        border_style=border_style,
        box=box.HEAVY_EDGE,
        padding=(1, 2),
    )


def splash(console: Console, animate: bool = True) -> None:
    if not animate or not console.is_interactive:
        console.print(hero_frame(PANDA_FRAMES[-1], "READY"))
        return

    frames = [
        ("BOOT", PANDA_FRAMES[0], "local-first OCR console"),
        ("TRACE", PANDA_FRAMES[1], "render -> read -> reconcile"),
        ("READY", PANDA_FRAMES[2], "private data stays local"),
    ]
    with Live(console=console, refresh_per_second=10, transient=True) as live:
        for label, panda, line in frames:
            live.update(hero_frame(panda, label, line))
            time.sleep(0.38)
    console.print(hero_frame(PANDA_FRAMES[-1], "READY", "private data stays local"))


def hero_frame(panda: str, state: str, line: str = "playful local OCR for serious CSV cleanup") -> Panel:
    title = Text("THAI BANK PARSER", style=BRAND_YELLOW)
    title.stylize("bold")
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(width=24)
    grid.add_column(ratio=1)
    grid.add_row(
        Text(panda, style=BRAND_RED, no_wrap=False),
        Group(
            Text("HANZU OPEN TOOLS // LOCAL BANK OCR", style=BRAND_DIM),
            Text.assemble(title, "  ", Text(f"[{state}]", style=BRAND_RED)),
            Text(line, style="white"),
            Text("convert PDFs  |  validate balances  |  export categorized sheets", style=BRAND_DIM),
        ),
    )
    return brand_panel(grid, title="red panda console", subtitle="offline-capable / scriptable / interactive")


def progress_columns() -> tuple:
    return (
        SpinnerColumn(spinner_name="dots12", style=BRAND_RED),
        TextColumn("[bold red]{task.description}"),
        BarColumn(bar_width=34, complete_style="yellow", finished_style="green"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    )


def menu_panel(actions: Iterable[MenuAction]) -> Panel:
    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(justify="right", width=5)
    table.add_column(ratio=1)
    for action in actions:
        table.add_row(
            f"[bold yellow]\\[{escape(action.key)}][/bold yellow]",
            f"[bold white]{action.title}[/bold white]\n[dim]{action.detail}[/dim]",
        )
    return brand_panel(table, title="command deck", subtitle="choose a workflow")


def step_panel(number: int, title: str, detail: str) -> Panel:
    label = Text(f"STEP {number:02d}", style=BRAND_YELLOW)
    body = Group(label, Text(title, style="bold white"), Text(detail, style=BRAND_DIM))
    return Panel(body, border_style="yellow", box=box.ROUNDED, padding=(1, 2))


def success_panel(title: str, lines: Iterable[str]) -> Panel:
    body = Group(Text(title, style="bold green"), *(Text(line, style="white") for line in lines))
    return Panel(body, border_style="green", box=box.HEAVY_EDGE, padding=(1, 2))


def validation_panel(result) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(style=BRAND_DIM)
    table.add_column(justify="right", style="bold white")
    table.add_row("Rows", str(result.rows))
    table.add_row("Deposits / in", str(result.deposits))
    table.add_row("Withdrawals / out", str(result.withdrawals))
    table.add_row("Missing times", str(result.missing_times))
    table.add_row("Missing ISO datetimes", str(result.missing_iso_datetimes))
    table.add_row("Missing amounts", str(result.missing_amounts))
    table.add_row("Bad balance deltas", str(result.bad_balance_deltas))
    title = "validation pass" if result.ok else "validation needs review"
    style = "green" if result.ok else "red"
    return Panel(table, title=f"[bold {style}]{title}[/bold {style}]", border_style=style, box=box.HEAVY_EDGE)


def templates_table(templates) -> Table:
    table = Table(title="Template Bay", border_style="yellow", header_style="bold red", box=box.SIMPLE_HEAVY)
    table.add_column("Key", style=BRAND_YELLOW)
    table.add_column("Bank")
    table.add_column("Status")
    table.add_column("Notes")
    for template in templates:
        info = template.info
        status_style = "green" if info.status == "implemented" else "dim"
        table.add_row(info.key, info.bank, f"[{status_style}]{info.status}[/{status_style}]", info.description)
    return table


def pause(console: Console) -> None:
    if console.is_interactive:
        console.input("[dim]Press Enter to return to the command deck...[/dim]")


def goodbye(console: Console) -> None:
    console.print(Align.center(Text("red panda clerk signing off - keep the data private", style=BRAND_DIM)))
