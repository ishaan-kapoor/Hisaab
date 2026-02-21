from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class Posting:
    """A single posting (account + amount) within a transaction."""

    account: str
    amount: Decimal
    currency: str = "INR"
    tags: list[str] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)


@dataclass
class Transaction:
    """A complete transaction with multiple postings."""

    date: date
    description: str
    postings: list[Posting]
    payee: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)
    source_file: Optional[str] = None
    ref_no: Optional[str] = None

    @property
    def is_balanced(self) -> bool:
        """Returns True if the sum of all posting amounts equals zero."""
        return sum(p.amount for p in self.postings) == Decimal("0")
