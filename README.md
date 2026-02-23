# Hisaab

Personal finance and expense tracker with double-entry accounting.

## What This Is

- Parse bank statements (PDF/CSV) from Indian banks (ICICI, HDFC, Axis)
- Store transactions in Beancount format (plain text, git-trackable)
- Auto-categorize expenses using suckless rules (edit Python, no YAML)
- Query via CLI wrapper around bean-query/bean-report
- Generate Ledger format on demand

## Architecture

```
PDF/CSV -> Parser -> DataFrame -> Transformer -> Transaction -> Rules -> Formatter -> .beancount
                  (standardized)  (+ rewards)                                      -> .ledger
```

## Existing Parsers

| File | Bank | Format | Notes |
|------|------|--------|-------|
| `icici.py` | ICICI | PDF | Smart indent detection for multi-line descriptions |
| `hdfc.py` | HDFC Tata Neu | PDF | Grid tables, extracts NeuCoins |
| `axis.py` | Axis | PDF | Table extraction |

## Usage

```bash
hisaab import statement.pdf --bank icici    # Parse PDF, categorize, write beancount
hisaab import statement.pdf --bank icici -n # Dry run (print without saving)
hisaab show                                 # List all transactions
hisaab show Expenses:Food                   # Filter by account substring
hisaab balance                              # Show account balances
hisaab uncategorized                        # List uncategorized transactions
hisaab export                               # Export as beancount (default)
hisaab export --format ledger               # Export as ledger
hisaab export --format ledger -o out.ledger # Export to file
```

See `design.md` for architecture details.
