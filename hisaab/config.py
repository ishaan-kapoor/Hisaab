from pathlib import Path

ACCOUNTS = {
    "icici": "Liabilities:CreditCard:ICICI:Coral",
    "hdfc": "Liabilities:CreditCard:HDFC:TataNeu",
    "axis": "Liabilities:CreditCard:Axis:MyZone",
}

REWARDS_ACCOUNTS = {
    "icici": "Assets:RewardPoints:ICICI",
    "hdfc": "Assets:RewardPoints:HDFC:NeuCoins",
}

# Rules: (keyword, category, tags)
RULES = [
    ("swiggy", "Expenses:Food:Delivery", ["food"]),
    ("zomato", "Expenses:Food:Delivery", ["food"]),
    ("amazon", "Expenses:Shopping", []),
    ("uber", "Expenses:Transport:Cab", ["transport"]),
    ("ola", "Expenses:Transport:Cab", ["transport"]),
    ("flipkart", "Expenses:Shopping", []),
]

LEDGER_DIR = Path("~/finance").expanduser()
