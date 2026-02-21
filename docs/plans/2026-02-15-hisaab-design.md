# Hisaab - Personal Finance Tracker Design

**Date:** 2026-02-15
**Status:** Approved

## Overview

Personal expense tracking app with double-entry accounting for correctness. Local-first, git-trackable, CLI-driven. Personal use only.

## Architecture

```
PDF/CSV  Parser  DataFrame  Transformer  Transaction  Rules  Formatter  .beancount
                  (standardized)  (+ rewards)                                   .ledger
```

**Directory structure:**
```
hisaab/
  config.py              # Accounts, rules, paths (suckless - edit directly)
  models.py              # Transaction, Posting dataclasses
  transformer.py         # DataFrame  Transaction (handles reward points)
  rules.py               # Auto-categorize (~20 lines)
  cli.py                 # Typer CLI

  parsers/
    icici.py             # PDF  DataFrame
    hdfc.py
    axis.py

  formatters/
    beancount.py         # Transaction  .beancount text
    ledger.py            # Transaction  .ledger text
```

## Core Data Model

```python
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

@dataclass
class Posting:
    account: str                          # "Expenses:Food:Delivery"
    amount: Decimal
    currency: str = "INR"
    tags: list[str] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)

@dataclass
class Transaction:
    date: date
    description: str
    postings: list[Posting]
    payee: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)
    source_file: Optional[str] = None
    ref_no: Optional[str] = None

    @property
    def is_balanced(self) -> bool:
        return sum(p.amount for p in self.postings) == Decimal("0")
```

## Parser Output Schema

All parsers output identical DataFrame columns:
```
Date, Description, Amount, RewardPoints (optional)
```

- `Amount`: Negative = expense, Positive = income (parsers handle sign conversion)
- `RewardPoints`: Optional, numeric. If present and non-zero, transformer adds reward postings.

## Transformer

Single transformer handles all banks. Reward points become postings within same transaction:

```python
def transform(df, default_account: str, rewards_account: str = None) -> list[Transaction]:
    for _, row in df.iterrows():
        amount = Decimal(str(row["Amount"]))
        reward_points = Decimal(str(row.get("RewardPoints", 0) or 0))

        postings = []

        if amount < 0:  # Expense
            postings.append(Posting(account="Expenses:Uncategorized", amount=-amount))
            postings.append(Posting(account=default_account, amount=amount))
        else:  # Income
            postings.append(Posting(account="Income:Uncategorized", amount=-amount))
            postings.append(Posting(account=default_account, amount=amount))

        # Reward points as part of same transaction
        if reward_points and rewards_account:
            postings.append(Posting(account=rewards_account, amount=reward_points, currency="PTS"))
            postings.append(Posting(account="Income:RewardPoints", amount=-reward_points, currency="PTS"))

        transactions.append(Transaction(
            date=parse_date(row["Date"]),
            description=row["Description"],
            postings=postings,
            tags=["imported"],
        ))

    return transactions
```

## Rules Engine (Suckless Style)

No YAML. Config in Python, edit directly:

```python
# config.py
from pathlib import Path

ACCOUNTS = {
    "icici_coral": "Liabilities:CreditCard:ICICI:Coral",
    "hdfc_tataneu": "Liabilities:CreditCard:HDFC:TataNeu",
    "axis": "Liabilities:CreditCard:Axis:MyZone",
}

REWARDS_ACCOUNTS = {
    "icici_coral": "Assets:RewardPoints:ICICI",
    "hdfc_tataneu": "Assets:RewardPoints:HDFC:NeuCoins",
}

# Rules: (keyword, category, tags)
RULES = [
    ("swiggy", "Expenses:Food:Delivery", ["food"]),
    ("zomato", "Expenses:Food:Delivery", ["food"]),
    ("amazon", "Expenses:Shopping", []),
    ("uber", "Expenses:Transport:Cab", ["transport"]),
]

LEDGER_DIR = Path("~/finance")
```

```python
# rules.py (~20 lines)
from config import RULES

def categorize(transactions: list[Transaction]) -> None:
    for txn in transactions:
        text = f"{txn.payee or ''} {txn.description}".lower()

        for keyword, category, tags in RULES:
            if keyword in text:
                for posting in txn.postings:
                    if "Uncategorized" in posting.account:
                        posting.account = category
                txn.tags.extend(tags)
                break
```

## Formatters

**beancount.py (~30 lines):**
```python
def format_transaction(txn: Transaction) -> str:
    tags = " ".join(f"#{t}" for t in txn.tags) if txn.tags else ""
    payee = f'"{txn.payee}"' if txn.payee else '""'
    narration = f'"{txn.description}"'

    header = f'{txn.date} * {payee} {narration} {tags}'.strip()
    lines = [header]

    for key, val in txn.meta.items():
        lines.append(f'  {key}: "{val}"')

    for p in txn.postings:
        if p.amount is not None:
            lines.append(f'  {p.account}  {p.amount:.2f} {p.currency}')
        else:
            lines.append(f'  {p.account}')

    return "\n".join(lines)
```

**ledger.py (~30 lines):**
```python
def format_transaction(txn: Transaction) -> str:
    tags = " :".join(txn.tags)
    tag_comment = f"    ; :{tags}:" if tags else ""

    payee = txn.payee or ""
    header = f'{txn.date.strftime("%Y/%m/%d")} {payee} - {txn.description}'.strip(" -")

    lines = [header]
    if tag_comment:
        lines.append(tag_comment)

    for p in txn.postings:
        if p.amount is not None:
            lines.append(f'    {p.account}    {p.amount:.2f} {p.currency}')
        else:
            lines.append(f'    {p.account}')

    return "\n".join(lines)
```

## CLI

```python
# cli.py - Typer-based
import typer
app = typer.Typer()

@app.command()
def import_(files: list[Path], bank: str = None, dry_run: bool = False):
    """Import statement(s) into ledger."""
    ...

@app.command()
def show(from_date: str = None, to_date: str = None, tag: str = None):
    """Show transactions (wraps bean-query)."""
    ...

@app.command()
def balance(account: str = None):
    """Show balances (wraps bean-report)."""
    ...

@app.command()
def uncategorized():
    """List uncategorized transactions."""
    ...

@app.command()
def export(format: str = "ledger"):
    """Export to Ledger format."""
    ...
```

**Usage:**
```bash
hisaab import statement.pdf --bank icici
hisaab import *.pdf --dry-run
hisaab show --from 2026-01-01 --tag food
hisaab balance Expenses
hisaab uncategorized
hisaab export --ledger
```

## File Organization

- Beancount canonical, Ledger generated on demand
- Per-account files: `icici.beancount`, `hdfc.beancount`, `axis.beancount`
- Shared `accounts.beancount` for chart of accounts
- `main.beancount` includes all files

```
~/finance/
  main.beancount         # includes all
  accounts.beancount     # chart of accounts
  icici.beancount        # ICICI transactions
  hdfc.beancount         # HDFC transactions
  axis.beancount         # Axis transactions
```

## Double-Entry Sign Convention

| Account Type | Increase | Decrease |
|--------------|----------|----------|
| Assets       | +        | -        |
| Expenses     | +        | -        |
| Liabilities  | -        | +        |
| Income       | -        | +        |

Example - purchase with reward points:
```python
postings = [
    Posting(account="Expenses:Food", amount=Decimal("540")),
    Posting(account="Liabilities:CreditCard:HDFC", amount=Decimal("-540")),
    Posting(account="Assets:RewardPoints:HDFC", amount=Decimal("5")),
    Posting(account="Income:RewardPoints", amount=Decimal("-5")),
]
# Sum: 540 - 540 + 5 - 5 = 0 (balanced)
```

## Categorization Workflow

1. **Auto-categorization** - Rules applied during import
2. **Batch review** - `hisaab uncategorized` dumps list, edit beancount file directly
3. **Editor-native** - Open `.beancount` in vim/VSCode, change `Expenses:Uncategorized` to correct category

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage | Beancount (text) | Git-trackable, single source of truth |
| Ledger support | Generated on demand | Avoid sync complexity |
| Config | Python (suckless) | No YAML parsing, edit source directly |
| Transformers | Single module | Parsers output identical schema |
| Reward points | Same transaction | Cleaner than linking separate transactions |
| CLI | Thin wrapper | Delegate to bean-query/bean-report |

## Existing Assets

Working parsers in `/codemill/kapooris-r/Calc/`:
- `icici.py` - PDF parser with smart indent detection
- `hdfc.py` - PDF parser for HDFC Tata Neu (grid tables, NeuCoins)
- `axis.py` - PDF parser for Axis

Need modification to output standardized DataFrame: Date, Description, Amount, RewardPoints

## Estimated Size

~400 lines total (excluding existing parsers):
- models.py: ~40 lines
- transformer.py: ~50 lines
- config.py: ~30 lines
- rules.py: ~20 lines
- formatters/beancount.py: ~30 lines
- formatters/ledger.py: ~30 lines
- cli.py: ~100 lines
- parsers (modifications): ~50 lines each
