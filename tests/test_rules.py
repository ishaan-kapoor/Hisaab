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


class TestCategorizeEdgeCases:
    def test_case_insensitive_matching(self):
        """Rules match regardless of case in description."""
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

        expense_posting = next(p for p in txn.postings if p.amount > 0)
        assert expense_posting.account == "Expenses:Food:Delivery"

    def test_first_match_wins(self):
        """When description matches multiple rules, the first rule wins."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="swiggy zomato combo deal",
            postings=[
                Posting(account="Expenses:Uncategorized", amount=Decimal("500.00")),
                Posting(
                    account="Liabilities:CreditCard:ICICI", amount=Decimal("-500.00")
                ),
            ],
        )
        categorize([txn])

        expense_posting = next(p for p in txn.postings if p.amount > 0)
        # "swiggy" appears first in RULES, so it should win
        assert expense_posting.account == "Expenses:Food:Delivery"
        # Tags should be from swiggy rule only, not both
        assert txn.tags == ["food"]

    def test_matches_on_payee_field(self):
        """Rules should match keywords found in the payee field."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Online payment",
            payee="Swiggy",
            postings=[
                Posting(account="Expenses:Uncategorized", amount=Decimal("350.00")),
                Posting(
                    account="Liabilities:CreditCard:ICICI", amount=Decimal("-350.00")
                ),
            ],
        )
        categorize([txn])

        expense_posting = next(p for p in txn.postings if p.amount > 0)
        assert expense_posting.account == "Expenses:Food:Delivery"

    def test_already_categorized_not_changed(self):
        """Transactions without Uncategorized postings are not modified."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Swiggy order",
            postings=[
                Posting(
                    account="Expenses:Food:Restaurant", amount=Decimal("350.00")
                ),
                Posting(
                    account="Liabilities:CreditCard:ICICI", amount=Decimal("-350.00")
                ),
            ],
        )
        categorize([txn])

        # Account should remain as-is since it is not "Uncategorized"
        assert txn.postings[0].account == "Expenses:Food:Restaurant"
        # Tags should still be added though (rules only check description, not account)
        assert "food" in txn.tags

    def test_no_rules_match_leaves_uncategorized(self):
        """Transaction with no matching rules stays Uncategorized with no tags."""
        txn = Transaction(
            date=date(2024, 1, 15),
            description="Unknown vendor payment",
            postings=[
                Posting(account="Expenses:Uncategorized", amount=Decimal("999.00")),
                Posting(
                    account="Liabilities:CreditCard:ICICI", amount=Decimal("-999.00")
                ),
            ],
        )
        categorize([txn])

        assert txn.postings[0].account == "Expenses:Uncategorized"
        assert txn.tags == []


class TestRegexRules:
    def test_regex_pattern_matches(self):
        """Regex pattern in rules should match transactions."""
        from unittest.mock import patch

        regex_rules = [
            (r"swiggy|zomato", "Expenses:Food:Delivery", ["food"]),
        ]

        txns = [
            Transaction(
                date=date(2024, 1, 15),
                description="SWIGGY ORDER 123",
                postings=[
                    Posting(account="Expenses:Uncategorized", amount=Decimal("350.00")),
                    Posting(
                        account="Liabilities:CreditCard:ICICI:Coral",
                        amount=Decimal("-350.00"),
                    ),
                ],
            ),
            Transaction(
                date=date(2024, 1, 16),
                description="ZOMATO DELIVERY",
                postings=[
                    Posting(account="Expenses:Uncategorized", amount=Decimal("250.00")),
                    Posting(
                        account="Liabilities:CreditCard:ICICI:Coral",
                        amount=Decimal("-250.00"),
                    ),
                ],
            ),
        ]

        with patch("hisaab.rules.RULES", regex_rules):
            categorize(txns)

        assert txns[0].postings[0].account == "Expenses:Food:Delivery"
        assert txns[1].postings[0].account == "Expenses:Food:Delivery"

    def test_regex_word_boundary(self):
        """Regex with word boundaries should not match substrings incorrectly."""
        from unittest.mock import patch

        regex_rules = [
            (r"\buber\b", "Expenses:Transport:Cab", ["transport"]),
        ]

        txns = [
            Transaction(
                date=date(2024, 1, 15),
                description="UBER CAB RIDE",
                postings=[
                    Posting(account="Expenses:Uncategorized", amount=Decimal("200.00")),
                    Posting(
                        account="Liabilities:CreditCard:ICICI:Coral",
                        amount=Decimal("-200.00"),
                    ),
                ],
            ),
            Transaction(
                date=date(2024, 1, 16),
                description="TUBEROUS PLANT SHOP",
                postings=[
                    Posting(account="Expenses:Uncategorized", amount=Decimal("150.00")),
                    Posting(
                        account="Liabilities:CreditCard:ICICI:Coral",
                        amount=Decimal("-150.00"),
                    ),
                ],
            ),
        ]

        with patch("hisaab.rules.RULES", regex_rules):
            categorize(txns)

        assert txns[0].postings[0].account == "Expenses:Transport:Cab"
        assert txns[1].postings[0].account == "Expenses:Uncategorized"

    def test_existing_plain_rules_still_work(self):
        """Plain string keywords should still work after regex change."""
        txns = [
            Transaction(
                date=date(2024, 1, 15),
                description="swiggy order",
                postings=[
                    Posting(account="Expenses:Uncategorized", amount=Decimal("350.00")),
                    Posting(
                        account="Liabilities:CreditCard:ICICI:Coral",
                        amount=Decimal("-350.00"),
                    ),
                ],
            ),
        ]

        categorize(txns)

        assert txns[0].postings[0].account == "Expenses:Food:Delivery"
