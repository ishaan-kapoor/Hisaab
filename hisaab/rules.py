from hisaab.config import RULES
from hisaab.models import Transaction


def categorize(transactions: list[Transaction]) -> None:
    """Categorize transactions in-place based on rules."""
    for txn in transactions:
        text = f"{txn.payee or ''} {txn.description}".lower()

        for keyword, category, tags in RULES:
            if keyword in text:
                for posting in txn.postings:
                    if "Uncategorized" in posting.account:
                        posting.account = category
                txn.tags.extend(tags)
                break
