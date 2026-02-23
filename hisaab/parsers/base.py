from abc import ABC, abstractmethod

import pandas as pd

REQUIRED_COLUMNS = ["Date", "Description", "Amount", "RewardPoints", "RefNo"]


class StatementParser(ABC):
    """Base class for all statement parsers."""

    @abstractmethod
    def parse(self, file_path: str) -> pd.DataFrame:
        """Parse a statement file into a standardized DataFrame.

        Returns DataFrame with columns:
        - Date: str in DD/MM/YYYY format
        - Description: str
        - Amount: float, negative=expense, positive=income/credit
        - RewardPoints: numeric, 0 if not applicable
        - RefNo: str or None
        """
        ...

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure output has required columns with defaults for optional ones."""
        if "RewardPoints" not in df.columns:
            df = df.copy()
            df["RewardPoints"] = 0
        if "RefNo" not in df.columns:
            df = df.copy()
            df["RefNo"] = None
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                raise ValueError(f"Parser output missing required column: {col}")
        return df[REQUIRED_COLUMNS]
