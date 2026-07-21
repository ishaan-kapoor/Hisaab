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
    """Auto-detect bank from filename and extension."""
    name_lower = filename.lower()
    ext = Path(filename).suffix.lower()
    is_xls = ext in ('.xls', '.xlsx')
    is_pdf = ext == '.pdf'
    extra_mapping = { "emralde": 'icici', "coral": 'icici' }
    banks = ('icici', 'hdfc', 'axis')
    for bank in banks:
        if bank in name_lower:
            return f"{bank}-cc" if is_pdf else bank
    for key_word, bank in extra_mapping.items():
        if key_word in name_lower:
            return f"{bank}-cc" if is_pdf else bank
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


@app.command()
def merchants():
    """List uncategorized merchants by frequency and total spend."""
    from hisaab.categorizer import group_uncategorized
    from hisaab.storage import entries_to_transactions, read_ledger

    transactions = entries_to_transactions(read_ledger(LEDGER_DIR))
    buckets = group_uncategorized(transactions)

    if not buckets:
        typer.echo("No uncategorized transactions.")
        return

    typer.echo(f"{len(buckets)} uncategorized merchant(s):\n")
    typer.echo(f"{'#':>3}  {'count':>5}  {'total INR':>12}  fingerprint")
    typer.echo("-" * 60)
    for i, b in enumerate(buckets, 1):
        typer.echo(f"{i:>3}  {b.count:>5}  {b.total_abs:>12,.2f}  {b.fingerprint}")


@app.command()
def learn():
    """Walk uncategorized merchants and append rules to config.py."""
    import hisaab.config as cfg
    from hisaab.categorizer import (
        append_rule, existing_categories, existing_tags, first_alpha_token,
        fzf_pick, group_uncategorized, input_with_prefill, reload_rules,
    )
    from hisaab.storage import entries_to_transactions, read_ledger

    transactions = entries_to_transactions(read_ledger(LEDGER_DIR))
    buckets = group_uncategorized(transactions)

    if not buckets:
        typer.echo("No uncategorized transactions to learn from.")
        return

    config_path = Path(cfg.__file__)
    rules = list(cfg.RULES)
    added = 0
    skipped = 0

    typer.echo(f"{len(buckets)} merchant(s) to categorize. [s]kip / [q]uit\n")

    for i, b in enumerate(buckets, 1):
        typer.echo(f"[{i}/{len(buckets)}] {b.fingerprint}  --  {b.count} txns, INR {b.total_abs:,.2f}")
        typer.echo("  samples:")
        for s in b.samples:
            typer.echo(f"    {s}")

        prefill = first_alpha_token(b.most_common_description)
        try:
            pattern = input_with_prefill("  pattern  > ", prefill)
        except (EOFError, KeyboardInterrupt):
            typer.echo("\n")
            break
        if pattern.lower() == "q":
            break
        if pattern.lower() == "s" or not pattern:
            skipped += 1
            typer.echo("  skipped\n")
            continue

        category_pick = fzf_pick(existing_categories(rules, LEDGER_DIR), "category")
        if not category_pick:
            skipped += 1
            typer.echo("  skipped (no category)\n")
            continue
        category = category_pick[0]

        tag_pick = fzf_pick(existing_tags(rules), "tags", multi=True)
        tags = tag_pick

        append_rule(config_path, pattern, category, tags)
        rules = reload_rules(config_path)
        added += 1
        typer.echo(f"  -> ({pattern!r}, {category!r}, {tags!r})\n")

    typer.echo(f"Done. Added {added} rule(s), skipped {skipped}.")
    if added:
        typer.echo("Run 'hisaab recategorize' to apply to existing transactions.")


@app.command()
def recategorize(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show changes without writing"),
):
    """Re-run RULES against existing Uncategorized entries in the ledger."""
    import importlib
    from copy import deepcopy

    import hisaab.config as cfg_module
    from hisaab.categorizer import (
        is_uncategorized, recategorize_entry_in_file,
    )
    from hisaab.rules import categorize
    from hisaab.storage import entries_to_transactions, read_ledger

    importlib.reload(cfg_module)
    entries = read_ledger(LEDGER_DIR)
    txns = entries_to_transactions(entries)

    uncats_with_entry = [
        (e, t) for e, t in zip(
            (e for e in entries if hasattr(e, "narration")), txns
        )
        if is_uncategorized(t)
    ]

    if not uncats_with_entry:
        typer.echo("Nothing uncategorized.")
        return

    after = [deepcopy(t) for _, t in uncats_with_entry]
    categorize(after)

    changes = []
    for (entry, before), updated in zip(uncats_with_entry, after):
        account_changes = {}
        for b_post, a_post in zip(before.postings, updated.postings):
            if b_post.account != a_post.account:
                account_changes[b_post.account] = a_post.account
        added_tags = [t for t in updated.tags if t not in before.tags]
        if account_changes or added_tags:
            changes.append((entry, account_changes, added_tags))

    if not changes:
        typer.echo("No matching rules. Add rules with 'hisaab learn' first.")
        return

    typer.echo(f"{len(changes)} entr(ies) would be updated:\n")
    for entry, acct_changes, tags in changes:
        loc = f"{entry.meta.get('filename')}:{entry.meta.get('lineno')}"
        typer.echo(f"  {entry.date}  {entry.narration}")
        typer.echo(f"    {loc}")
        for old, new in acct_changes.items():
            typer.echo(f"    {old}  ->  {new}")
        if tags:
            typer.echo(f"    +tags: {', '.join('#' + t for t in tags)}")

    if dry_run:
        typer.echo("\n(dry-run; no files written)")
        return

    written_files = set()
    for entry, acct_changes, tags in changes:
        path = Path(entry.meta["filename"])
        lineno = entry.meta["lineno"]
        if recategorize_entry_in_file(path, lineno, acct_changes, tags):
            written_files.add(path)

    typer.echo(f"\nWrote {len(written_files)} file(s).")


@app.command()
def fava(
    port: int = typer.Option(5000, "--port", "-p", help="Port to bind"),
    host: str = typer.Option("localhost", "--host", "-h", help="Host to bind"),
):
    """Launch Fava web UI on the ledger."""
    import subprocess

    main_file = LEDGER_DIR / "main.beancount"
    if not main_file.exists():
        typer.echo(f"No ledger found at {main_file}. Import a statement first.")
        raise typer.Exit(1)

    subprocess.run(["fava", "--port", str(port), "--host", host, str(main_file)])


def main():
    app()


if __name__ == "__main__":
    main()
