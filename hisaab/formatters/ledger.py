from hisaab.models import Transaction


def format_transaction(txn: Transaction) -> str:
    payee = txn.payee or ""
    if payee:
        header = f'{txn.date.strftime("%Y/%m/%d")} {payee} - {txn.description}'
    else:
        header = f'{txn.date.strftime("%Y/%m/%d")} {txn.description}'

    lines = [header]

    if txn.tags:
        tags = ":".join(txn.tags)
        lines.append(f"    ; :{tags}:")

    for p in txn.postings:
        lines.append(f"    {p.account}    {p.amount:.2f} {p.currency}")

    return "\n".join(lines)


def format_transactions(transactions: list[Transaction]) -> str:
    return "\n\n".join(format_transaction(t) for t in transactions)
