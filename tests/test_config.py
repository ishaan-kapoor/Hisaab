from pathlib import Path

from hisaab.config import ACCOUNTS, REWARDS_ACCOUNTS, RULES, LEDGER_DIR


class TestConfig:
    def test_accounts_contains_required_keys(self):
        """ACCOUNTS dict must contain our credit card accounts."""
        assert "icici_coral" in ACCOUNTS
        assert "hdfc_tataneu" in ACCOUNTS
        assert "axis" in ACCOUNTS

    def test_accounts_values_are_ledger_paths(self):
        """Account values should be Ledger-style account paths."""
        assert ACCOUNTS["icici_coral"].startswith("Liabilities:CreditCard:")
        assert ACCOUNTS["hdfc_tataneu"].startswith("Liabilities:CreditCard:")
        assert ACCOUNTS["axis"].startswith("Liabilities:CreditCard:")

    def test_rewards_accounts_exist(self):
        """REWARDS_ACCOUNTS for cards with reward points."""
        assert "icici_coral" in REWARDS_ACCOUNTS
        assert "hdfc_tataneu" in REWARDS_ACCOUNTS

    def test_rules_structure(self):
        """RULES should be list of (keyword, category, tags) tuples."""
        assert len(RULES) > 0
        for rule in RULES:
            assert len(rule) == 3
            keyword, category, tags = rule
            assert isinstance(keyword, str)
            assert isinstance(category, str)
            assert isinstance(tags, list)

    def test_rules_contain_common_keywords(self):
        """RULES should have common merchant keywords."""
        keywords = [rule[0] for rule in RULES]
        assert "swiggy" in keywords
        assert "zomato" in keywords
        assert "amazon" in keywords

    def test_ledger_dir_is_path(self):
        """LEDGER_DIR should be a Path object."""
        assert isinstance(LEDGER_DIR, Path)
