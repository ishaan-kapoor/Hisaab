from unittest.mock import patch, MagicMock
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from hisaab.cli import app

runner = CliRunner()


class TestCLI:
    def test_app_exists(self):
        """CLI app should exist and respond to --help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Usage" in result.output

    def test_import_command_exists(self):
        """Import command should be available."""
        result = runner.invoke(app, ["import", "--help"])
        assert result.exit_code == 0
        assert "--bank" in result.output or "bank" in result.output.lower()

    def test_uncategorized_command_exists(self):
        """Uncategorized command should be available."""
        result = runner.invoke(app, ["uncategorized", "--help"])
        assert result.exit_code == 0

    def test_balance_command_exists(self):
        """Balance command should be available."""
        result = runner.invoke(app, ["balance", "--help"])
        assert result.exit_code == 0

    def test_show_command_exists(self):
        """Show command should be available."""
        result = runner.invoke(app, ["show", "--help"])
        assert result.exit_code == 0

    def test_export_command_exists(self):
        """Export command should be available."""
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0


class TestImportCommand:
    @patch("hisaab.cli.write_transactions")
    def test_import_calls_write_when_not_dry_run(self, mock_write, tmp_path):
        """Import without --dry-run should call write_transactions."""
        test_pdf = tmp_path / "icici_statement.pdf"
        test_pdf.write_bytes(b"dummy")

        mock_df = pd.DataFrame({
            "Date": ["15/01/2026"],
            "Description": ["Test"],
            "Amount": [-100.0],
            "RewardPoints": [0],
            "RefNo": [None],
        })

        with patch("hisaab.cli.PARSERS") as mock_parsers:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = mock_df
            mock_parsers.__contains__ = lambda self, key: key == "icici"
            mock_parsers.__getitem__ = lambda self, key: mock_parser
            mock_parsers.keys.return_value = ["icici"]

            result = runner.invoke(app, ["import", str(test_pdf), "--bank", "icici"])

        mock_write.assert_called_once()

    @patch("hisaab.cli.write_transactions")
    def test_import_skips_write_on_dry_run(self, mock_write, tmp_path):
        """Import with --dry-run should NOT call write_transactions."""
        test_pdf = tmp_path / "icici_statement.pdf"
        test_pdf.write_bytes(b"dummy")

        mock_df = pd.DataFrame({
            "Date": ["15/01/2026"],
            "Description": ["Test"],
            "Amount": [-100.0],
            "RewardPoints": [0],
            "RefNo": [None],
        })

        with patch("hisaab.cli.PARSERS") as mock_parsers:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = mock_df
            mock_parsers.__contains__ = lambda self, key: key == "icici"
            mock_parsers.__getitem__ = lambda self, key: mock_parser
            mock_parsers.keys.return_value = ["icici"]

            result = runner.invoke(app, ["import", str(test_pdf), "--bank", "icici", "--dry-run"])

        mock_write.assert_not_called()


class TestUncategorizedCommand:
    def test_uncategorized_shows_uncategorized_transactions(self, tmp_path):
        """Should list transactions with Uncategorized accounts."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Mystery purchase",
                postings=[
                    Posting(account="Expenses:Uncategorized", amount=Decimal("500.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
                ],
            ),
            Transaction(
                date=date(2024, 1, 16),
                description="Swiggy order",
                postings=[
                    Posting(account="Expenses:Food:Delivery", amount=Decimal("350.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-350.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["uncategorized"])

        assert result.exit_code == 0
        assert "Mystery purchase" in result.output
        assert "Swiggy order" not in result.output

    def test_uncategorized_empty(self, tmp_path):
        """Should show message when no uncategorized transactions exist."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Swiggy order",
                postings=[
                    Posting(account="Expenses:Food:Delivery", amount=Decimal("350.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-350.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["uncategorized"])

        assert result.exit_code == 0
        assert "No uncategorized" in result.output or "0" in result.output


class TestBalanceCommand:
    def test_balance_shows_account_balances(self, tmp_path):
        """Should show balances per account."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Grocery",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("500.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
                ],
            ),
            Transaction(
                date=date(2024, 1, 16),
                description="More food",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("300.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-300.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["balance"])

        assert result.exit_code == 0
        assert "Expenses:Food" in result.output
        assert "800.00" in result.output
        assert "Liabilities:CreditCard:ICICI:Coral" in result.output
        assert "-800.00" in result.output

    def test_balance_filters_by_account(self, tmp_path):
        """Should show only matching account balances when account argument given."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Grocery",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("500.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
                ],
            ),
            Transaction(
                date=date(2024, 1, 16),
                description="Cab ride",
                postings=[
                    Posting(account="Expenses:Transport:Cab", amount=Decimal("200.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-200.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["balance", "Food"])

        assert result.exit_code == 0
        assert "Expenses:Food" in result.output
        assert "Transport" not in result.output
        assert "Liabilities" not in result.output

    def test_balance_empty_ledger(self, tmp_path):
        """Should handle empty/missing ledger gracefully."""
        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["balance"])

        assert result.exit_code == 0
        assert "No transactions" in result.output or result.output.strip() == ""


class TestShowCommand:
    def test_show_filters_by_account(self, tmp_path):
        """Should show only transactions touching the given account."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Grocery",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("500.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
                ],
            ),
            Transaction(
                date=date(2024, 1, 16),
                description="Cab ride",
                postings=[
                    Posting(account="Expenses:Transport:Cab", amount=Decimal("200.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-200.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["show", "Food"])

        assert result.exit_code == 0
        assert "Grocery" in result.output
        assert "Cab ride" not in result.output

    def test_show_all_when_no_account(self, tmp_path):
        """Should show all transactions when no account filter given."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Grocery",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("500.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
                ],
            ),
            Transaction(
                date=date(2024, 1, 16),
                description="Cab ride",
                postings=[
                    Posting(account="Expenses:Transport:Cab", amount=Decimal("200.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-200.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["show"])

        assert result.exit_code == 0
        assert "Grocery" in result.output
        assert "Cab ride" in result.output


    def test_show_filters_by_from_date(self, tmp_path):
        """Should exclude transactions before --from date."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 10),
                description="Early purchase",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("100.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-100.00")),
                ],
            ),
            Transaction(
                date=date(2024, 1, 20),
                description="Late purchase",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("200.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-200.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["show", "--from", "2024-01-15"])

        assert result.exit_code == 0
        assert "Late purchase" in result.output
        assert "Early purchase" not in result.output

    def test_show_filters_by_to_date(self, tmp_path):
        """Should exclude transactions after --to date."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 10),
                description="Early purchase",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("100.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-100.00")),
                ],
            ),
            Transaction(
                date=date(2024, 1, 20),
                description="Late purchase",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("200.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-200.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["show", "--to", "2024-01-15"])

        assert result.exit_code == 0
        assert "Early purchase" in result.output
        assert "Late purchase" not in result.output

    def test_show_filters_by_date_range(self, tmp_path):
        """Should show only transactions within --from to --to range."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 5),
                description="Too early",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("100.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-100.00")),
                ],
            ),
            Transaction(
                date=date(2024, 1, 15),
                description="In range",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("200.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-200.00")),
                ],
            ),
            Transaction(
                date=date(2024, 1, 25),
                description="Too late",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("300.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-300.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["show", "--from", "2024-01-10", "--to", "2024-01-20"])

        assert result.exit_code == 0
        assert "In range" in result.output
        assert "Too early" not in result.output
        assert "Too late" not in result.output

    def test_show_filters_by_tag(self, tmp_path):
        """Should show only transactions with matching tag."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Swiggy order",
                postings=[
                    Posting(account="Expenses:Food:Delivery", amount=Decimal("350.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-350.00")),
                ],
                tags=["food"],
            ),
            Transaction(
                date=date(2024, 1, 16),
                description="Cab ride",
                postings=[
                    Posting(account="Expenses:Transport:Cab", amount=Decimal("200.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-200.00")),
                ],
                tags=["transport"],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["show", "--tag", "food"])

        assert result.exit_code == 0
        assert "Swiggy order" in result.output
        assert "Cab ride" not in result.output

    def test_show_tag_with_no_match(self, tmp_path):
        """Should show no transactions when tag doesn't match."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Swiggy order",
                postings=[
                    Posting(account="Expenses:Food:Delivery", amount=Decimal("350.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-350.00")),
                ],
                tags=["food"],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["show", "--tag", "nonexistent"])

        assert result.exit_code == 0
        assert "No transactions" in result.output


class TestExportCommand:
    def test_export_beancount_to_stdout(self, tmp_path):
        """Export in beancount format should print to stdout."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Grocery",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("500.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["export", "--format", "beancount"])

        assert result.exit_code == 0
        assert "2024-01-15" in result.output
        assert "Grocery" in result.output

    def test_export_ledger_format(self, tmp_path):
        """Export in ledger format should use slash dates."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Grocery",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("500.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["export", "--format", "ledger"])

        assert result.exit_code == 0
        assert "2024/01/15" in result.output
        assert "Grocery" in result.output

    def test_export_to_file(self, tmp_path):
        """Export with --output should write to file."""
        from datetime import date
        from decimal import Decimal
        from hisaab.models import Posting, Transaction
        from hisaab.storage import write_transactions

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Grocery",
                postings=[
                    Posting(account="Expenses:Food", amount=Decimal("500.00")),
                    Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=Decimal("-500.00")),
                ],
            ),
        ]

        write_transactions(transactions, tmp_path, "icici")
        output_file = tmp_path / "export.beancount"

        with patch("hisaab.cli.LEDGER_DIR", tmp_path):
            result = runner.invoke(app, ["export", "--output", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert "Grocery" in output_file.read_text()
