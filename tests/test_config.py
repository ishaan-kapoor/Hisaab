from pathlib import Path

from hisaab.config import ACCOUNTS, REWARDS_ACCOUNTS, RULES, LEDGER_DIR


class TestConfig:
    def test_accounts_contains_required_keys(self):
        assert "icici" in ACCOUNTS
        assert "hdfc" in ACCOUNTS
        assert "axis" in ACCOUNTS

    def test_accounts_values_are_ledger_paths(self):
        assert ACCOUNTS["icici"].startswith("Liabilities:CreditCard:")
        assert ACCOUNTS["hdfc"].startswith("Liabilities:CreditCard:")
        assert ACCOUNTS["axis"].startswith("Liabilities:CreditCard:")

    def test_rewards_accounts_exist(self):
        assert "icici" in REWARDS_ACCOUNTS
        assert "hdfc" in REWARDS_ACCOUNTS

    def test_rules_structure(self):
        assert len(RULES) > 0
        for rule in RULES:
            assert len(rule) == 3
            keyword, category, tags = rule
            assert isinstance(keyword, str)
            assert isinstance(category, str)
            assert isinstance(tags, list)

    def test_rules_contain_common_keywords(self):
        keywords = [rule[0] for rule in RULES]
        assert "swiggy" in keywords
        assert "zomato" in keywords
        assert "amazon" in keywords

    def test_ledger_dir_is_path(self):
        assert isinstance(LEDGER_DIR, Path)
