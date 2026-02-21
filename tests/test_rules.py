from datetime import date
from decimal import Decimal

from hisaab.models import Posting, Transaction
from hisaab.rules import categorize


class TestCategorize:
    def test_categorize_swiggy(self):
        """Transaction with 'SWIGGY ORDER' should be categorized as Food:Delivery."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="SWIGGY ORDER #12345",
            postings=[
                Posting(account="Expenses:Uncategorized", amount=Decimal("350.00")),
                Posting(
                    account="Liabilities:CreditCard:ICICI", amount=Decimal("-350.00")
                ),
            ],
        )
        categorize([txn])

        # Check that the expense posting was re-categorized
        expense_posting = next(p for p in txn.postings if p.amount > 0)
        assert expense_posting.account == "Expenses:Food:Delivery"

        # Check that the tag was added
        assert "food" in txn.tags

    def test_categorize_zomato(self):
        """Transaction with 'zomato' should be categorized as Food:Delivery."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Zomato Payment for order",
            postings=[
                Posting(account="Expenses:Uncategorized", amount=Decimal("450.00")),
                Posting(
                    account="Liabilities:CreditCard:HDFC", amount=Decimal("-450.00")
                ),
            ],
        )
        categorize([txn])

        expense_posting = next(p for p in txn.postings if p.amount > 0)
        assert expense_posting.account == "Expenses:Food:Delivery"
        assert "food" in txn.tags

    def test_categorize_uber(self):
        """Transaction with 'uber' should be categorized as Transport:Cab."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="UBER BV payment",
            postings=[
                Posting(account="Expenses:Uncategorized", amount=Decimal("250.00")),
                Posting(
                    account="Liabilities:CreditCard:ICICI", amount=Decimal("-250.00")
                ),
            ],
        )
        categorize([txn])

        expense_posting = next(p for p in txn.postings if p.amount > 0)
        assert expense_posting.account == "Expenses:Transport:Cab"
        assert "transport" in txn.tags

    def test_categorize_no_match(self):
        """Transaction with unknown merchant stays Uncategorized."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Random Store Payment",
            postings=[
                Posting(account="Expenses:Uncategorized", amount=Decimal("100.00")),
                Posting(
                    account="Liabilities:CreditCard:HDFC", amount=Decimal("-100.00")
                ),
            ],
        )
        categorize([txn])

        expense_posting = next(p for p in txn.postings if p.amount > 0)
        assert expense_posting.account == "Expenses:Uncategorized"
        assert txn.tags == []

    def test_categorize_multiple_transactions(self):
        """Multiple transactions are categorized correctly."""
        txns = [
            Transaction(
                date=date(2024, 1, 15),
                description="Swiggy order",
                postings=[
                    Posting(account="Expenses:Uncategorized", amount=Decimal("350.00")),
                    Posting(
                        account="Liabilities:CreditCard:ICICI",
                        amount=Decimal("-350.00"),
                    ),
                ],
            ),
            Transaction(
                date=date(2024, 1, 16),
                description="Amazon purchase",
                postings=[
                    Posting(account="Expenses:Uncategorized", amount=Decimal("1000.00")),
                    Posting(
                        account="Liabilities:CreditCard:ICICI",
                        amount=Decimal("-1000.00"),
                    ),
                ],
            ),
        ]
        categorize(txns)

        assert txns[0].postings[0].account == "Expenses:Food:Delivery"
        assert txns[1].postings[0].account == "Expenses:Shopping"
