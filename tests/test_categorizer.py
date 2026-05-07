from datetime import date
from decimal import Decimal
from pathlib import Path

from hisaab.categorizer import (
    append_rule,
    existing_categories,
    existing_tags,
    first_alpha_token,
    group_uncategorized,
    is_uncategorized,
    recategorize_entry_in_file,
)
from hisaab.models import Posting, Transaction


def _txn(desc: str, amount: str = "100.00", account: str = "Expenses:Uncategorized") -> Transaction:
    return Transaction(
        date=date(2024, 1, 15),
        description=desc,
        postings=[
            Posting(account=account, amount=Decimal(amount)),
            Posting(account="Liabilities:CreditCard:ICICI:Coral", amount=-Decimal(amount)),
        ],
    )


class TestFirstAlphaToken:
    def test_basic(self):
        assert first_alpha_token("SWIGGY *MUMBAI 1234") == "swiggy"

    def test_skips_non_alpha_leading(self):
        assert first_alpha_token("*123 AMAZON RETAIL") == "amazon"

    def test_empty_when_all_punct(self):
        assert first_alpha_token("123 *** 456") == ""


class TestIsUncategorized:
    def test_true_when_postings_have_uncategorized(self):
        assert is_uncategorized(_txn("Test")) is True

    def test_false_when_categorized(self):
        assert is_uncategorized(_txn("Test", account="Expenses:Food")) is False


class TestGroupUncategorized:
    def test_groups_by_first_token(self):
        """SWIGGY *MUMBAI and SWIGGY *DELHI both fingerprint to 'swiggy'
        because one 'swiggy' rule covers both."""
        txns = [
            _txn("SWIGGY *MUMBAI 1234"),
            _txn("SWIGGY *DELHI 5678"),
            _txn("AMAZON RETAIL"),
        ]
        buckets = group_uncategorized(txns)
        assert len(buckets) == 2
        assert buckets[0].fingerprint == "swiggy"
        assert buckets[0].count == 2

    def test_orders_by_count_then_total(self):
        txns = [
            _txn("SWIGGY 1", "120.00"),
            _txn("SWIGGY 2", "120.00"),  # 2 txns, ₹240
            _txn("AMAZON", "5000.00"),    # 1 txn, ₹5000
        ]
        buckets = group_uncategorized(txns)
        assert buckets[0].fingerprint == "swiggy"  # wins on count
        assert buckets[1].fingerprint == "amazon"

    def test_breaks_count_tie_by_total(self):
        txns = [
            _txn("SMALL 1", "10.00"),
            _txn("SMALL 2", "10.00"),
            _txn("BIG 1", "5000.00"),
            _txn("BIG 2", "5000.00"),
        ]
        buckets = group_uncategorized(txns)
        # equal count -> bigger total wins
        assert buckets[0].fingerprint == "big"

    def test_skips_categorized(self):
        txns = [
            _txn("SWIGGY", account="Expenses:Food:Delivery"),
            _txn("AMAZON"),
        ]
        buckets = group_uncategorized(txns)
        assert len(buckets) == 1
        assert "amazon" in buckets[0].fingerprint

    def test_samples_dedupes(self):
        txns = [_txn("SAME DESC") for _ in range(5)]
        buckets = group_uncategorized(txns)
        assert buckets[0].samples == ["SAME DESC"]


class TestExistingCategories:
    def test_from_rules(self):
        rules = [
            ("swiggy", "Expenses:Food:Delivery", ["food"]),
            ("amazon", "Expenses:Shopping:Online", []),
        ]
        cats = existing_categories(rules)
        assert "Expenses:Food:Delivery" in cats
        assert "Expenses:Shopping:Online" in cats

    def test_from_accounts_file(self, tmp_path):
        rules = []
        accounts = tmp_path / "accounts.beancount"
        accounts.write_text(
            "; Chart of Accounts\n"
            "1970-01-01 open Expenses:Travel:Hotel\n"
            "1970-01-01 open Liabilities:CreditCard:ICICI\n"
        )
        cats = existing_categories(rules, tmp_path)
        assert "Expenses:Travel:Hotel" in cats
        assert "Liabilities:CreditCard:ICICI" in cats


class TestExistingTags:
    def test_collects_unique(self):
        rules = [
            ("a", "X", ["food"]),
            ("b", "Y", ["food", "delivery"]),
            ("c", "Z", []),
        ]
        assert existing_tags(rules) == ["delivery", "food"]


class TestAppendRule:
    def test_appends_before_closing_bracket(self, tmp_path):
        cfg = tmp_path / "config.py"
        cfg.write_text(
            'RULES = [\n'
            '    ("swiggy", "Expenses:Food:Delivery", ["food"]),\n'
            ']\n'
        )
        append_rule(cfg, "blinkit", "Expenses:Food:Grocery", ["food", "grocery"])
        text = cfg.read_text()
        # Order matters: blinkit must come AFTER swiggy and BEFORE closing ]
        assert text == (
            'RULES = [\n'
            '    ("swiggy", "Expenses:Food:Delivery", ["food"]),\n'
            "    ('blinkit', 'Expenses:Food:Grocery', ['food', 'grocery']),\n"
            ']\n'
        )

    def test_handles_empty_tags(self, tmp_path):
        cfg = tmp_path / "config.py"
        cfg.write_text('RULES = [\n]\n')
        append_rule(cfg, "amazon", "Expenses:Shopping", [])
        text = cfg.read_text()
        assert "[]" in text
        assert "amazon" in text


class TestRecategorizeEntryInFile:
    def test_replaces_account(self, tmp_path):
        f = tmp_path / "icici.beancount"
        f.write_text(
            '2024-01-15 * "" "SWIGGY"\n'
            '  Expenses:Uncategorized  540.00 INR\n'
            '  Liabilities:CreditCard:ICICI  -540.00 INR\n'
        )
        changed = recategorize_entry_in_file(
            f, lineno=1,
            account_changes={"Expenses:Uncategorized": "Expenses:Food:Delivery"},
            add_tags=[],
        )
        assert changed
        assert "Expenses:Food:Delivery  540.00 INR" in f.read_text()
        assert "Expenses:Uncategorized" not in f.read_text()

    def test_appends_tags_to_header(self, tmp_path):
        f = tmp_path / "icici.beancount"
        f.write_text(
            '2024-01-15 * "" "SWIGGY"\n'
            '  Expenses:Food:Delivery  540.00 INR\n'
            '  Liabilities:CreditCard:ICICI  -540.00 INR\n'
        )
        changed = recategorize_entry_in_file(
            f, lineno=1, account_changes={}, add_tags=["food"],
        )
        assert changed
        assert '"SWIGGY" #food' in f.read_text()

    def test_does_not_duplicate_existing_tag(self, tmp_path):
        f = tmp_path / "icici.beancount"
        f.write_text(
            '2024-01-15 * "" "SWIGGY" #food\n'
            '  Expenses:Food:Delivery  540.00 INR\n'
            '  Liabilities:CreditCard:ICICI  -540.00 INR\n'
        )
        changed = recategorize_entry_in_file(
            f, lineno=1, account_changes={}, add_tags=["food"],
        )
        # No account changes and tag already present; nothing modified
        assert not changed
        assert f.read_text().count("#food") == 1

    def test_only_touches_target_entry(self, tmp_path):
        f = tmp_path / "icici.beancount"
        f.write_text(
            '2024-01-15 * "" "FIRST"\n'
            '  Expenses:Uncategorized  100.00 INR\n'
            '  Liabilities:CreditCard:ICICI  -100.00 INR\n'
            '\n'
            '2024-01-16 * "" "SECOND"\n'
            '  Expenses:Uncategorized  200.00 INR\n'
            '  Liabilities:CreditCard:ICICI  -200.00 INR\n'
        )
        # Edit only the FIRST entry (lineno=1)
        recategorize_entry_in_file(
            f, lineno=1,
            account_changes={"Expenses:Uncategorized": "Expenses:Food"},
            add_tags=[],
        )
        text = f.read_text()
        # First entry's posting changed, second entry's preserved
        assert "Expenses:Food  100.00 INR" in text
        assert "Expenses:Uncategorized  200.00 INR" in text
