from pathlib import Path
from typing import Optional

import typer

from hisaab.config import ACCOUNTS
from hisaab.formatters.beancount import format_transactions
from hisaab.parsers import icici, hdfc, axis
from hisaab.rules import categorize
from hisaab.transformer import transform

app = typer.Typer(help="Hisaab - Personal Finance Tracker")

BANK_PARSERS = {
    "icici": icici.parse,
    "hdfc": hdfc.parse,
    "axis": axis.parse,
}


def detect_bank(filename: str) -> Optional[str]:
    """Auto-detect bank from filename."""
    name_lower = filename.lower()
    for bank in BANK_PARSERS:
        if bank in name_lower:
            return bank
    return None


@app.command("import")
def import_cmd(
    files: list[Path] = typer.Argument(..., help="PDF files to import"),
    bank: Optional[str] = typer.Option(None, "--bank", "-b", help="Bank name (icici, hdfc, axis)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be imported without saving"),
):
    """Import credit card statements from PDF files."""
    for file in files:
        detected_bank = bank or detect_bank(file.name)
        if not detected_bank:
            typer.echo(f"Could not detect bank for {file.name}. Use --bank option.")
            continue

        if detected_bank not in BANK_PARSERS:
            typer.echo(f"Unknown bank: {detected_bank}")
            continue

        typer.echo(f"Importing {file.name} as {detected_bank}...")

        parser = BANK_PARSERS[detected_bank]
        df = parser(str(file))

        if df.empty:
            typer.echo(f"  No transactions found in {file.name}")
            continue

        default_account = ACCOUNTS.get(detected_bank, f"Liabilities:CreditCard:{detected_bank.upper()}")
        transactions = transform(df, default_account)
        categorize(transactions)

        if dry_run:
            typer.echo(format_transactions(transactions))
        else:
            typer.echo(f"  Imported {len(transactions)} transactions")


@app.command()
def uncategorized():
    """Show transactions that couldn't be categorized."""
    typer.echo("Uncategorized transactions: (not implemented)")


@app.command()
def balance():
    """Show account balances."""
    typer.echo("Account balances: (not implemented)")


@app.command()
def show(
    account: Optional[str] = typer.Argument(None, help="Account to show"),
):
    """Show transactions for an account."""
    typer.echo(f"Transactions for {account or 'all accounts'}: (not implemented)")


@app.command()
def export(
    format: str = typer.Option("beancount", "--format", "-f", help="Output format (beancount, ledger)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Export transactions to Beancount or Ledger format."""
    typer.echo(f"Exporting to {format}: (not implemented)")


def main():
    app()


if __name__ == "__main__":
    main()
