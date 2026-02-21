# Hisaab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a personal finance tracker that parses bank statements, stores transactions in Beancount format, and provides CLI for querying.

**Architecture:** PDF/CSV parsers output standardized DataFrames. A single transformer converts to Transaction dataclasses. Rules engine auto-categorizes. Formatters output Beancount (canonical) or Ledger (on demand).

**Tech Stack:** Python 3.10+, pdfplumber, pandas, typer, beancount (for bean-query/bean-report)

---

## Task 1: Project Structure and Models

**Files:**
- Create: `hisaab/__init__.py`
- Create: `hisaab/models.py`
- Create: `tests/__init__.py`
- Create: `tests/test_models.py`

**Step 1: Create package structure**

```bash
mkdir -p hisaab/parsers hisaab/formatters tests
touch hisaab/__init__.py hisaab/parsers/__init__.py hisaab/formatters/__init__.py tests/__init__.py
```

**Step 2: Write the failing test for Posting**

Create `tests/test_models.py`:

```python
from decimal import Decimal
from hisaab.models import Posting


def test_posting_defaults():
    p = Posting(account="Expenses:Food", amount=Decimal("100"))
    assert p.account == "Expenses:Food"
    assert p.amount == Decimal("100")
    assert p.currency == "INR"
    assert p.tags == []
    assert p.meta == {}
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_models.py::test_posting_defaults -v`
Expected: FAIL with "cannot import name 'Posting'"

**Step 4: Write Posting dataclass**

Create `hisaab/models.py`:

```python
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class Posting:
    account: str
    amount: Decimal
    currency: str = "INR"
    tags: list[str] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_models.py::test_posting_defaults -v`
Expected: PASS

**Step 6: Write the failing test for Transaction**

Add to `tests/test_models.py`:

```python
from datetime import date
from hisaab.models import Transaction


def test_transaction_is_balanced():
    postings = [
        Posting(account="Expenses:Food", amount=Decimal("100")),
        Posting(account="Liabilities:CC", amount=Decimal("-100")),
    ]
    txn = Transaction(date=date(2026, 1, 15), description="Lunch", postings=postings)
    assert txn.is_balanced is True


def test_transaction_unbalanced():
    postings = [
        Posting(account="Expenses:Food", amount=Decimal("100")),
    ]
    txn = Transaction(date=date(2026, 1, 15), description="Lunch", postings=postings)
    assert txn.is_balanced is False
```

**Step 7: Run test to verify it fails**

Run: `pytest tests/test_models.py::test_transaction_is_balanced -v`
Expected: FAIL with "cannot import name 'Transaction'"

**Step 8: Write Transaction dataclass**

Add to `hisaab/models.py`:

```python
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

**Step 9: Run all model tests**

Run: `pytest tests/test_models.py -v`
Expected: All PASS

**Step 10: Commit**

```bash
git add hisaab/ tests/
git commit -m "feat: add Transaction and Posting dataclasses"
```

---

## Task 2: Configuration Module

**Files:**
- Create: `hisaab/config.py`
- Create: `tests/test_config.py`

**Step 1: Write the failing test**

Create `tests/test_config.py`:

```python
from hisaab.config import ACCOUNTS, REWARDS_ACCOUNTS, RULES, LEDGER_DIR


def test_accounts_defined():
    assert "icici_coral" in ACCOUNTS
    assert "hdfc_tataneu" in ACCOUNTS
    assert "axis" in ACCOUNTS


def test_rules_structure():
    assert len(RULES) > 0
    keyword, category, tags = RULES[0]
    assert isinstance(keyword, str)
    assert isinstance(category, str)
    assert isinstance(tags, list)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with "cannot import name 'ACCOUNTS'"

**Step 3: Write config module**

Create `hisaab/config.py`:

```python
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
    ("ola", "Expenses:Transport:Cab", ["transport"]),
    ("flipkart", "Expenses:Shopping", []),
]

LEDGER_DIR = Path("~/finance").expanduser()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add hisaab/config.py tests/test_config.py
git commit -m "feat: add suckless config module"
```

---

## Task 3: Beancount Formatter

**Files:**
- Create: `hisaab/formatters/beancount.py`
- Create: `tests/test_formatters.py`

**Step 1: Write the failing test**

Create `tests/test_formatters.py`:

```python
from datetime import date
from decimal import Decimal
from hisaab.models import Transaction, Posting
from hisaab.formatters.beancount import format_transaction


def test_format_simple_transaction():
    postings = [
        Posting(account="Expenses:Food", amount=Decimal("100")),
        Posting(account="Liabilities:CC", amount=Decimal("-100")),
    ]
    txn = Transaction(
        date=date(2026, 1, 15),
        description="Swiggy order",
        postings=postings,
    )
    result = format_transaction(txn)
    assert "2026-01-15" in result
    assert "Swiggy order" in result
    assert "Expenses:Food" in result
    assert "100.00 INR" in result


def test_format_transaction_with_tags():
    postings = [
        Posting(account="Expenses:Food", amount=Decimal("100")),
        Posting(account="Liabilities:CC", amount=Decimal("-100")),
    ]
    txn = Transaction(
        date=date(2026, 1, 15),
        description="Swiggy order",
        postings=postings,
        tags=["food", "delivery"],
    )
    result = format_transaction(txn)
    assert "#food" in result
    assert "#delivery" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_formatters.py::test_format_simple_transaction -v`
Expected: FAIL with "cannot import name 'format_transaction'"

**Step 3: Write beancount formatter**

Create `hisaab/formatters/beancount.py`:

```python
from hisaab.models import Transaction


def format_transaction(txn: Transaction) -> str:
    tags = " ".join(f"#{t}" for t in txn.tags) if txn.tags else ""
    payee = f'"{txn.payee}"' if txn.payee else '""'
    narration = f'"{txn.description}"'

    header = f'{txn.date} * {payee} {narration}'
    if tags:
        header = f'{header} {tags}'

    lines = [header]

    for key, val in txn.meta.items():
        lines.append(f'  {key}: "{val}"')

    for p in txn.postings:
        lines.append(f'  {p.account}  {p.amount:.2f} {p.currency}')

    return "\n".join(lines)


def format_transactions(transactions: list[Transaction]) -> str:
    return "\n\n".join(format_transaction(t) for t in transactions)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_formatters.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add hisaab/formatters/beancount.py tests/test_formatters.py
git commit -m "feat: add beancount formatter"
```

---

## Task 4: Ledger Formatter

**Files:**
- Create: `hisaab/formatters/ledger.py`
- Modify: `tests/test_formatters.py`

**Step 1: Write the failing test**

Add to `tests/test_formatters.py`:

```python
from hisaab.formatters.ledger import format_transaction as format_ledger


def test_ledger_format_simple():
    postings = [
        Posting(account="Expenses:Food", amount=Decimal("100")),
        Posting(account="Liabilities:CC", amount=Decimal("-100")),
    ]
    txn = Transaction(
        date=date(2026, 1, 15),
        description="Swiggy order",
        postings=postings,
    )
    result = format_ledger(txn)
    assert "2026/01/15" in result  # Ledger uses / not -
    assert "Swiggy order" in result
    assert "Expenses:Food" in result


def test_ledger_format_with_tags():
    postings = [
        Posting(account="Expenses:Food", amount=Decimal("100")),
        Posting(account="Liabilities:CC", amount=Decimal("-100")),
    ]
    txn = Transaction(
        date=date(2026, 1, 15),
        description="Swiggy order",
        postings=postings,
        tags=["food", "delivery"],
    )
    result = format_ledger(txn)
    assert ":food:" in result
    assert ":delivery:" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_formatters.py::test_ledger_format_simple -v`
Expected: FAIL with "cannot import name 'format_transaction'"

**Step 3: Write ledger formatter**

Create `hisaab/formatters/ledger.py`:

```python
from hisaab.models import Transaction


def format_transaction(txn: Transaction) -> str:
    payee = txn.payee or ""
    if payee:
        header = f'{txn.date.strftime("%Y/%m/%d")} {payee} - {txn.description}'
    else:
        header = f'{txn.date.strftime("%Y/%m/%d")} {txn.description}'

    lines = [header]

    if txn.tags:
        tags = ":".join(txn.tags)
        lines.append(f"    ; :{tags}:")

    for p in txn.postings:
        lines.append(f"    {p.account}    {p.amount:.2f} {p.currency}")

    return "\n".join(lines)


def format_transactions(transactions: list[Transaction]) -> str:
    return "\n\n".join(format_transaction(t) for t in transactions)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_formatters.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add hisaab/formatters/ledger.py tests/test_formatters.py
git commit -m "feat: add ledger formatter"
```

---

## Task 5: Transformer Module

**Files:**
- Create: `hisaab/transformer.py`
- Create: `tests/test_transformer.py`

**Step 1: Write the failing test for expense transformation**

Create `tests/test_transformer.py`:

```python
import pandas as pd
from decimal import Decimal
from hisaab.transformer import transform


def test_transform_expense():
    df = pd.DataFrame([
        {"Date": "15/01/2026", "Description": "Swiggy order", "Amount": -500.0},
    ])
    transactions = transform(df, default_account="Liabilities:CreditCard:ICICI")

    assert len(transactions) == 1
    txn = transactions[0]
    assert txn.description == "Swiggy order"
    assert len(txn.postings) == 2

    # Expense posting (positive)
    expense = next(p for p in txn.postings if "Expenses" in p.account)
    assert expense.amount == Decimal("500")

    # Liability posting (negative)
    liability = next(p for p in txn.postings if "Liabilities" in p.account)
    assert liability.amount == Decimal("-500")

    assert txn.is_balanced
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_transformer.py::test_transform_expense -v`
Expected: FAIL with "cannot import name 'transform'"

**Step 3: Write basic transformer**

Create `hisaab/transformer.py`:

```python
import pandas as pd
from datetime import datetime
from decimal import Decimal
from hisaab.models import Transaction, Posting


def parse_date(date_str: str):
    """Parse date from DD/MM/YYYY format."""
    return datetime.strptime(date_str, "%d/%m/%Y").date()


def transform(
    df: pd.DataFrame,
    default_account: str,
    rewards_account: str = None
) -> list[Transaction]:
    transactions = []

    for _, row in df.iterrows():
        amount = Decimal(str(row["Amount"]))
        reward_points = Decimal(str(row.get("RewardPoints", 0) or 0))

        postings = []

        if amount < 0:  # Expense
            postings.append(Posting(account="Expenses:Uncategorized", amount=-amount))
            postings.append(Posting(account=default_account, amount=amount))
        else:  # Income/Credit
            postings.append(Posting(account="Income:Uncategorized", amount=-amount))
            postings.append(Posting(account=default_account, amount=amount))

        # Reward points as part of same transaction
        if reward_points and rewards_account:
            postings.append(Posting(
                account=rewards_account,
                amount=reward_points,
                currency="PTS"
            ))
            postings.append(Posting(
                account="Income:RewardPoints",
                amount=-reward_points,
                currency="PTS"
            ))

        transactions.append(Transaction(
            date=parse_date(row["Date"]),
            description=row["Description"],
            postings=postings,
            tags=["imported"],
        ))

    return transactions
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_transformer.py::test_transform_expense -v`
Expected: PASS

**Step 5: Write test for income/credit transformation**

Add to `tests/test_transformer.py`:

```python
def test_transform_credit():
    df = pd.DataFrame([
        {"Date": "15/01/2026", "Description": "Refund", "Amount": 200.0},
    ])
    transactions = transform(df, default_account="Liabilities:CreditCard:ICICI")

    txn = transactions[0]
    assert len(txn.postings) == 2

    # Income posting (negative in double-entry)
    income = next(p for p in txn.postings if "Income" in p.account)
    assert income.amount == Decimal("-200")

    # Liability posting (positive - reduces liability)
    liability = next(p for p in txn.postings if "Liabilities" in p.account)
    assert liability.amount == Decimal("200")

    assert txn.is_balanced
```

**Step 6: Run test**

Run: `pytest tests/test_transformer.py::test_transform_credit -v`
Expected: PASS (already implemented)

**Step 7: Write test for reward points**

Add to `tests/test_transformer.py`:

```python
def test_transform_with_reward_points():
    df = pd.DataFrame([
        {"Date": "15/01/2026", "Description": "Shopping", "Amount": -1000.0, "RewardPoints": 10},
    ])
    transactions = transform(
        df,
        default_account="Liabilities:CreditCard:HDFC",
        rewards_account="Assets:RewardPoints:HDFC"
    )

    txn = transactions[0]
    assert len(txn.postings) == 4  # expense, liability, reward asset, reward income

    # Reward points postings
    reward_asset = next(p for p in txn.postings if "Assets:RewardPoints" in p.account)
    assert reward_asset.amount == Decimal("10")
    assert reward_asset.currency == "PTS"

    reward_income = next(p for p in txn.postings if p.account == "Income:RewardPoints")
    assert reward_income.amount == Decimal("-10")
    assert reward_income.currency == "PTS"

    assert txn.is_balanced
```

**Step 8: Run all transformer tests**

Run: `pytest tests/test_transformer.py -v`
Expected: All PASS

**Step 9: Commit**

```bash
git add hisaab/transformer.py tests/test_transformer.py
git commit -m "feat: add transformer for DataFrame to Transaction"
```

---

## Task 6: Rules Engine

**Files:**
- Create: `hisaab/rules.py`
- Create: `tests/test_rules.py`

**Step 1: Write the failing test**

Create `tests/test_rules.py`:

```python
from datetime import date
from decimal import Decimal
from hisaab.models import Transaction, Posting
from hisaab.rules import categorize


def test_categorize_swiggy():
    postings = [
        Posting(account="Expenses:Uncategorized", amount=Decimal("500")),
        Posting(account="Liabilities:CC", amount=Decimal("-500")),
    ]
    txn = Transaction(
        date=date(2026, 1, 15),
        description="SWIGGY ORDER 12345",
        postings=postings,
    )
    categorize([txn])

    expense = next(p for p in txn.postings if p.amount > 0)
    assert expense.account == "Expenses:Food:Delivery"
    assert "food" in txn.tags


def test_categorize_no_match():
    postings = [
        Posting(account="Expenses:Uncategorized", amount=Decimal("500")),
        Posting(account="Liabilities:CC", amount=Decimal("-500")),
    ]
    txn = Transaction(
        date=date(2026, 1, 15),
        description="Random merchant",
        postings=postings,
    )
    categorize([txn])

    expense = next(p for p in txn.postings if p.amount > 0)
    assert expense.account == "Expenses:Uncategorized"  # Unchanged
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_rules.py::test_categorize_swiggy -v`
Expected: FAIL with "cannot import name 'categorize'"

**Step 3: Write rules engine**

Create `hisaab/rules.py`:

```python
from hisaab.config import RULES
from hisaab.models import Transaction


def categorize(transactions: list[Transaction]) -> None:
    """Categorize transactions in-place based on rules."""
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

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_rules.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add hisaab/rules.py tests/test_rules.py
git commit -m "feat: add rules engine for auto-categorization"
```

---

## Task 7: Update Existing Parsers

**Files:**
- Modify: `icici.py` (move to `hisaab/parsers/icici.py`)
- Modify: `hdfc.py` (move to `hisaab/parsers/hdfc.py`)
- Modify: `axis.py` (move to `hisaab/parsers/axis.py`)

**Step 1: Copy and update ICICI parser**

Create `hisaab/parsers/icici.py` based on existing `icici.py`:

Key changes:
- Rename function to `parse`
- Return DataFrame with standardized columns: Date, Description, Amount, RewardPoints
- Remove `Type` column (derived from Amount sign)
- Ensure Amount is negative for expenses

```python
import pdfplumber
import pandas as pd
import re


def parse(pdf_path: str) -> pd.DataFrame:
    """Parse ICICI credit card statement PDF.

    Returns DataFrame with columns: Date, Description, Amount, RewardPoints
    Amount: negative for expenses, positive for credits
    """
    extracted_data = []
    date_pattern = re.compile(r'^(\d{2}/\d{2}/\d{4})')
    current_txn = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if not text:
                continue

            lines = text.split('\n')

            for line in lines:
                raw_line = line
                stripped_line = line.strip()

                if not stripped_line:
                    continue

                date_match = date_pattern.match(stripped_line)

                if date_match:
                    if current_txn:
                        extracted_data.append(current_txn)
                        current_txn = None

                    date = date_match.group(1)
                    rest = stripped_line[len(date):].strip()

                    # Amount extraction
                    amt_match = re.search(r'([\d,]+\.\d{2}(\s*(?:CR|Cr|Dr))?)$', rest)
                    amount = 0.0
                    is_credit = False

                    if amt_match:
                        amt_str_full = amt_match.group(1)
                        rest = rest[:amt_match.start()].strip()
                        is_credit = "cr" in amt_str_full.lower()
                        clean_amt = re.sub(r'[^\d\.]', '', amt_str_full)
                        amount = float(clean_amt)
                        if not is_credit:
                            amount = -amount  # Expenses are negative

                    # SerNo extraction
                    ser_match = re.match(r'^(\d+)', rest)
                    if ser_match:
                        rest = rest[len(ser_match.group(1)):].strip()

                    # Points & Intl extraction
                    tokens = rest.split()
                    points = 0
                    desc_words = tokens

                    if tokens:
                        last_token = tokens[-1]
                        second_last = tokens[-2] if len(tokens) > 1 else None

                        if re.match(r'[\d,]+\.\d{2}', last_token):
                            if second_last and re.match(r'^\d+$', second_last):
                                points = int(second_last)
                                desc_words = tokens[:-2]
                            else:
                                desc_words = tokens[:-1]
                        elif re.match(r'^\d+$', last_token):
                            points = int(last_token)
                            desc_words = tokens[:-1]

                    description = " ".join(desc_words)

                    current_txn = {
                        "Date": date,
                        "Description": description,
                        "Amount": amount,
                        "RewardPoints": points,
                    }

                else:
                    if current_txn:
                        if date_pattern.match(stripped_line):
                            continue

                        leading_spaces = len(raw_line) - len(raw_line.lstrip())
                        INDENT_THRESHOLD = 10

                        if leading_spaces < INDENT_THRESHOLD:
                            continue

                        if re.search(r'^\s*\d+%\s*$', raw_line):
                            continue

                        current_txn["Description"] += " " + stripped_line

    if current_txn:
        extracted_data.append(current_txn)

    df = pd.DataFrame(extracted_data)
    if not df.empty:
        df["Description"] = df["Description"].astype(str).str.replace(r'# I.*', '', regex=True).str.strip()
    return df
```

**Step 2: Write test for ICICI parser**

Create `tests/test_parsers.py`:

```python
import pandas as pd
from pathlib import Path


def test_icici_parser_returns_correct_columns():
    # This test requires a sample PDF - skip if not available
    from hisaab.parsers.icici import parse

    # Check function signature exists
    assert callable(parse)
```

**Step 3: Copy and update HDFC parser**

Create `hisaab/parsers/hdfc.py` with standardized output (rename NeuCoins to RewardPoints).

**Step 4: Copy and update Axis parser**

Create `hisaab/parsers/axis.py` with standardized output (add RewardPoints column with 0).

**Step 5: Commit**

```bash
git add hisaab/parsers/
git commit -m "feat: move and standardize parsers"
```

---

## Task 8: CLI - Import Command

**Files:**
- Create: `hisaab/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write the failing test**

Create `tests/test_cli.py`:

```python
from typer.testing import CliRunner
from hisaab.cli import app

runner = CliRunner()


def test_app_exists():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "import" in result.output.lower() or "Usage" in result.output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py::test_app_exists -v`
Expected: FAIL with "cannot import name 'app'"

**Step 3: Write basic CLI structure**

Create `hisaab/cli.py`:

```python
from pathlib import Path
from typing import Optional
import typer

app = typer.Typer(help="Hisaab - Personal finance tracker")


@app.command("import")
def import_(
    files: list[Path] = typer.Argument(..., help="PDF/CSV files to import"),
    bank: str = typer.Option(None, "--bank", "-b", help="Bank name (icici, hdfc, axis)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be imported"),
):
    """Import bank statement(s) into ledger."""
    from hisaab.config import ACCOUNTS, REWARDS_ACCOUNTS
    from hisaab.transformer import transform
    from hisaab.rules import categorize
    from hisaab.formatters.beancount import format_transactions

    for file in files:
        if not file.exists():
            typer.echo(f"File not found: {file}", err=True)
            raise typer.Exit(1)

        # Auto-detect bank from filename if not provided
        detected_bank = bank
        if not detected_bank:
            fname = file.name.lower()
            if "icici" in fname:
                detected_bank = "icici_coral"
            elif "hdfc" in fname:
                detected_bank = "hdfc_tataneu"
            elif "axis" in fname:
                detected_bank = "axis"
            else:
                typer.echo(f"Cannot detect bank for {file}. Use --bank option.", err=True)
                raise typer.Exit(1)

        # Import the appropriate parser
        if "icici" in detected_bank:
            from hisaab.parsers.icici import parse
        elif "hdfc" in detected_bank:
            from hisaab.parsers.hdfc import parse
        elif "axis" in detected_bank:
            from hisaab.parsers.axis import parse
        else:
            typer.echo(f"Unknown bank: {detected_bank}", err=True)
            raise typer.Exit(1)

        df = parse(str(file))
        if df.empty:
            typer.echo(f"No transactions found in {file}")
            continue

        default_account = ACCOUNTS.get(detected_bank, f"Liabilities:CreditCard:{detected_bank}")
        rewards_account = REWARDS_ACCOUNTS.get(detected_bank)

        transactions = transform(df, default_account, rewards_account)
        categorize(transactions)

        if dry_run:
            typer.echo(f"\n--- {file} ({len(transactions)} transactions) ---\n")
            typer.echo(format_transactions(transactions))
        else:
            # TODO: Write to beancount file
            typer.echo(f"Imported {len(transactions)} transactions from {file}")


@app.command()
def uncategorized():
    """List uncategorized transactions."""
    typer.echo("TODO: Implement uncategorized listing")


@app.command()
def balance(account: Optional[str] = typer.Argument(None, help="Account to show balance for")):
    """Show account balances (wraps bean-report)."""
    typer.echo("TODO: Implement balance (wrap bean-report)")


@app.command()
def show(
    from_date: Optional[str] = typer.Option(None, "--from", help="Start date"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End date"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
):
    """Show transactions (wraps bean-query)."""
    typer.echo("TODO: Implement show (wrap bean-query)")


@app.command()
def export(
    format: str = typer.Option("ledger", "--format", "-f", help="Output format (ledger)"),
):
    """Export to Ledger format."""
    typer.echo("TODO: Implement export to ledger")


def main():
    app()


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

**Step 5: Add pyproject.toml for CLI entry point**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "hisaab"
version = "0.1.0"
description = "Personal finance tracker with double-entry accounting"
requires-python = ">=3.10"
dependencies = [
    "pdfplumber>=0.10.0",
    "pandas>=2.0.0",
    "typer>=0.9.0",
]

[project.scripts]
hisaab = "hisaab.cli:main"

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
]
```

**Step 6: Commit**

```bash
git add hisaab/cli.py tests/test_cli.py pyproject.toml
git commit -m "feat: add CLI with import command"
```

---

## Task 9: Integration Test

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration test**

Create `tests/test_integration.py`:

```python
import pandas as pd
from decimal import Decimal
from hisaab.transformer import transform
from hisaab.rules import categorize
from hisaab.formatters.beancount import format_transactions


def test_full_pipeline():
    """Test the full pipeline: DataFrame -> Transform -> Categorize -> Format"""
    df = pd.DataFrame([
        {"Date": "15/01/2026", "Description": "SWIGGY ORDER", "Amount": -540.0, "RewardPoints": 5},
        {"Date": "16/01/2026", "Description": "AMAZON PURCHASE", "Amount": -1200.0, "RewardPoints": 0},
        {"Date": "17/01/2026", "Description": "REFUND FROM MERCHANT", "Amount": 200.0, "RewardPoints": 0},
    ])

    transactions = transform(
        df,
        default_account="Liabilities:CreditCard:HDFC:TataNeu",
        rewards_account="Assets:RewardPoints:HDFC:NeuCoins"
    )

    assert len(transactions) == 3

    categorize(transactions)

    # Check Swiggy was categorized
    swiggy_txn = transactions[0]
    expense_posting = next(p for p in swiggy_txn.postings if p.amount > 0 and p.currency == "INR")
    assert expense_posting.account == "Expenses:Food:Delivery"
    assert "food" in swiggy_txn.tags

    # Check Amazon was categorized
    amazon_txn = transactions[1]
    expense_posting = next(p for p in amazon_txn.postings if p.amount > 0)
    assert expense_posting.account == "Expenses:Shopping"

    # Check refund remains uncategorized (income)
    refund_txn = transactions[2]
    income_posting = next(p for p in refund_txn.postings if "Income" in p.account and "RewardPoints" not in p.account)
    assert income_posting.account == "Income:Uncategorized"

    # All transactions should be balanced
    for txn in transactions:
        assert txn.is_balanced

    # Format and verify output
    output = format_transactions(transactions)
    assert "2026-01-15" in output
    assert "Expenses:Food:Delivery" in output
    assert "#food" in output
```

**Step 2: Run integration test**

Run: `pytest tests/test_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test for full pipeline"
```

---

## Task 10: File Writing and Main Beancount Structure

**Files:**
- Modify: `hisaab/cli.py`
- Create: `hisaab/storage.py`

**Step 1: Write storage module test**

Add to `tests/test_integration.py`:

```python
from pathlib import Path
from hisaab.storage import write_transactions, ensure_ledger_structure


def test_ensure_ledger_structure(tmp_path):
    """Test that ledger directory structure is created."""
    ensure_ledger_structure(tmp_path)

    assert (tmp_path / "main.beancount").exists()
    assert (tmp_path / "accounts.beancount").exists()
```

**Step 2: Write storage module**

Create `hisaab/storage.py`:

```python
from pathlib import Path
from hisaab.models import Transaction
from hisaab.formatters.beancount import format_transactions


def ensure_ledger_structure(ledger_dir: Path) -> None:
    """Ensure the ledger directory has the basic structure."""
    ledger_dir.mkdir(parents=True, exist_ok=True)

    main_file = ledger_dir / "main.beancount"
    if not main_file.exists():
        main_file.write_text(
            '; Hisaab - Personal Finance Ledger\n'
            '; Generated by hisaab\n\n'
            'include "accounts.beancount"\n'
            'include "icici.beancount"\n'
            'include "hdfc.beancount"\n'
            'include "axis.beancount"\n'
        )

    accounts_file = ledger_dir / "accounts.beancount"
    if not accounts_file.exists():
        accounts_file.write_text(
            '; Chart of Accounts\n\n'
            '1970-01-01 open Assets:RewardPoints:ICICI\n'
            '1970-01-01 open Assets:RewardPoints:HDFC:NeuCoins\n'
            '1970-01-01 open Liabilities:CreditCard:ICICI:Coral\n'
            '1970-01-01 open Liabilities:CreditCard:HDFC:TataNeu\n'
            '1970-01-01 open Liabilities:CreditCard:Axis:MyZone\n'
            '1970-01-01 open Expenses:Uncategorized\n'
            '1970-01-01 open Expenses:Food:Delivery\n'
            '1970-01-01 open Expenses:Shopping\n'
            '1970-01-01 open Expenses:Transport:Cab\n'
            '1970-01-01 open Income:Uncategorized\n'
            '1970-01-01 open Income:RewardPoints\n'
        )


def write_transactions(
    transactions: list[Transaction],
    ledger_dir: Path,
    bank: str
) -> Path:
    """Append transactions to the bank-specific beancount file."""
    ensure_ledger_structure(ledger_dir)

    bank_file = ledger_dir / f"{bank}.beancount"
    content = format_transactions(transactions)

    with open(bank_file, "a") as f:
        f.write("\n\n")
        f.write(content)

    return bank_file
```

**Step 3: Run test**

Run: `pytest tests/test_integration.py::test_ensure_ledger_structure -v`
Expected: PASS

**Step 4: Update CLI to write files**

Modify `hisaab/cli.py` import command to use storage module when not in dry-run mode.

**Step 5: Commit**

```bash
git add hisaab/storage.py hisaab/cli.py tests/test_integration.py
git commit -m "feat: add storage module for writing beancount files"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Models (Transaction, Posting) | `hisaab/models.py` |
| 2 | Config (suckless) | `hisaab/config.py` |
| 3 | Beancount formatter | `hisaab/formatters/beancount.py` |
| 4 | Ledger formatter | `hisaab/formatters/ledger.py` |
| 5 | Transformer | `hisaab/transformer.py` |
| 6 | Rules engine | `hisaab/rules.py` |
| 7 | Standardize parsers | `hisaab/parsers/*.py` |
| 8 | CLI with import | `hisaab/cli.py` |
| 9 | Integration test | `tests/test_integration.py` |
| 10 | File storage | `hisaab/storage.py` |

**Post-implementation:**
- Add more rules to `config.py` as you categorize transactions
- Implement remaining CLI commands (show, balance, export) when needed
