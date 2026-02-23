# TODO

## CLI Enhancements

- [x] `show` command: add `--from` and `--to` date range filters
- [x] `show` command: add `--tag` filter
- [x] `balance` command: add optional `account` argument to filter by account substring

## New Parsers

- [ ] Bank account statement parser (savings/current account)
- [ ] UPI export parser
- [ ] Amazon Pay statement parser

## Categorization Rules

- [ ] Add more rules to `config.py` as transactions are categorized
- [x] Consider regex-based rules for more complex matching

## Storage

- [x] Auto-create `open` directives in `accounts.beancount` when new accounts appear in categorized transactions
