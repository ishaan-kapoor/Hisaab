from decimal import Decimal
from pathlib import Path

import pandas as pd

from hisaab.models import Posting, Transaction
from hisaab.transformer import transform
from hisaab.rules import categorize
from hisaab.formatters.beancount import format_transactions
from hisaab.storage import write_transactions, ensure_ledger_structure


def test_full_pipeline():
    """Test full pipeline: DataFrame -> Transform -> Categorize -> Format"""
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
