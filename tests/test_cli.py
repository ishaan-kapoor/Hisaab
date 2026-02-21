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
