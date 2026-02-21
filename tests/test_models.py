from decimal import Decimal
from datetime import date

import pytest

from hisaab.models import Posting, Transaction


class TestPosting:
    def test_posting_defaults(self):
        """Test Posting with minimal required fields."""
        posting = Posting(account="Expenses:Food", amount=Decimal("100.00"))
        assert posting.account == "Expenses:Food"
        assert posting.amount == Decimal("100.00")
        assert posting.currency == "INR"
        assert posting.tags == []
        assert posting.meta == {}

    def test_posting_with_all_fields(self):
        """Test Posting with all fields specified."""
        posting = Posting(
            account="Assets:Bank:HDFC",
            amount=Decimal("-500.00"),
            currency="USD",
            tags=["transfer", "urgent"],
            meta={"ref": "TXN123"},
        )
        assert posting.account == "Assets:Bank:HDFC"
        assert posting.amount == Decimal("-500.00")
        assert posting.currency == "USD"
        assert posting.tags == ["transfer", "urgent"]
        assert posting.meta == {"ref": "TXN123"}


class TestTransaction:
    def test_balanced_transaction(self):
        """A balanced transaction sums to zero."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Grocery shopping",
            postings=[
                Posting(account="Expenses:Food", amount=Decimal("500.00")),
                Posting(account="Assets:Bank:HDFC", amount=Decimal("-500.00")),
            ],
        )
        assert txn.is_balanced is True

    def test_unbalanced_transaction(self):
        """An unbalanced transaction does not sum to zero."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Incomplete entry",
            postings=[
                Posting(account="Expenses:Food", amount=Decimal("500.00")),
            ],
        )
        assert txn.is_balanced is False

    def test_transaction_with_all_fields(self):
        """Test Transaction with all optional fields."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Transfer",
            postings=[
                Posting(account="Assets:Bank:HDFC", amount=Decimal("-1000.00")),
                Posting(account="Assets:Bank:ICICI", amount=Decimal("1000.00")),
            ],
            payee="Self",
            tags=["transfer"],
            meta={"method": "NEFT"},
            source_file="2024-01.journal",
            ref_no="TXN123456",
        )
        assert txn.payee == "Self"
        assert txn.tags == ["transfer"]
        assert txn.meta == {"method": "NEFT"}
        assert txn.source_file == "2024-01.journal"
        assert txn.ref_no == "TXN123456"
