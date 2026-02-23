import pandas as pd
import pytest

from hisaab.parsers.base import StatementParser, REQUIRED_COLUMNS


class TestStatementParserABC:
    def test_cannot_instantiate_abc(self):
        """StatementParser is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            StatementParser()

    def test_validate_adds_missing_reward_points(self):
        """validate() adds RewardPoints=0 when column is missing."""
        class StubParser(StatementParser):
            def parse(self, file_path):
                return pd.DataFrame()

        parser = StubParser()
        df = pd.DataFrame({
            "Date": ["15/01/2026"],
            "Description": ["Test"],
            "Amount": [-100.0],
        })
        result = parser.validate(df)
        assert "RewardPoints" in result.columns
        assert result["RewardPoints"].iloc[0] == 0

    def test_validate_adds_missing_ref_no(self):
        """validate() adds RefNo=None when column is missing."""
        class StubParser(StatementParser):
            def parse(self, file_path):
                return pd.DataFrame()

        parser = StubParser()
        df = pd.DataFrame({
            "Date": ["15/01/2026"],
            "Description": ["Test"],
            "Amount": [-100.0],
            "RewardPoints": [5],
        })
        result = parser.validate(df)
        assert "RefNo" in result.columns
        assert result["RefNo"].iloc[0] is None

    def test_validate_preserves_existing_columns(self):
        """validate() keeps existing values when all columns present."""
        class StubParser(StatementParser):
            def parse(self, file_path):
                return pd.DataFrame()

        parser = StubParser()
        df = pd.DataFrame({
            "Date": ["15/01/2026"],
            "Description": ["Test"],
            "Amount": [-100.0],
            "RewardPoints": [10],
            "RefNo": ["REF123"],
        })
        result = parser.validate(df)
        assert list(result.columns) == REQUIRED_COLUMNS
        assert result["RewardPoints"].iloc[0] == 10
        assert result["RefNo"].iloc[0] == "REF123"

    def test_validate_raises_on_missing_required_column(self):
        """validate() raises ValueError when a required column (not RewardPoints/RefNo) is missing."""
        class StubParser(StatementParser):
            def parse(self, file_path):
                return pd.DataFrame()

        parser = StubParser()
        df = pd.DataFrame({
            "Date": ["15/01/2026"],
            "Amount": [-100.0],
        })
        with pytest.raises(ValueError, match="Description"):
            parser.validate(df)

    def test_validate_reorders_columns(self):
        """validate() returns columns in standard order."""
        class StubParser(StatementParser):
            def parse(self, file_path):
                return pd.DataFrame()

        parser = StubParser()
        df = pd.DataFrame({
            "Amount": [-100.0],
            "RefNo": ["X"],
            "Date": ["15/01/2026"],
            "RewardPoints": [0],
            "Description": ["Test"],
        })
        result = parser.validate(df)
        assert list(result.columns) == REQUIRED_COLUMNS


from hisaab.parsers.icici import ICICIParser
from hisaab.parsers.hdfc import HDFCParser
from hisaab.parsers.axis import AxisParser


class TestICICIParser:
    def test_is_statement_parser(self):
        """ICICIParser should inherit from StatementParser."""
        parser = ICICIParser()
        assert isinstance(parser, StatementParser)

    def test_parse_returns_dataframe(self):
        """parse() should return a DataFrame (empty for nonexistent file)."""
        parser = ICICIParser()
        result = parser.parse("/nonexistent/file.pdf")
        assert isinstance(result, pd.DataFrame)

    def test_parse_output_has_standard_columns(self):
        """parse() output should have all required columns."""
        parser = ICICIParser()
        result = parser.parse("/nonexistent/file.pdf")
        assert list(result.columns) == REQUIRED_COLUMNS


class TestHDFCParser:
    def test_is_statement_parser(self):
        parser = HDFCParser()
        assert isinstance(parser, StatementParser)

    def test_parse_returns_dataframe(self):
        parser = HDFCParser()
        result = parser.parse("/nonexistent/file.pdf")
        assert isinstance(result, pd.DataFrame)

    def test_parse_output_has_standard_columns(self):
        parser = HDFCParser()
        result = parser.parse("/nonexistent/file.pdf")
        assert list(result.columns) == REQUIRED_COLUMNS


class TestAxisParser:
    def test_is_statement_parser(self):
        parser = AxisParser()
        assert isinstance(parser, StatementParser)

    def test_parse_returns_dataframe(self):
        parser = AxisParser()
        result = parser.parse("/nonexistent/file.pdf")
        assert isinstance(result, pd.DataFrame)

    def test_parse_output_has_standard_columns(self):
        parser = AxisParser()
        result = parser.parse("/nonexistent/file.pdf")
        assert list(result.columns) == REQUIRED_COLUMNS


from hisaab.parsers import PARSERS


class TestParserRegistry:
    def test_parsers_dict_has_all_banks(self):
        assert "icici" in PARSERS
        assert "hdfc" in PARSERS
        assert "axis" in PARSERS

    def test_parsers_are_statement_parser_instances(self):
        for name, parser in PARSERS.items():
            assert isinstance(parser, StatementParser), f"{name} is not a StatementParser"
