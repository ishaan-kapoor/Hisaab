from datetime import datetime, date
from decimal import Decimal
from typing import Optional

import pandas as pd

from hisaab.models import Posting, Transaction


def parse_date(date_str: str) -> date:
    """Parse date string in DD/MM/YYYY or DD/MM/YY format."""
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date: {date_str}")


def transform(
    df: pd.DataFrame,
    default_account: str,
    rewards_account: Optional[str] = None,
) -> list[Transaction]:
    """Transform a DataFrame of bank transactions into Transaction objects.

    Args:
        df: DataFrame with Date, Description, Amount columns (and optionally RewardPoints)
        default_account: The liability account (e.g., "Liabilities:CreditCard:ICICI")
        rewards_account: Optional rewards account for reward points

    Returns:
        List of Transaction objects, all balanced
    """
    transactions = []

    for _, row in df.iterrows():
        txn_date = parse_date(row["Date"])
        description = row["Description"]
        amount = Decimal(str(row["Amount"]))

        postings = []

        if amount < 0:
            # Expense: negative amount means we spent money
            expense_amount = abs(amount)
            postings.append(
                Posting(account="Expenses:Uncategorized", amount=expense_amount)
            )
            postings.append(
                Posting(account=default_account, amount=-expense_amount)
            )
        else:
            # Credit/Income: positive amount means payment or refund
            postings.append(
                Posting(account="Income:Uncategorized", amount=-amount)
            )
            postings.append(
                Posting(account=default_account, amount=amount)
            )

        # Handle reward points if present
        if rewards_account and "RewardPoints" in row and pd.notna(row["RewardPoints"]):
            points = Decimal(str(int(row["RewardPoints"])))
            if points > 0:
                postings.append(
                    Posting(account=rewards_account, amount=points, currency="PTS")
                )
                postings.append(
                    Posting(
                        account="Income:RewardPoints",
                        amount=-points,
                        currency="PTS",
                    )
                )

        txn = Transaction(
            date=txn_date,
            description=description,
            postings=postings,
        )
        transactions.append(txn)

    return transactions
