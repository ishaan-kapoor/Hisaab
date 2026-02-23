from datetime import date
from decimal import Decimal

from beancount import loader

from hisaab.models import Posting, Transaction
from hisaab.formatters.beancount import format_transaction, format_transactions
from hisaab.formatters import ledger


def _validate_beancount(transactions: list[Transaction]) -> None:
    """Validate that formatted output parses as valid Beancount."""
    accounts = set()
    for txn in transactions:
        for p in txn.postings:
            accounts.add(p.account)

    currencies = set()
    for txn in transactions:
        for p in txn.postings:
            currencies.add(p.currency)

    preamble_lines = [f"1970-01-01 commodity {c}" for c in sorted(currencies)]
    for acct in sorted(accounts):
        preamble_lines.append(f"1970-01-01 open {acct}")

    preamble = "\n".join(preamble_lines) + "\n\n"
    body = format_transactions(transactions)

    _, errors, _ = loader.load_string(preamble + body)
    assert errors == [], f"Beancount parse errors: {errors}"


class TestBeancountFormatter:
    def test_format_simple_transaction(self):
        """Test formatting a basic transaction."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Grocery shopping",
            postings=[
                Posting(account="Expenses:Food", amount=Decimal("500.00")),
                Posting(account="Liabilities:CreditCard:HDFC", amount=Decimal("-500.00")),
            ],
        )
        result = format_transaction(txn)

        assert "2024-01-15" in result
        assert '"Grocery shopping"' in result
        assert "Expenses:Food" in result
        assert "500.00 INR" in result
        assert "Liabilities:CreditCard:HDFC" in result
        assert "-500.00 INR" in result
        _validate_beancount([txn])

    def test_format_transaction_with_tags(self):
        """Test formatting a transaction with tags."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Swiggy order",
            postings=[
                Posting(account="Expenses:Food:Delivery", amount=Decimal("350.00")),
                Posting(account="Liabilities:CreditCard:ICICI", amount=Decimal("-350.00")),
            ],
            tags=["food", "delivery"],
        )
        result = format_transaction(txn)

        assert "#food" in result
        assert "#delivery" in result
        _validate_beancount([txn])

    def test_format_transaction_with_payee(self):
        """Test formatting a transaction with payee."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Monthly bill",
            payee="Netflix",
            postings=[
                Posting(account="Expenses:Entertainment", amount=Decimal("649.00")),
                Posting(account="Liabilities:CreditCard:HDFC", amount=Decimal("-649.00")),
            ],
        )
        result = format_transaction(txn)

        assert '"Netflix"' in result
        _validate_beancount([txn])

    def test_format_transaction_with_meta(self):
        """Test formatting a transaction with metadata."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="ATM withdrawal",
            postings=[
                Posting(account="Assets:Cash", amount=Decimal("2000.00")),
                Posting(account="Assets:Bank:HDFC", amount=Decimal("-2000.00")),
            ],
            meta={"ref": "TXN123456"},
        )
        result = format_transaction(txn)

        assert 'ref: "TXN123456"' in result
        _validate_beancount([txn])

    def test_format_transactions_multiple(self):
        """Test formatting multiple transactions."""
        txns = [
            Transaction(
                date=date(2024, 1, 15),
                description="First",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("100.00")),
                    Posting(account="Assets:Cash", amount=Decimal("-100.00")),
                ],
            ),
            Transaction(
                date=date(2024, 1, 16),
                description="Second",
                postings=[
                    Posting(account="Expenses:Transport", amount=Decimal("50.00")),
                    Posting(account="Assets:Cash", amount=Decimal("-50.00")),
                ],
            ),
        ]
        result = format_transactions(txns)

        assert "First" in result
        assert "Second" in result
        assert "\n\n" in result  # Transactions separated by blank line
        _validate_beancount(txns)

    def test_reward_points_valid_beancount(self):
        """Transaction with multi-currency postings (INR + PTS) is valid Beancount."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Purchase with rewards",
            postings=[
                Posting(account="Expenses:Shopping", amount=Decimal("1000.00")),
                Posting(account="Liabilities:CreditCard:ICICI", amount=Decimal("-1000.00")),
                Posting(account="Assets:RewardPoints:ICICI", amount=Decimal("50"), currency="PTS"),
                Posting(account="Income:RewardPoints", amount=Decimal("-50"), currency="PTS"),
            ],
        )
        _validate_beancount([txn])


class TestLedgerFormatter:
    def test_ledger_format_simple(self):
        """Test Ledger date format (YYYY/MM/DD with slashes)."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Grocery shopping",
            postings=[
                Posting(account="Expenses:Food", amount=Decimal("500.00")),
                Posting(account="Liabilities:CreditCard:HDFC", amount=Decimal("-500.00")),
            ],
        )
        result = ledger.format_transaction(txn)

        assert "2024/01/15" in result  # Ledger uses slashes, not dashes
        assert "Grocery shopping" in result
        assert "Expenses:Food" in result
        assert "500.00 INR" in result

    def test_ledger_format_with_tags(self):
        """Test Ledger tag format (:tag: with colons, not hashes)."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Swiggy order",
            postings=[
                Posting(account="Expenses:Food:Delivery", amount=Decimal("350.00")),
                Posting(account="Liabilities:CreditCard:ICICI", amount=Decimal("-350.00")),
            ],
            tags=["food", "delivery"],
        )
        result = ledger.format_transaction(txn)

        assert ":food:delivery:" in result  # Ledger uses :tag: format

    def test_ledger_format_with_payee(self):
        """Test Ledger payee format."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Monthly bill",
            payee="Netflix",
            postings=[
                Posting(account="Expenses:Entertainment", amount=Decimal("649.00")),
                Posting(account="Liabilities:CreditCard:HDFC", amount=Decimal("-649.00")),
            ],
        )
        result = ledger.format_transaction(txn)

        assert "Netflix" in result
        assert "Monthly bill" in result

    def test_ledger_format_transactions_multiple(self):
        """Test formatting multiple transactions in Ledger format."""
        txns = [
            Transaction(
                date=date(2024, 1, 15),
                description="First",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("100.00")),
                    Posting(account="Assets:Cash", amount=Decimal("-100.00")),
                ],
            ),
            Transaction(
                date=date(2024, 1, 16),
                description="Second",
                postings=[
                    Posting(account="Expenses:Transport", amount=Decimal("50.00")),
                    Posting(account="Assets:Cash", amount=Decimal("-50.00")),
                ],
            ),
        ]
        result = ledger.format_transactions(txns)

        assert "First" in result
        assert "Second" in result
        assert "\n\n" in result
