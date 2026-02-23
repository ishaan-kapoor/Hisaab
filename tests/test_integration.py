from decimal import Decimal
from pathlib import Path

import pandas as pd

from hisaab.models import Posting, Transaction
from hisaab.transformer import transform
from hisaab.rules import categorize
from hisaab.formatters.beancount import format_transactions
from hisaab.storage import write_transactions, ensure_ledger_structure, entries_to_transactions


def test_full_pipeline():
    """Test full pipeline: DataFrame -> Transform -> Categorize -> Format"""
    df = pd.DataFrame([
        {"Date": "15/01/2026", "Description": "SWIGGY ORDER", "Amount": -540.0, "RewardPoints": 5, "RefNo": "REF001"},
        {"Date": "16/01/2026", "Description": "AMAZON PURCHASE", "Amount": -1200.0, "RewardPoints": 0, "RefNo": None},
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

    # Check RefNo passthrough
    assert transactions[0].ref_no == "REF001"
    assert transactions[1].ref_no is None
    assert transactions[2].ref_no is None

    # All transactions balanced
    for txn in transactions:
        assert txn.is_balanced

    # Format works
    output = format_transactions(transactions)
    assert "2026-01-15" in output
    assert "#food" in output


def test_pipeline_with_credits():
    """Test that credits (refunds/payments) are handled correctly."""
    df = pd.DataFrame([
        {"Date": "20/01/2026", "Description": "PAYMENT - THANK YOU", "Amount": 5000.0},
    ])

    transactions = transform(
        df,
        default_account="Liabilities:CreditCard:HDFC:TataNeu"
    )

    assert len(transactions) == 1
    txn = transactions[0]

    # Credit should have Income posting with negative amount
    income_posting = next(p for p in txn.postings if "Income" in p.account)
    assert income_posting.amount < 0

    # And liability posting with positive amount
    liability_posting = next(p for p in txn.postings if "Liabilities" in p.account)
    assert liability_posting.amount > 0

    assert txn.is_balanced


def test_pipeline_with_reward_points():
    """Test that reward points create additional postings."""
    df = pd.DataFrame([
        {"Date": "15/01/2026", "Description": "PURCHASE", "Amount": -1000.0, "RewardPoints": 100},
    ])

    transactions = transform(
        df,
        default_account="Liabilities:CreditCard:ICICI:Coral",
        rewards_account="Assets:RewardPoints:ICICI"
    )

    assert len(transactions) == 1
    txn = transactions[0]

    # Should have 4 postings: expense, liability, rewards asset, rewards income
    assert len(txn.postings) == 4

    # Check reward points postings
    pts_postings = [p for p in txn.postings if p.currency == "PTS"]
    assert len(pts_postings) == 2

    # INR postings balance
    inr_sum = sum(p.amount for p in txn.postings if p.currency == "INR")
    assert inr_sum == 0

    # PTS postings balance
    pts_sum = sum(p.amount for p in txn.postings if p.currency == "PTS")
    assert pts_sum == 0


def test_ensure_ledger_structure(tmp_path):
    """Test that ledger directory structure is created."""
    ensure_ledger_structure(tmp_path)
    assert (tmp_path / "main.beancount").exists()
    assert (tmp_path / "accounts.beancount").exists()


def test_write_transactions(tmp_path):
    """Test writing transactions to a beancount file."""
    from datetime import date

    transactions = [
        Transaction(
            date=date(2024, 1, 15),
            description="Test transaction",
            postings=[
                Posting(account="Expenses:Food", amount=Decimal("100.00")),
                Posting(account="Liabilities:CreditCard:ICICI", amount=Decimal("-100.00")),
            ],
        )
    ]

    output_file = write_transactions(transactions, tmp_path, "icici")

    assert output_file.exists()
    content = output_file.read_text()
    assert "Test transaction" in content
    assert "Expenses:Food" in content


def test_read_ledger(tmp_path):
    """Test reading transactions back from ledger files."""
    from datetime import date
    from hisaab.storage import read_ledger

    transactions = [
        Transaction(
            date=date(2024, 1, 15),
            description="Grocery shopping",
            postings=[
                Posting(account="Expenses:Food", amount=Decimal("500.00")),
                Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
            ],
        ),
    ]

    write_transactions(transactions, tmp_path, "icici")
    entries = read_ledger(tmp_path)

    assert len(entries) > 0
    txns = [e for e in entries if hasattr(e, "narration")]
    assert any("Grocery shopping" in e.narration for e in txns)


def test_write_transactions_deduplicates(tmp_path):
    """Importing the same transactions twice should not create duplicates."""
    from datetime import date

    transactions = [
        Transaction(
            date=date(2024, 1, 15),
            description="Grocery shopping",
            postings=[
                Posting(account="Expenses:Food", amount=Decimal("500.00")),
                Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
            ],
        ),
    ]

    write_transactions(transactions, tmp_path, "icici")
    write_transactions(transactions, tmp_path, "icici")

    content = (tmp_path / "icici.beancount").read_text()
    assert content.count("Grocery shopping") == 1


def test_write_transactions_allows_different_transactions(tmp_path):
    """Different transactions on the same date should not be deduplicated."""
    from datetime import date

    batch1 = [
        Transaction(
            date=date(2024, 1, 15),
            description="Grocery shopping",
            postings=[
                Posting(account="Expenses:Food", amount=Decimal("500.00")),
                Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
            ],
        ),
    ]
    batch2 = [
        Transaction(
            date=date(2024, 1, 15),
            description="Amazon purchase",
            postings=[
                Posting(account="Expenses:Shopping", amount=Decimal("1200.00")),
                Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-1200.00")),
            ],
        ),
    ]

    write_transactions(batch1, tmp_path, "icici")
    write_transactions(batch2, tmp_path, "icici")

    content = (tmp_path / "icici.beancount").read_text()
    assert "Grocery shopping" in content
    assert "Amazon purchase" in content


class TestEntriesToTransactions:
    def test_converts_basic_transaction(self, tmp_path):
        """Beancount entry converts to Transaction with correct date, description, postings."""
        from datetime import date
        from hisaab.storage import read_ledger

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Grocery shopping",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("500.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")
        entries = read_ledger(tmp_path)
        result = entries_to_transactions(entries)

        assert len(result) == 1
        txn = result[0]
        assert txn.date == date(2024, 1, 15)
        assert txn.description == "Grocery shopping"
        assert len(txn.postings) == 2
        assert txn.postings[0].account == "Expenses:Food"
        assert txn.postings[0].amount == Decimal("500.00")
        assert txn.postings[0].currency == "INR"
        assert txn.postings[1].account == "Liabilities:CreditCard:ICICI:Coral"
        assert txn.postings[1].amount == Decimal("-500.00")

    def test_preserves_payee(self, tmp_path):
        """Payee survives write -> read -> convert cycle."""
        from datetime import date
        from hisaab.storage import read_ledger

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Monthly bill",
                payee="Netflix",
                postings=[
                    Posting(account="Expenses:Entertainment", amount=Decimal("649.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-649.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")
        entries = read_ledger(tmp_path)
        result = entries_to_transactions(entries)

        assert len(result) == 1
        assert result[0].payee == "Netflix"
        assert result[0].description == "Monthly bill"

    def test_preserves_tags(self, tmp_path):
        """Tags survive write -> read -> convert cycle."""
        from datetime import date
        from hisaab.storage import read_ledger

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Swiggy order",
                postings=[
                    Posting(account="Expenses:Food:Delivery", amount=Decimal("350.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-350.00")),
                ],
                tags=["food", "delivery"],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")
        entries = read_ledger(tmp_path)
        result = entries_to_transactions(entries)

        assert len(result) == 1
        assert "food" in result[0].tags
        assert "delivery" in result[0].tags

    def test_handles_multi_currency_postings(self, tmp_path):
        """INR + PTS postings survive write -> read -> convert cycle."""
        from datetime import date
        from hisaab.storage import read_ledger

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Purchase with rewards",
                postings=[
                    Posting(account="Expenses:Shopping", amount=Decimal("1000.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-1000.00")),
                    Posting(account="Assets:RewardPoints:ICICI", amount=Decimal("50"), currency="PTS"),
                    Posting(account="Income:RewardPoints", amount=Decimal("-50"), currency="PTS"),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")
        entries = read_ledger(tmp_path)
        result = entries_to_transactions(entries)

        assert len(result) == 1
        txn = result[0]
        assert len(txn.postings) == 4

        pts_postings = [p for p in txn.postings if p.currency == "PTS"]
        assert len(pts_postings) == 2

        inr_postings = [p for p in txn.postings if p.currency == "INR"]
        assert len(inr_postings) == 2

    def test_skips_non_transaction_entries(self, tmp_path):
        """Open directives and other non-transaction entries are skipped."""
        from hisaab.storage import read_ledger

        ensure_ledger_structure(tmp_path)
        entries = read_ledger(tmp_path)
        result = entries_to_transactions(entries)

        assert len(result) == 0

    def test_empty_entries_returns_empty_list(self):
        """Empty input returns empty output."""
        result = entries_to_transactions([])
        assert result == []


class TestDedup:
    def test_dedup_with_payee(self, tmp_path):
        """Transaction with payee is deduped correctly."""
        from datetime import date

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Monthly bill",
                payee="Netflix",
                postings=[
                    Posting(account="Expenses:Entertainment", amount=Decimal("649.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-649.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")
        write_transactions(transactions, tmp_path, "icici")

        content = (tmp_path / "icici.beancount").read_text()
        assert content.count("Monthly bill") == 1

    def test_same_description_different_payee_not_deduped(self, tmp_path):
        """Same description but different payee should not be deduped."""
        from datetime import date

        batch1 = [
            Transaction(
                date=date(2024, 1, 15),
                description="Monthly subscription",
                payee="Netflix",
                postings=[
                    Posting(account="Expenses:Entertainment", amount=Decimal("649.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-649.00")),
                ],
            ),
        ]
        batch2 = [
            Transaction(
                date=date(2024, 1, 15),
                description="Monthly subscription",
                payee="Spotify",
                postings=[
                    Posting(account="Expenses:Entertainment", amount=Decimal("119.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-119.00")),
                ],
            ),
        ]

        write_transactions(batch1, tmp_path, "icici")
        write_transactions(batch2, tmp_path, "icici")

        content = (tmp_path / "icici.beancount").read_text()
        assert "Netflix" in content
        assert "Spotify" in content

    def test_same_description_no_payee_vs_with_payee_not_deduped(self, tmp_path):
        """Transaction without payee and same transaction with payee should not be deduped."""
        from datetime import date

        batch1 = [
            Transaction(
                date=date(2024, 1, 15),
                description="Payment received",
                postings=[
                    Posting(account="Income:Uncategorized", amount=Decimal("-5000.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("5000.00")),
                ],
            ),
        ]
        batch2 = [
            Transaction(
                date=date(2024, 1, 15),
                description="Payment received",
                payee="HDFC Bank",
                postings=[
                    Posting(account="Income:Uncategorized", amount=Decimal("-5000.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("5000.00")),
                ],
            ),
        ]

        write_transactions(batch1, tmp_path, "icici")
        write_transactions(batch2, tmp_path, "icici")

        content = (tmp_path / "icici.beancount").read_text()
        assert content.count("Payment received") == 2


class TestAutoOpenDirectives:
    def test_new_account_gets_open_directive(self, tmp_path):
        """Writing a transaction with a new account should add an open directive."""
        from datetime import date

        txns = [
            Transaction(
                date=date(2024, 1, 15),
                description="New category",
                postings=[
                    Posting(account="Expenses:Entertainment:Movies", amount=Decimal("500.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
                ],
            ),
        ]

        write_transactions(txns, tmp_path, "icici")

        accounts_file = tmp_path / "accounts.beancount"
        content = accounts_file.read_text()
        assert "Expenses:Entertainment:Movies" in content

    def test_existing_account_not_duplicated(self, tmp_path):
        """Accounts already in accounts.beancount should not be duplicated."""
        from datetime import date

        txns = [
            Transaction(
                date=date(2024, 1, 15),
                description="Food",
                postings=[
                    Posting(account="Expenses:Food:Delivery", amount=Decimal("350.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-350.00")),
                ],
            ),
        ]

        write_transactions(txns, tmp_path, "icici")

        accounts_file = tmp_path / "accounts.beancount"
        content = accounts_file.read_text()
        assert content.count("Expenses:Food:Delivery") == 1

    def test_pts_currency_account_gets_open_directive(self, tmp_path):
        """Reward points accounts should also get open directives."""
        from datetime import date

        txns = [
            Transaction(
                date=date(2024, 1, 15),
                description="Purchase with rewards",
                postings=[
                    Posting(account="Expenses:Shopping", amount=Decimal("1000.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-1000.00")),
                    Posting(account="Assets:RewardPoints:NewBank", amount=Decimal("50"), currency="PTS"),
                    Posting(account="Income:RewardPoints", amount=Decimal("-50"), currency="PTS"),
                ],
            ),
        ]

        write_transactions(txns, tmp_path, "icici")

        accounts_file = tmp_path / "accounts.beancount"
        content = accounts_file.read_text()
        assert "Assets:RewardPoints:NewBank" in content
        assert "Expenses:Shopping" in content


class TestFullRoundTrip:
    def test_dataframe_to_beancount_and_back(self, tmp_path):
        """Full round-trip: DataFrame -> transform -> categorize -> write -> read -> convert."""
        from hisaab.storage import read_ledger, entries_to_transactions

        df = pd.DataFrame([
            {"Date": "15/01/2026", "Description": "SWIGGY ORDER", "Amount": -540.0, "RewardPoints": 5, "RefNo": "REF001"},
            {"Date": "16/01/2026", "Description": "AMAZON PURCHASE", "Amount": -1200.0, "RewardPoints": 0},
            {"Date": "17/01/2026", "Description": "PAYMENT THANK YOU", "Amount": 5000.0, "RewardPoints": 0},
        ])

        # Forward: transform, categorize, write
        transactions = transform(
            df,
            default_account="Liabilities:CreditCard:ICICI:Coral",
            rewards_account="Assets:RewardPoints:ICICI",
        )
        categorize(transactions)
        write_transactions(transactions, tmp_path, "icici")

        # Backward: read, convert
        entries = read_ledger(tmp_path)
        recovered = entries_to_transactions(entries)

        assert len(recovered) == 3

        # Verify Swiggy transaction
        swiggy = recovered[0]
        assert swiggy.description == "SWIGGY ORDER"
        assert "food" in swiggy.tags
        expense = next(p for p in swiggy.postings if "Food" in p.account)
        assert expense.account == "Expenses:Food:Delivery"
        assert expense.amount == Decimal("540.00")

        # Verify reward points survived
        pts = [p for p in swiggy.postings if p.currency == "PTS"]
        assert len(pts) == 2

        # Verify Amazon transaction
        amazon = recovered[1]
        assert amazon.description == "AMAZON PURCHASE"
        shopping = next(p for p in amazon.postings if "Shopping" in p.account)
        assert shopping.account == "Expenses:Shopping"

        # Verify payment (credit)
        payment = recovered[2]
        assert payment.description == "PAYMENT THANK YOU"
        income = next(p for p in payment.postings if "Income" in p.account)
        assert income.amount < 0  # Income postings are negative
        liability = next(p for p in payment.postings if "Liabilities" in p.account)
        assert liability.amount > 0  # Liability reduced (positive)

    def test_write_and_read_preserves_balance(self, tmp_path):
        """All transactions remain balanced after round-trip through beancount."""
        from datetime import date
        from hisaab.storage import read_ledger, entries_to_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Complex purchase",
                postings=[
                    Posting(account="Expenses:Shopping", amount=Decimal("1000.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-1000.00")),
                    Posting(account="Assets:RewardPoints:ICICI", amount=Decimal("50"), currency="PTS"),
                    Posting(account="Income:RewardPoints", amount=Decimal("-50"), currency="PTS"),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")
        entries = read_ledger(tmp_path)
        recovered = entries_to_transactions(entries)

        assert len(recovered) == 1
        txn = recovered[0]
        inr_sum = sum(p.amount for p in txn.postings if p.currency == "INR")
        pts_sum = sum(p.amount for p in txn.postings if p.currency == "PTS")
        assert inr_sum == Decimal("0")
        assert pts_sum == Decimal("0")

    def test_multiple_banks_stay_separate(self, tmp_path):
        """Transactions written to different bank files stay independent."""
        from datetime import date
        from hisaab.storage import read_ledger, entries_to_transactions

        icici_txns = [
            Transaction(
                date=date(2024, 1, 15),
                description="ICICI purchase",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("500.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
                ],
            ),
        ]
        hdfc_txns = [
            Transaction(
                date=date(2024, 1, 15),
                description="HDFC purchase",
                postings=[
                    Posting(account="Expenses:Shopping", amount=Decimal("1200.00")),
                    Posting(account="Liabilities:CreditCard:HDFC:TataNeu", amount=Decimal("-1200.00")),
                ],
            ),
        ]

        write_transactions(icici_txns, tmp_path, "icici")
        write_transactions(hdfc_txns, tmp_path, "hdfc")

        entries = read_ledger(tmp_path)
        recovered = entries_to_transactions(entries)

        assert len(recovered) == 2
        descriptions = {t.description for t in recovered}
        assert "ICICI purchase" in descriptions
        assert "HDFC purchase" in descriptions
