from decimal import Decimal
from pathlib import Path

from beancount import loader
from beancount.parser import parser

from hisaab.models import Posting, Transaction
from hisaab.formatters.beancount import format_transactions


def _normalize_desc(s: str) -> str:
    return " ".join(s.lower().split())


def _txn_signature(txn: Transaction) -> tuple:
    """Stable identity for dedup.

    Uses (date, ref_no) when ref_no is present (banks assign unique refs).
    Falls back to (date, primary_amount, normalized_description) otherwise.
    The primary amount is the liability/asset posting (not Expense/Income),
    so manually-edited categorization does not break the signature.
    """
    if txn.ref_no:
        return ("ref", txn.date, txn.ref_no)

    primary = next(
        (
            p for p in txn.postings
            if not (p.account.startswith("Expenses:") or p.account.startswith("Income:"))
        ),
        txn.postings[0] if txn.postings else None,
    )
    amount = primary.amount if primary else Decimal("0")
    return ("desc", txn.date, amount, _normalize_desc(txn.description))


def _entry_signature(entry) -> tuple:
    """Compute signature for a parsed beancount entry (read path)."""
    ref = entry.meta.get("ref") if entry.meta else None
    if ref:
        return ("ref", entry.date, str(ref))

    primary = next(
        (
            p for p in entry.postings
            if not (p.account.startswith("Expenses:") or p.account.startswith("Income:"))
        ),
        entry.postings[0] if entry.postings else None,
    )
    amount = Decimal(str(primary.units.number)) if primary else Decimal("0")
    return ("desc", entry.date, amount, _normalize_desc(entry.narration))


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
            'include "icici-xls.beancount"\n'
            'include "hdfc-xls.beancount"\n'
            'include "axis-xls.beancount"\n'
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
    """Write transactions to a beancount file with count-based dedup.

    Two signature schemes:
      - ("ref", date, ref_no) when the parser populated ref_no. Refs are
        unique per bank, so set-semantics (skip on first match) is correct.
      - ("desc", date, primary_amount, normalized_description) otherwise.
        Genuine duplicates are common (two same-day Uber rides, multiple
        identical metro recharges), so we use count-semantics: only skip
        an input transaction if the file already has at least one
        unmatched copy of the same signature.

    The signature is computed from the liability/asset posting amount, so
    manual recategorization, payee additions, and whitespace edits to the
    description never break dedup on re-import.

    Args:
        transactions: List of Transaction objects to write
        ledger_dir: Directory containing ledger files
        bank: Bank identifier (used for filename)

    Returns:
        Path to the written file
    """
    from collections import Counter

    ensure_ledger_structure(ledger_dir)
    bank_file = ledger_dir / f"{bank}.beancount"

    existing_counts: Counter = Counter()
    if bank_file.exists():
        entries, _, _ = parser.parse_file(str(bank_file))
        for e in entries:
            if hasattr(e, "narration"):
                existing_counts[_entry_signature(e)] += 1

    matched: Counter = Counter()
    new_transactions = []
    for txn in transactions:
        sig = _txn_signature(txn)
        if matched[sig] < existing_counts[sig]:
            matched[sig] += 1
            continue
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
        ref_no = None
        if e.meta:
            ref = e.meta.get("ref")
            if ref:
                ref_no = str(ref)
        txn = Transaction(
            date=e.date,
            description=e.narration,
            payee=e.payee if e.payee else None,
            postings=postings,
            tags=list(e.tags) if e.tags else [],
            ref_no=ref_no,
        )
        transactions.append(txn)
    return transactions
