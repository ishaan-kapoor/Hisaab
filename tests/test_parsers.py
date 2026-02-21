import pandas as pd

from hisaab.parsers import icici, hdfc, axis


class TestParserImports:
    def test_icici_has_parse_function(self):
        """ICICI parser should have a callable parse function."""
        assert hasattr(icici, "parse")
        assert callable(icici.parse)

    def test_hdfc_has_parse_function(self):
        """HDFC parser should have a callable parse function."""
        assert hasattr(hdfc, "parse")
        assert callable(hdfc.parse)

    def test_axis_has_parse_function(self):
        """Axis parser should have a callable parse function."""
        assert hasattr(axis, "parse")
        assert callable(axis.parse)


class TestParserReturnTypes:
    def test_icici_returns_dataframe(self):
        """ICICI parser should return a DataFrame with expected columns."""
        # Using a non-existent file should return empty DataFrame
        result = icici.parse("/nonexistent/file.pdf")
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["Date", "Description", "Amount", "RewardPoints"]

    def test_hdfc_returns_dataframe(self):
        """HDFC parser should return a DataFrame with expected columns."""
        result = hdfc.parse("/nonexistent/file.pdf")
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["Date", "Description", "Amount", "RewardPoints"]

    def test_axis_returns_dataframe(self):
        """Axis parser should return a DataFrame with expected columns."""
        result = axis.parse("/nonexistent/file.pdf")
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["Date", "Description", "Amount", "RewardPoints"]
