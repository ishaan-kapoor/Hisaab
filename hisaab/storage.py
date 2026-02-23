from decimal import Decimal
from pathlib import Path

from beancount import loader

from hisaab.models import Posting, Transaction
from hisaab.formatters.beancount import format_transactions


def ensure_ledger_structure(ledger_dir: Path) -> None:
    """Ensure the ledger directory structure exists with required files."""
    ledger_dir.mkdir(parents=True, exist_ok=True)

    main_file = ledger_dir / "main.beancount"
    if not main_file.exists():
        main_file.write_text(
            "; Hisaab - Personal Finance Ledger\n"
            'include "accounts.beancount"\n'
            'include "icici.beancount"\n'
            'include "hdfc.beancount"\n'
            'include "axis.beancount"\n'
        )

    accounts_file = ledger_dir / "accounts.beancount"
    if not accounts_file.exists():
        accounts_file.write_text(
            "; Chart of Accounts\n\n"
            "1970-01-01 open Assets:RewardPoints:ICICI\n"
            "1970-01-01 open Assets:RewardPoints:HDFC:NeuCoins\n"
            "1970-01-01 open Liabilities:CreditCard:ICICI:Coral\n"
            "1970-01-01 open Liabilities:CreditCard:HDFC:TataNeu\n"
            "1970-01-01 open Liabilities:CreditCard:Axis:MyZone\n"
            "1970-01-01 open Expenses:Uncategorized\n"
            "1970-01-01 open Expenses:Food:Delivery\n"
            "1970-01-01 open Expenses:Shopping\n"
            "1970-01-01 open Expenses:Transport:Cab\n"
            "1970-01-01 open Income:Uncategorized\n"
            "1970-01-01 open Income:RewardPoints\n"
        )


def _update_open_directives(ledger_dir: Path, transactions: list[Transaction]) -> None:
    """Add open directives for any new accounts found in transactions."""
    accounts_file = ledger_dir / "accounts.beancount"
    existing = accounts_file.read_text() if accounts_file.exists() else ""

    new_accounts = set()
    for txn in transactions:
        for p in txn.postings:
            if p.account not in existing:
                new_accounts.add(p.account)

    if not new_accounts:
        return

    lines = []
    for acct in sorted(new_accounts):
        lines.append(f"1970-01-01 open {acct}")

    with open(accounts_file, "a") as f:
        f.write("\n" + "\n".join(lines) + "\n")


def write_transactions(
    transactions: list[Transaction], ledger_dir: Path, bank: str
) -> Path:
    """Write transactions to a beancount file.

    Args:
        transactions: List of Transaction objects to write
        ledger_dir: Directory containing ledger files
        bank: Bank identifier (used for filename)

    Returns:
        Path to the written file
    """
    ensure_ledger_structure(ledger_dir)
    bank_file = ledger_dir / f"{bank}.beancount"

    existing_content = bank_file.read_text() if bank_file.exists() else ""

    new_transactions = []
    for txn in transactions:
        header = f'{txn.date} * "" "{txn.description}"'
        if txn.payee:
            header = f'{txn.date} * "{txn.payee}" "{txn.description}"'
        if header not in existing_content:
            new_transactions.append(txn)

    if not new_transactions:
        return bank_file

    content = format_transactions(new_transactions)

    with open(bank_file, "a") as f:
        f.write("\n\n" + content)

    _update_open_directives(ledger_dir, new_transactions)

    return bank_file


def read_ledger(ledger_dir: Path) -> list:
    """Read all entries from the ledger directory via beancount loader."""
    main_file = ledger_dir / "main.beancount"
    if not main_file.exists():
        return []

    entries, errors, _ = loader.load_file(str(main_file))
    return entries


def entries_to_transactions(entries: list) -> list[Transaction]:
    """Convert beancount entries back to Transaction objects for re-formatting."""
    transactions = []
    for e in entries:
        if not hasattr(e, "narration"):
            continue
        postings = []
        for p in e.postings:
            postings.append(Posting(
                account=p.account,
                amount=Decimal(str(p.units.number)),
                currency=p.units.currency,
            ))
        txn = Transaction(
            date=e.date,
            description=e.narration,
            payee=e.payee if e.payee else None,
            postings=postings,
            tags=list(e.tags) if e.tags else [],
        )
        transactions.append(txn)
    return transactions
