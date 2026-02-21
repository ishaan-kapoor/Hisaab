# Hisaab

Personal finance and expense tracker with double-entry accounting.

## Status

**Design Approved** - See `docs/plans/2026-02-15-hisaab-design.md`

## What This Is

- Parse bank statements (PDF/CSV) from Indian banks (ICICI, HDFC, Axis)
- Store transactions in Beancount format (plain text, git-trackable)
- Auto-categorize expenses using suckless rules (edit Python, no YAML)
- Query via CLI wrapper around bean-query/bean-report
- Generate Ledger format on demand

## Architecture

```
PDF/CSV  Parser  DataFrame  Transformer  Transaction  Rules  Formatter  .beancount
                  (standardized)  (+ rewards)                                   .ledger
```

## Existing Parsers

| File | Bank | Format | Notes |
|------|------|--------|-------|
| `icici.py` | ICICI | PDF | Smart indent detection for multi-line descriptions |
| `hdfc.py` | HDFC Tata Neu | PDF | Grid tables, extracts NeuCoins |
| `axis.py` | Axis | PDF | Table extraction |

## Usage (Current - Parsers Only)

```bash
python icici.py statement.pdf    # Outputs statement_parsed.csv
python hdfc.py statement.pdf
python axis.py statement.pdf
```

## Usage (Planned - Full CLI)

```bash
hisaab import statement.pdf --bank icici
hisaab show --from 2026-01-01 --tag food
hisaab balance Expenses
hisaab uncategorized
hisaab export --ledger
```

See design doc for full details.
