from pathlib import Path

from hisaab.models import Transaction
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
    content = format_transactions(transactions)

    with open(bank_file, "a") as f:
        f.write("\n\n" + content)

    return bank_file
