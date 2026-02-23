from datetime import date
from decimal import Decimal

import pandas as pd

from hisaab.transformer import parse_date, transform
from hisaab.models import Transaction


class TestParseDate:
    def test_parse_dd_mm_yyyy(self):
        """Parse DD/MM/YYYY format."""
        result = parse_date("15/01/2024")
        assert result == date(2024, 1, 15)

    def test_parse_dd_mm_yy(self):
        """Parse DD/MM/YY format."""
        result = parse_date("15/01/24")
        assert result == date(2024, 1, 15)


class TestTransform:
    def test_transform_expense(self):
        """Expense row (negative amount) creates balanced transaction."""
        df = pd.DataFrame({
            "Date": ["15/01/2024"],
            "Description": ["Swiggy order"],
            "Amount": [-350.00],
        })
        txns = transform(df, default_account="Liabilities:CreditCard:ICICI")

        assert len(txns) == 1
        txn = txns[0]
        assert txn.date == date(2024, 1, 15)
        assert txn.description == "Swiggy order"
        assert len(txn.postings) == 2

        # Expense gets positive amount
        expense_posting = next(p for p in txn.postings if "Expenses" in p.account)
        assert expense_posting.amount == Decimal("350.00")

        # Liability gets negative amount
        liability_posting = next(p for p in txn.postings if "Liabilities" in p.account)
        assert liability_posting.amount == Decimal("-350.00")

        assert txn.is_balanced is True

    def test_transform_credit(self):
        """Credit row (positive amount) creates balanced transaction."""
        df = pd.DataFrame({
            "Date": ["20/01/2024"],
            "Description": ["Payment received - Thank you"],
            "Amount": [5000.00],
        })
        txns = transform(df, default_account="Liabilities:CreditCard:HDFC")

        assert len(txns) == 1
        txn = txns[0]
        assert len(txn.postings) == 2

        # Income gets negative amount (credit to income)
        income_posting = next(p for p in txn.postings if "Income" in p.account)
        assert income_posting.amount == Decimal("-5000.00")

        # Liability gets positive amount (debit to reduce liability)
        liability_posting = next(p for p in txn.postings if "Liabilities" in p.account)
        assert liability_posting.amount == Decimal("5000.00")

        assert txn.is_balanced is True

    def test_transform_with_reward_points(self):
        """Transaction with reward points creates 4 postings."""
        df = pd.DataFrame({
            "Date": ["15/01/2024"],
            "Description": ["Amazon purchase"],
            "Amount": [-1000.00],
            "RewardPoints": [50],
        })
        txns = transform(
            df,
            default_account="Liabilities:CreditCard:ICICI",
            rewards_account="Assets:RewardPoints:ICICI",
        )

        assert len(txns) == 1
        txn = txns[0]
        assert len(txn.postings) == 4

        # Check reward points postings
        rewards_asset = next(
            p for p in txn.postings if p.account == "Assets:RewardPoints:ICICI"
        )
        assert rewards_asset.amount == Decimal("50")
        assert rewards_asset.currency == "PTS"

        rewards_income = next(
            p for p in txn.postings if "Income:RewardPoints" in p.account
        )
        assert rewards_income.amount == Decimal("-50")
        assert rewards_income.currency == "PTS"

        # Main transaction should still be balanced (INR postings balance, PTS postings balance)
        inr_sum = sum(
            p.amount for p in txn.postings if p.currency == "INR"
        )
        pts_sum = sum(
            p.amount for p in txn.postings if p.currency == "PTS"
        )
        assert inr_sum == Decimal("0")
        assert pts_sum == Decimal("0")

    def test_transform_passes_ref_no(self):
        """RefNo from DataFrame is passed to Transaction.ref_no."""
        df = pd.DataFrame({
            "Date": ["15/01/2024"],
            "Description": ["Purchase"],
            "Amount": [-500.0],
            "RefNo": ["REF123"],
        })
        txns = transform(df, default_account="Liabilities:CreditCard:ICICI")
        assert txns[0].ref_no == "REF123"

    def test_transform_ref_no_none_when_missing(self):
        """RefNo defaults to None when not in DataFrame."""
        df = pd.DataFrame({
            "Date": ["15/01/2024"],
            "Description": ["Purchase"],
            "Amount": [-500.0],
        })
        txns = transform(df, default_account="Liabilities:CreditCard:ICICI")
        assert txns[0].ref_no is None

    def test_transform_multiple_rows(self):
        """Multiple rows create multiple transactions."""
        df = pd.DataFrame({
            "Date": ["15/01/2024", "16/01/2024"],
            "Description": ["First purchase", "Second purchase"],
            "Amount": [-100.00, -200.00],
        })
        txns = transform(df, default_account="Liabilities:CreditCard:HDFC")

        assert len(txns) == 2
        assert all(isinstance(t, Transaction) for t in txns)


class TestTransformEdgeCases:
    def test_zero_reward_points_no_pts_postings(self):
        """RewardPoints=0 should NOT create PTS postings."""
        df = pd.DataFrame({
            "Date": ["15/01/2024"],
            "Description": ["Purchase"],
            "Amount": [-500.0],
            "RewardPoints": [0],
        })
        txns = transform(
            df,
            default_account="Liabilities:CreditCard:ICICI",
            rewards_account="Assets:RewardPoints:ICICI",
        )

        assert len(txns) == 1
        pts_postings = [p for p in txns[0].postings if p.currency == "PTS"]
        assert len(pts_postings) == 0
        assert len(txns[0].postings) == 2

    def test_nan_reward_points_no_pts_postings(self):
        """NaN RewardPoints should NOT create PTS postings."""
        import numpy as np

        df = pd.DataFrame({
            "Date": ["15/01/2024"],
            "Description": ["Purchase"],
            "Amount": [-500.0],
            "RewardPoints": [np.nan],
        })
        txns = transform(
            df,
            default_account="Liabilities:CreditCard:ICICI",
            rewards_account="Assets:RewardPoints:ICICI",
        )

        assert len(txns) == 1
        pts_postings = [p for p in txns[0].postings if p.currency == "PTS"]
        assert len(pts_postings) == 0

    def test_no_rewards_account_skips_pts_postings(self):
        """When rewards_account is None, reward points are ignored even if present."""
        df = pd.DataFrame({
            "Date": ["15/01/2024"],
            "Description": ["Purchase"],
            "Amount": [-500.0],
            "RewardPoints": [100],
        })
        txns = transform(
            df,
            default_account="Liabilities:CreditCard:Axis",
            rewards_account=None,
        )

        assert len(txns) == 1
        pts_postings = [p for p in txns[0].postings if p.currency == "PTS"]
        assert len(pts_postings) == 0

    def test_nan_ref_no_becomes_none(self):
        """NaN in RefNo column should become None on the Transaction."""
        import numpy as np

        df = pd.DataFrame({
            "Date": ["15/01/2024"],
            "Description": ["Purchase"],
            "Amount": [-500.0],
            "RefNo": [np.nan],
        })
        txns = transform(df, default_account="Liabilities:CreditCard:ICICI")

        assert txns[0].ref_no is None
