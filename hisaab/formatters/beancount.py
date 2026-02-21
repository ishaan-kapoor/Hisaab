from hisaab.models import Transaction


def format_transaction(txn: Transaction) -> str:
    tags = " ".join(f"#{t}" for t in txn.tags) if txn.tags else ""
    payee = f'"{txn.payee}"' if txn.payee else '""'
    narration = f'"{txn.description}"'

    header = f'{txn.date} * {payee} {narration}'
    if tags:
        header = f'{header} {tags}'

    lines = [header]

    for key, val in txn.meta.items():
        lines.append(f'  {key}: "{val}"')

    for p in txn.postings:
        lines.append(f'  {p.account}  {p.amount:.2f} {p.currency}')

    return "\n".join(lines)


def format_transactions(transactions: list[Transaction]) -> str:
    return "\n\n".join(format_transaction(t) for t in transactions)
