import pandas as pd


def parse(pdf_path: str) -> pd.DataFrame:
    """Parse ICICI credit card statement PDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        DataFrame with columns: Date, Description, Amount, RewardPoints
    """
    # TODO: Implement actual parsing using pdfplumber
    # For now, return empty DataFrame with expected columns
    return pd.DataFrame(columns=["Date", "Description", "Amount", "RewardPoints"])
