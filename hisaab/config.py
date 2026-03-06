from pathlib import Path

ACCOUNTS = {
    "icici": "Liabilities:CreditCard:ICICI:Coral",
    "hdfc": "Liabilities:CreditCard:HDFC:TataNeu",
    "axis": "Liabilities:CreditCard:Axis:MyZone",
    "icici-xls": "Assets:Bank:ICICI",
    "hdfc-xls": "Assets:Bank:HDFC",
    "axis-xls": "Assets:Bank:Axis",
}

REWARDS_ACCOUNTS = {
    "icici": "Assets:RewardPoints:ICICI",
    "hdfc": "Assets:RewardPoints:HDFC:NeuCoins",
}

# Rules: (keyword_regex, category, tags)
# Applied in order - first match wins. Keywords are case-insensitive regex.
RULES = [
    # Food - Delivery
    ("swiggy", "Expenses:Food:Delivery", ["food"]),
    ("zomato", "Expenses:Food:Delivery", ["food"]),
    ("dunzo", "Expenses:Food:Delivery", ["food"]),

    # Food - Grocery
    ("blinkit", "Expenses:Food:Grocery", ["food"]),
    ("zepto", "Expenses:Food:Grocery", ["food"]),
    ("bigbasket", "Expenses:Food:Grocery", ["food"]),
    ("jiomart", "Expenses:Food:Grocery", ["food"]),
    ("dmart", "Expenses:Food:Grocery", ["food"]),
    ("grofers", "Expenses:Food:Grocery", ["food"]),
    ("instamart", "Expenses:Food:Grocery", ["food"]),  # Swiggy Instamart

    # Food - Restaurants & Cafes
    ("dominos", "Expenses:Food:Restaurant", ["food"]),
    ("pizza hut", "Expenses:Food:Restaurant", ["food"]),
    ("mcdonald", "Expenses:Food:Restaurant", ["food"]),
    ("kfc", "Expenses:Food:Restaurant", ["food"]),
    ("subway", "Expenses:Food:Restaurant", ["food"]),
    ("starbucks", "Expenses:Food:Restaurant", ["food"]),
    ("cafe coffee day", "Expenses:Food:Restaurant", ["food"]),
    ("burger king", "Expenses:Food:Restaurant", ["food"]),

    # Transport - Cab
    ("uber", "Expenses:Transport:Cab", ["transport"]),
    ("ola\\b", "Expenses:Transport:Cab", ["transport"]),  # \b avoids matching "cola"
    ("rapido", "Expenses:Transport:Cab", ["transport"]),

    # Transport - Fuel
    ("hpcl", "Expenses:Transport:Fuel", ["transport"]),
    ("iocl", "Expenses:Transport:Fuel", ["transport"]),
    ("bpcl", "Expenses:Transport:Fuel", ["transport"]),
    ("indian oil", "Expenses:Transport:Fuel", ["transport"]),
    ("hindustan petroleum", "Expenses:Transport:Fuel", ["transport"]),
    ("bharat petroleum", "Expenses:Transport:Fuel", ["transport"]),
    ("shell", "Expenses:Transport:Fuel", ["transport"]),

    # Transport - Travel
    ("irctc", "Expenses:Travel:Train", ["travel"]),
    ("indian railway", "Expenses:Travel:Train", ["travel"]),
    ("indigo", "Expenses:Travel:Flight", ["travel"]),
    ("air india", "Expenses:Travel:Flight", ["travel"]),
    ("spicejet", "Expenses:Travel:Flight", ["travel"]),
    ("akasa", "Expenses:Travel:Flight", ["travel"]),
    ("vistara", "Expenses:Travel:Flight", ["travel"]),
    ("makemytrip", "Expenses:Travel:Booking", ["travel"]),
    ("goibibo", "Expenses:Travel:Booking", ["travel"]),
    ("easemytrip", "Expenses:Travel:Booking", ["travel"]),
    ("cleartrip", "Expenses:Travel:Booking", ["travel"]),
    ("yatra", "Expenses:Travel:Booking", ["travel"]),
    ("oyo", "Expenses:Travel:Hotel", ["travel"]),
    ("airbnb", "Expenses:Travel:Hotel", ["travel"]),

    # Shopping - Online
    ("amazon", "Expenses:Shopping:Online", []),
    ("flipkart", "Expenses:Shopping:Online", []),
    ("myntra", "Expenses:Shopping:Online", []),
    ("ajio", "Expenses:Shopping:Online", []),
    ("meesho", "Expenses:Shopping:Online", []),
    ("nykaa", "Expenses:Shopping:Online", []),
    ("tatacliq", "Expenses:Shopping:Online", []),
    ("snapdeal", "Expenses:Shopping:Online", []),
    ("firstcry", "Expenses:Shopping:Online", []),

    # Shopping - Electronics
    ("reliance digital", "Expenses:Shopping:Electronics", []),
    ("croma", "Expenses:Shopping:Electronics", []),

    # Entertainment - Streaming
    ("netflix", "Expenses:Entertainment:Streaming", ["entertainment"]),
    ("hotstar", "Expenses:Entertainment:Streaming", ["entertainment"]),
    ("amazon prime", "Expenses:Entertainment:Streaming", ["entertainment"]),
    ("prime video", "Expenses:Entertainment:Streaming", ["entertainment"]),
    ("jiocinema", "Expenses:Entertainment:Streaming", ["entertainment"]),
    ("sonyliv", "Expenses:Entertainment:Streaming", ["entertainment"]),
    ("zee5", "Expenses:Entertainment:Streaming", ["entertainment"]),
    ("spotify", "Expenses:Entertainment:Streaming", ["entertainment"]),
    ("jiosaavn", "Expenses:Entertainment:Streaming", ["entertainment"]),
    ("gaana", "Expenses:Entertainment:Streaming", ["entertainment"]),

    # Entertainment - Other
    ("bookmyshow", "Expenses:Entertainment:Events", ["entertainment"]),
    ("pvr", "Expenses:Entertainment:Movies", ["entertainment"]),
    ("inox", "Expenses:Entertainment:Movies", ["entertainment"]),

    # Telecom
    ("airtel", "Expenses:Utilities:Telecom", []),
    ("jio\\b", "Expenses:Utilities:Telecom", []),
    ("vodafone", "Expenses:Utilities:Telecom", []),
    ("vi\\b", "Expenses:Utilities:Telecom", []),
    ("bsnl", "Expenses:Utilities:Telecom", []),

    # Utilities
    ("electricity", "Expenses:Utilities:Electricity", []),
    ("bescom", "Expenses:Utilities:Electricity", []),
    ("msedcl", "Expenses:Utilities:Electricity", []),
    ("tata power", "Expenses:Utilities:Electricity", []),
    ("adani electricity", "Expenses:Utilities:Electricity", []),
    ("piped gas", "Expenses:Utilities:Gas", []),
    ("indraprastha gas", "Expenses:Utilities:Gas", []),
    ("mahanagar gas", "Expenses:Utilities:Gas", []),

    # Health
    ("apollo", "Expenses:Health:Pharmacy", ["health"]),
    ("medplus", "Expenses:Health:Pharmacy", ["health"]),
    ("netmeds", "Expenses:Health:Pharmacy", ["health"]),
    ("1mg", "Expenses:Health:Pharmacy", ["health"]),
    ("pharmeasy", "Expenses:Health:Pharmacy", ["health"]),
    ("tata 1mg", "Expenses:Health:Pharmacy", ["health"]),

    # Finance - Insurance
    ("hdfc life", "Expenses:Finance:Insurance", []),
    ("icici prudential", "Expenses:Finance:Insurance", []),
    ("star health", "Expenses:Finance:Insurance", []),
    ("niva bupa", "Expenses:Finance:Insurance", []),

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
