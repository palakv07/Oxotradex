"""Rich logger and console reporting utilities for Alpaca Options Alpha Agent."""

import logging
import sys
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Initialize Rich Console with utf-8 or ascii fallback
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(safe_box=True)

# Standard Python logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AlpacaAlphaAgent")


def log_header(title: str, subtitle: Optional[str] = None):
    """Print an eye-catching formatted panel header."""
    text = Text(title, style="bold cyan")
    if subtitle:
        text.append(f"\n{subtitle}", style="dim white")
    console.print(Panel(text, border_style="cyan", expand=False))


def log_info(msg: str):
    """Log an informative message."""
    console.print(f"[bold blue][*] [INFO][/bold blue] {msg}")


def log_success(msg: str):
    """Log a success message."""
    console.print(f"[bold green][+] [SUCCESS][/bold green] {msg}")


def log_warning(msg: str):
    """Log a warning message."""
    console.print(f"[bold yellow][!] [WARNING][/bold yellow] {msg}")


def log_error(msg: str):
    """Log an error message."""
    console.print(f"[bold red][X] [ERROR][/bold red] {msg}")


def log_risk_gate(gate_name: str, approved: bool, reason: str):
    """Log the evaluation of a deterministic risk gate."""
    if approved:
        console.print(f"  [bold green]PASSED[/bold green] | [bold]{gate_name}[/bold]: {reason}")
    else:
        console.print(f"  [bold red]BLOCKED[/bold red] | [bold]{gate_name}[/bold]: [bold red]{reason}[/bold red]")


def log_trade_proposal(candidate: Dict[str, Any], status: str, contracts: int):
    """Log a formatted summary of an options trade candidate."""
    table = Table(title=f"Trade Setup: {candidate.get('symbol')} {candidate.get('strategy_type')}", show_header=True)
    table.add_column("Symbol", style="cyan")
    table.add_column("Strategy", style="magenta")
    table.add_column("Expiry (DTE)", style="yellow")
    table.add_column("Strikes", style="white")
    table.add_column("Net Credit", style="green")
    table.add_column("Max Loss", style="red")
    table.add_column("Contracts", style="bold")
    table.add_column("Status", style="bold")

    strikes_desc = ", ".join([f"{leg.get('side')} {leg.get('strike')}{leg.get('type')}" for leg in candidate.get("legs", [])])
    table.add_row(
        str(candidate.get("symbol")),
        str(candidate.get("strategy_type")),
        f"{candidate.get('expiration')} ({candidate.get('dte')}d)",
        strikes_desc,
        f"${candidate.get('net_credit', 0):.2f}",
        f"${candidate.get('max_loss', 0):.2f}",
        str(contracts),
        f"[green]{status}[/green]" if status == "APPROVED" else f"[red]{status}[/red]"
    )
    console.print(table)
