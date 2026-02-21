from pathlib import Path

ACCOUNTS = {
    "icici_coral": "Liabilities:CreditCard:ICICI:Coral",
    "hdfc_tataneu": "Liabilities:CreditCard:HDFC:TataNeu",
    "axis": "Liabilities:CreditCard:Axis:MyZone",
}

REWARDS_ACCOUNTS = {
    "icici_coral": "Assets:RewardPoints:ICICI",
    "hdfc_tataneu": "Assets:RewardPoints:HDFC:NeuCoins",
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
