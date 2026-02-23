from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from hisaab.config import ACCOUNTS, REWARDS_ACCOUNTS, LEDGER_DIR
from hisaab.formatters.beancount import format_transactions
from hisaab.parsers import PARSERS
from hisaab.rules import categorize
from hisaab.storage import write_transactions
from hisaab.transformer import transform

app = typer.Typer(help="Hisaab - Personal Finance Tracker")


def detect_bank(filename: str) -> Optional[str]:
    """Auto-detect bank from filename."""
    name_lower = filename.lower()
    for bank in PARSERS:
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

        if detected_bank not in PARSERS:
            typer.echo(f"Unknown bank: {detected_bank}")
            continue

        typer.echo(f"Importing {file.name} as {detected_bank}...")

        parser = PARSERS[detected_bank]
        df = parser.parse(str(file))

        if df.empty:
            typer.echo(f"  No transactions found in {file.name}")
            continue

        default_account = ACCOUNTS.get(detected_bank, f"Liabilities:CreditCard:{detected_bank.upper()}")
        rewards_account = REWARDS_ACCOUNTS.get(detected_bank)
        transactions = transform(df, default_account, rewards_account)
        categorize(transactions)

        if dry_run:
            typer.echo(format_transactions(transactions))
        else:
            output_file = write_transactions(transactions, LEDGER_DIR, detected_bank)
            typer.echo(f"  Imported {len(transactions)} transactions to {output_file}")


@app.command()
def uncategorized():
    """Show transactions that couldn't be categorized."""
    from hisaab.storage import read_ledger

    entries = read_ledger(LEDGER_DIR)
    txns = [e for e in entries if hasattr(e, "narration")]

    found = []
    for txn in txns:
        if any("Uncategorized" in p.account for p in txn.postings):
            found.append(txn)

    if not found:
        typer.echo("No uncategorized transactions.")
        return

    typer.echo(f"{len(found)} uncategorized transaction(s):\n")
    for txn in found:
        amounts = [abs(p.units.number) for p in txn.postings if p.units.currency == "INR"]
        amount = max(amounts) if amounts else 0
        typer.echo(f"  {txn.date}  {amount:>10.2f} INR  {txn.narration}")


@app.command()
def balance(
    account: Optional[str] = typer.Argument(None, help="Filter by account substring"),
):
    """Show account balances."""
    from collections import defaultdict
    from decimal import Decimal
    from hisaab.storage import read_ledger

    entries = read_ledger(LEDGER_DIR)
    txns = [e for e in entries if hasattr(e, "narration")]

    if not txns:
        typer.echo("No transactions found.")
        return

    balances = defaultdict(Decimal)
    for txn in txns:
        for p in txn.postings:
            if p.units.currency == "INR":
                balances[p.account] += p.units.number

    for acct in sorted(balances):
        if account and account not in acct:
            continue
        typer.echo(f"  {balances[acct]:>12.2f} INR  {acct}")


@app.command()
def show(
    account: Optional[str] = typer.Argument(None, help="Account to filter by (substring match)"),
    from_date: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
):
    """Show transactions, optionally filtered by account."""
    from hisaab.storage import read_ledger

    entries = read_ledger(LEDGER_DIR)
    txns = [e for e in entries if hasattr(e, "narration")]

    if account:
        txns = [t for t in txns if any(account in p.account for p in t.postings)]

    if from_date:
        start = datetime.strptime(from_date, "%Y-%m-%d").date()
        txns = [t for t in txns if t.date >= start]

    if to_date:
        end = datetime.strptime(to_date, "%Y-%m-%d").date()
        txns = [t for t in txns if t.date <= end]

    if tag:
        txns = [t for t in txns if tag in t.tags]

    if not txns:
        typer.echo("No transactions found.")
        return

    for txn in txns:
        amounts = [abs(p.units.number) for p in txn.postings if p.units.currency == "INR"]
        amount = max(amounts) if amounts else 0
        typer.echo(f"  {txn.date}  {amount:>10.2f} INR  {txn.narration}")


@app.command()
def export(
    format: str = typer.Option("beancount", "--format", "-f", help="Output format (beancount, ledger)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Export all transactions to Beancount or Ledger format."""
    from hisaab.storage import read_ledger, entries_to_transactions
    from hisaab.formatters import ledger as ledger_fmt

    entries = read_ledger(LEDGER_DIR)
    transactions = entries_to_transactions(entries)

    if not transactions:
        typer.echo("No transactions to export.")
        return

    if format == "ledger":
        text = ledger_fmt.format_transactions(transactions)
    else:
        text = format_transactions(transactions)

    if output:
        output.write_text(text)
        typer.echo(f"Exported {len(transactions)} transactions to {output}")
    else:
        typer.echo(text)


def main():
    app()


if __name__ == "__main__":
    main()
