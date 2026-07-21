from pathlib import Path

ACCOUNTS = {
    "icici-cc": "Liabilities:CreditCard:ICICI",
    "hdfc-cc": "Liabilities:CreditCard:HDFC",
    "axis-cc": "Liabilities:CreditCard:Axis",
    "icici": "Assets:Bank:ICICI",
    "hdfc": "Assets:Bank:HDFC",
    "axis": "Assets:Bank:Axis",
}

REWARDS_ACCOUNTS = {
    "icici": "Assets:RewardPoints:ICICI",
    "hdfc": "Assets:RewardPoints:HDFC:NeuCoins",
    "axis": "Assets:RewardPoints:Axis",
}

# Rules: (keyword_regex, category, tags)
# Applied in order - first match wins. Keywords are case-insensitive regex.
RULES = [
    ("i shop https://ishop i", "Expenses:IShop", ["voucher"]),

    # Food
    ("swiggy", "Expenses:Food", []),
    ("zomato", "Expenses:Food", []),
    ("blinkit", "Expenses:Grocery", []),
    ("zepto", "Expenses:Grocery", []),
    ("bigbasket", "Expenses:Grocery", []),
    ("jiomart", "Expenses:Grocery", []),
    ("dmart", "Expenses:Grocery", []),
    ("grofers", "Expenses:Grocery", []),
    ("instamart", "Expenses:Grocery", []),  # Swiggy Instamart
    ("dominos", "Expenses:Food", []),
    ("pizza hut", "Expenses:Food", []),
    ("mcdonald", "Expenses:Food", []),
    ("kfc", "Expenses:Food", []),
    ("subway", "Expenses:Food", []),
    ("starbucks", "Expenses:Food", []),
    ("cafe coffee day", "Expenses:Food", []),
    ("burger king", "Expenses:Food", []),

    # Transport - Cab
    ("uber", "Expenses:Commute", []),
    ("ola\\b", "Expenses:Commute", []),  # \b avoids matching "cola"
    ("rapido", "Expenses:Commute", []),

    # Transport - Travel
    ("indigo", "Expenses:Travel:Flight", []),
    ("air india", "Expenses:Travel:Flight", []),
    ("spicejet", "Expenses:Travel:Flight", []),
    ("makemytrip", "Expenses:Travel", []),
    ("goibibo", "Expenses:Travel", []),
    ("easemytrip", "Expenses:Travel", []),
    ("cleartrip", "Expenses:Travel", []),
    ("yatra", "Expenses:Travel", []),
    ("airbnb", "Expenses:Travel:Stay", []),

    # Shopping - Online
    ("amazon", "Expenses:Shopping", []),
    ("flipkart", "Expenses:Shopping", []),
    ("myntra", "Expenses:Shopping", []),
    ("ajio", "Expenses:Shopping", []),
    ("meesho", "Expenses:Shopping", []),
    ("nykaa", "Expenses:Shopping", []),
    ("tatacliq", "Expenses:Shopping", []),
    ("snapdeal", "Expenses:Shopping", []),
    ("firstcry", "Expenses:Shopping", []),

    # Entertainment - Streaming
    ("netflix", "Expenses:Entertainment:Streaming", []),
    ("hotstar", "Expenses:Entertainment:Streaming", []),
    ("amazon prime", "Expenses:Entertainment:Streaming", []),
    ("prime video", "Expenses:Entertainment:Streaming", []),
    ("jiocinema", "Expenses:Entertainment:Streaming", []),
    ("sonyliv", "Expenses:Entertainment:Streaming", []),
    ("zee5", "Expenses:Entertainment:Streaming", []),
    ("spotify", "Expenses:Entertainment:Streaming", []),
    ("jiosaavn", "Expenses:Entertainment:Streaming", []),
    ("gaana", "Expenses:Entertainment:Streaming", []),

    # Entertainment - Other
    ("bookmyshow", "Expenses:Entertainment:Cinema", []),

    # Telecom
    ("airtel", "Expenses:Utilities:Telecom", []),
    ("jio\\b", "Expenses:Utilities:Telecom", []),
    ("vodafone", "Expenses:Utilities:Telecom", []),
    ("vi\\b", "Expenses:Utilities:Telecom", []),
    ("bsnl", "Expenses:Utilities:Telecom", []),

    # Utilities
    ("electricity", "Expenses:Utilities:Electricity", []),
    ("piped gas", "Expenses:Utilities:Gas", []),

    # Health
    ("apollo", "Expenses:Health:Pharmacy", []),
    ("medplus", "Expenses:Health:Pharmacy", []),
    ("netmeds", "Expenses:Health:Pharmacy", []),
    ("1mg", "Expenses:Health:Pharmacy", []),
    ("pharmeasy", "Expenses:Health:Pharmacy", []),
    ("tata 1mg", "Expenses:Health:Pharmacy", []),

    # Finance - Insurance
    ("hdfc life", "Expenses:Utilities:Insurance", []),

    # Investments
    ("zerodha", "Assets:Investment:MutualFund", ["investment", "zerodha"]),
    ("ach-dr-bd-mf utilities lump", "Assets:Investment:MutualFund", ["investment", "vishalJi"]),
    ("indian clearing corp", "Assets:Investment:MutualFund", ["investment", "zerodha"]),

    # Finance - Credit Card Payment
    ("payment.*thank", "Income:CreditCardPayment", []),
    ("cc payment", "Income:CreditCardPayment", []),
    ("credit card payment", "Income:CreditCardPayment", []),
]

LEDGER_DIR = Path("~/finance").expanduser()
