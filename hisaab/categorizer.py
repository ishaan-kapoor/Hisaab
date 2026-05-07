"""Helpers for the merchants / learn / recategorize CLI commands."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Optional

from hisaab.models import Transaction


_NON_ALPHA = re.compile(r"[^a-z]+")


def first_alpha_token(desc: str) -> str:
    """First alpha-only token of the description, lowercased.

    Used both as the bucket key (so 'SWIGGY *MUMBAI' and 'SWIGGY *DELHI'
    group together — one 'swiggy' rule covers both) and as the default
    pattern suggestion in 'learn'.
    """
    for token in desc.lower().split():
        cleaned = _NON_ALPHA.sub("", token)
        if cleaned:
            return cleaned
    return ""


def _primary_amount(txn: Transaction) -> Decimal:
    primary = next(
        (
            p for p in txn.postings
            if not (p.account.startswith("Expenses:") or p.account.startswith("Income:"))
        ),
        txn.postings[0] if txn.postings else None,
    )
    return primary.amount if primary else Decimal("0")


@dataclass
class MerchantBucket:
    fingerprint: str
    transactions: list[Transaction] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.transactions)

    @property
    def total_abs(self) -> Decimal:
        return sum((abs(_primary_amount(t)) for t in self.transactions), Decimal("0"))

    @property
    def samples(self) -> list[str]:
        seen: list[str] = []
        for t in self.transactions:
            if t.description not in seen:
                seen.append(t.description)
            if len(seen) == 3:
                break
        return seen

    @property
    def most_common_description(self) -> str:
        from collections import Counter
        c = Counter(t.description for t in self.transactions)
        return c.most_common(1)[0][0] if c else ""


def is_uncategorized(txn: Transaction) -> bool:
    return any("Uncategorized" in p.account for p in txn.postings)


def group_uncategorized(transactions: list[Transaction]) -> list[MerchantBucket]:
    """Group uncategorized transactions by description fingerprint.

    Returned in priority order: most frequent first, ties broken by total
    absolute amount descending.
    """
    by_fp: dict[str, MerchantBucket] = {}
    for t in transactions:
        if not is_uncategorized(t):
            continue
        fp = first_alpha_token(t.description) or "(unknown)"
        by_fp.setdefault(fp, MerchantBucket(fingerprint=fp)).transactions.append(t)

    return sorted(
        by_fp.values(),
        key=lambda b: (-b.count, -b.total_abs),
    )


def existing_categories(rules: list, ledger_dir: Optional[Path] = None) -> list[str]:
    """All categories the user has used: from RULES + accounts.beancount."""
    cats: set[str] = set()
    for _, category, _ in rules:
        cats.add(category)
    if ledger_dir is not None:
        accounts_file = Path(ledger_dir) / "accounts.beancount"
        if accounts_file.exists():
            for line in accounts_file.read_text().splitlines():
                m = re.match(r"^\d{4}-\d{2}-\d{2}\s+open\s+(\S+)", line)
                if m:
                    cats.add(m.group(1))
    return sorted(cats)


def existing_tags(rules: list) -> list[str]:
    tags: set[str] = set()
    for _, _, tag_list in rules:
        for t in tag_list:
            tags.add(t)
    return sorted(tags)


def fzf_pick(candidates: list[str], prompt: str, multi: bool = False) -> list[str]:
    """Pick from candidates via fzf. Falls back to raw input if fzf is missing.

    Returns a list of selected/typed values (single-element list when not multi).
    Empty list means the user cancelled.
    """
    candidates_text = "\n".join(sorted(set(c for c in candidates if c)))
    args = [
        "fzf",
        "--print-query",
        f"--prompt={prompt}> ",
        "--height=30%",
        "--reverse",
    ]
    if multi:
        args.append("--multi")
    try:
        r = subprocess.run(
            args, input=candidates_text, capture_output=True, text=True
        )
    except FileNotFoundError:
        s = input(f"{prompt}> ").strip()
        if not s:
            return []
        if multi:
            return [t.strip() for t in s.split(",") if t.strip()]
        return [s]

    lines = r.stdout.splitlines()
    if not lines:
        return []
    query = lines[0]
    selections = [l for l in lines[1:] if l]
    if selections:
        return selections
    return [query] if query else []


def input_with_prefill(prompt: str, prefill: str) -> str:
    """input() with an editable default value (uses readline)."""
    try:
        import readline
    except ImportError:
        v = input(f"{prompt} [{prefill}]: ").strip()
        return v or prefill

    def _hook():
        readline.insert_text(prefill)
        readline.redisplay()

    readline.set_startup_hook(_hook)
    try:
        return input(prompt).strip()
    finally:
        readline.set_startup_hook()


_RULE_LINE = "    ({pattern!r}, {category!r}, {tags!r}),"


def append_rule(config_path: Path, pattern: str, category: str, tags: list[str]) -> None:
    """Append a rule to the RULES list in config.py.

    Inserts immediately before the closing ']' of the RULES list. The closing
    ']' is expected to be on its own line at column 0 (the convention used
    throughout config.py).
    """
    text = config_path.read_text()
    lines = text.splitlines()

    start = None
    for i, line in enumerate(lines):
        if line.startswith("RULES = ["):
            start = i
            break
    if start is None:
        raise RuntimeError(f"Could not find 'RULES = [' in {config_path}")

    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].rstrip() == "]":
            end = i
            break
    if end is None:
        raise RuntimeError(f"Could not find closing ']' for RULES in {config_path}")

    new_line = _RULE_LINE.format(pattern=pattern, category=category, tags=tags)
    lines.insert(end, new_line)
    config_path.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""))


def reload_rules(config_path: Path) -> list:
    """Reload the RULES module attribute after appending. Used by 'learn'."""
    import importlib

    from hisaab import config as cfg

    importlib.reload(cfg)
    return cfg.RULES


def recategorize_entry_in_file(
    file_path: Path, lineno: int, account_changes: dict[str, str], add_tags: list[str]
) -> bool:
    """Modify a single entry in a beancount file in place.

    - Replaces lines matching `^\\s+<old_account>\\s+...` with the new account
      (preserving the rest of the line).
    - Appends new tags (prefixed with #) to the header line if not already there.

    Returns True if the file was modified.
    """
    text = file_path.read_text()
    lines = text.splitlines(keepends=True)
    if lineno < 1 or lineno > len(lines):
        return False

    header_idx = lineno - 1
    end_idx = header_idx + 1
    while end_idx < len(lines) and lines[end_idx].startswith((" ", "\t")):
        end_idx += 1

    modified = False

    if add_tags:
        header = lines[header_idx]
        existing_header_tags = set(re.findall(r"#(\S+)", header))
        new_tags = [t for t in add_tags if t not in existing_header_tags]
        if new_tags:
            line_no_newline = header.rstrip("\n")
            tag_str = " " + " ".join(f"#{t}" for t in new_tags)
            lines[header_idx] = line_no_newline + tag_str + "\n"
            modified = True

    for idx in range(header_idx + 1, end_idx):
        line = lines[idx]
        for old_acct, new_acct in account_changes.items():
            if old_acct in line:
                lines[idx] = line.replace(old_acct, new_acct, 1)
                modified = True
                break

    if modified:
        file_path.write_text("".join(lines))
    return modified
