# Design

## Overview

Personal expense tracking app with double-entry accounting for correctness. Local-first, git-trackable, CLI-driven.

## Architecture

```
PDF/CSV -> Parser -> DataFrame -> Transformer -> Transaction -> Rules -> Formatter -> .beancount
                    (standardized)  (+ rewards)                                     -> .ledger
```

## Package Structure

```
hisaab/
  config.py              # Accounts, rules, paths (suckless - edit directly)
  models.py              # Transaction, Posting dataclasses
  transformer.py         # DataFrame -> Transaction (handles reward points)
  rules.py               # Auto-categorize based on keyword matching
  cli.py                 # Typer CLI
  storage.py             # Read/write beancount files, deduplication

  parsers/
    base.py              # StatementParser ABC
    icici.py             # ICICI credit card PDF parser
    hdfc.py              # HDFC Tata Neu credit card PDF parser
    axis.py              # Axis credit card PDF parser

  formatters/
    beancount.py         # Transaction -> .beancount text
    ledger.py            # Transaction -> .ledger text
```

## Data Model

Two dataclasses in `models.py`:

- **Posting**: account, amount, currency (default INR), tags, meta
- **Transaction**: date, description, postings, payee, tags, meta, source_file, ref_no
  - `is_balanced` property: sum of all posting amounts equals zero

## Parser Schema

All parsers inherit `StatementParser` ABC and output a standardized DataFrame:

```
Date, Description, Amount, RewardPoints, RefNo
```

- `Date`: str in DD/MM/YYYY format
- `Description`: str
- `Amount`: float, negative = expense, positive = income/credit
- `RewardPoints`: numeric, 0 if not applicable (filled by `validate()`)
- `RefNo`: str or None (filled by `validate()`)

## Double-Entry Sign Convention

| Account Type | Increase | Decrease |
|--------------|----------|----------|
| Assets       | +        | -        |
| Expenses     | +        | -        |
| Liabilities  | -        | +        |
| Income       | -        | +        |

Example - purchase with reward points:

```
Expenses:Food              +540 INR
Liabilities:CreditCard     -540 INR
Assets:RewardPoints          +5 PTS
Income:RewardPoints          -5 PTS
Sum: 540 - 540 + 5 - 5 = 0 (balanced)
```

## Transformer

Single transformer handles all banks:

- Negative amount -> expense posting (`Expenses:Uncategorized`) + liability posting
- Positive amount -> income posting (`Income:Uncategorized`) + liability posting
- Non-zero reward points -> reward asset posting + reward income posting (same transaction)

## Rules Engine (Suckless Style)

No YAML. Config is Python, edit `config.py` directly:

```python
RULES = [
    ("swiggy", "Expenses:Food:Delivery", ["food"]),
    ("amazon", "Expenses:Shopping", []),
    ...
]
```

Rules are applied in-place during import. First matching keyword wins.

## Categorization Workflow

1. **Auto-categorization** - Rules applied during import
2. **Batch review** - `hisaab uncategorized` lists unmatched transactions
3. **Editor-native** - Open `.beancount` in editor, change `Expenses:Uncategorized` to correct category

## File Organization

Beancount is canonical. Ledger is generated on demand via `hisaab export --format ledger`.

```
~/finance/
  main.beancount         # includes all files
  accounts.beancount     # chart of accounts (open directives)
  icici.beancount        # ICICI transactions
  hdfc.beancount         # HDFC transactions
  axis.beancount         # Axis transactions
```

## Deduplication

`write_transactions` checks if a transaction's header line (`date * "" "description"`) already exists in the bank file before appending. Prevents duplicates when re-importing the same statement.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage | Beancount (text) | Git-trackable, single source of truth |
| Ledger support | Generated on demand | Avoid sync complexity |
| Config | Python (suckless) | No YAML parsing, edit source directly |
| Transformers | Single module | Parsers output identical schema |
| Reward points | Same transaction | Cleaner than linking separate transactions |
| Parser dispatch | Registry dict | Simple, extensible, no if/elif chains |
| Deduplication | Header string match | Simple, handles common re-import case |
