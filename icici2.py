import pdfplumber
import pandas as pd
import re
import sys
import os

def parse_icici_ultimate(pdf_path):
    print(f"🚀 Processing ICICI (Typo-Proof Mode): {pdf_path}")
    extracted_data = []

    start_date_pattern = re.compile(r'^(\d{2}/\d{2}/\d{4})')
    middle_date_pattern = re.compile(r'\s+(\d{2}/\d{2}/\d{4})\s+')

    # STOP PATTERNS (Updated to handle 'ICICl' typo and other common variants)
    STOP_PATTERNS = [
        r"total\s+due", r"credit\s+limit", r"available\s+credit",
        r"previous\s+balance", r"purchases\s*/\s*charges",
        r"reward\s+points\s+earned", r"most\s+important\s+terms",
        r"invoice\s+no", r"cin\s+no", r"credit\s+card\s+statement",
        r"download\s+the\s+imobile", r"scan\s+the\s+or\s+code",
        r"gst\s+number", r"registered\s+office",
        r"important\s+messages", r"safe\s+banking\s+tips",
        r"complimentary\s+insurance", r"fuel\s+surcharge",
        r"toll\s+free", r"email\s+id", r"click\s+here\s+to\s+access",
        r"ask\s+ipal", r"contact\s+our\s+customer\s+care",
        r"for\s+further\s+information",

        # TYPO-PROOFED PATTERNS
        r"icic[il1]\s+bank\s+rewards",  # Matches ICICI, ICICl, ICIC1
        r"total\s+points\s+earned",
        r"points\s+earned\s+on"
    ]

    current_txn = None

    def process_transaction_line(line_text):
        date_match = start_date_pattern.match(line_text)
        if not date_match: return None
        date = date_match.group(1)
        rest = line_text[len(date):].strip()

        amt_match = re.search(r'([\d,]+\.\d{2}(\s*(?:CR|Cr|Dr))?)$', rest)
        amount = 0.0
        is_credit = False
        if amt_match:
            amt_str_full = amt_match.group(1)
            rest = rest[:amt_match.start()].strip()
            is_credit = "cr" in amt_str_full.lower()
            clean_amt = re.sub(r'[^\d\.]', '', amt_str_full)
            amount = float(clean_amt)
            if not is_credit: amount = -amount

        ser_match = re.match(r'^(\d+)', rest)
        ser_no = ""
        if ser_match:
            ser_no = ser_match.group(1)
            rest = rest[len(ser_no):].strip()

        tokens = rest.split()
        points = "0"
        intl_amt = "0.00"
        desc_words = tokens
        if tokens:
            last_token = tokens[-1]
            second_last = tokens[-2] if len(tokens) > 1 else None
            if re.match(r'[\d,]+\.\d{2}', last_token):
                intl_amt = last_token
                if second_last and re.match(r'^\d+$', second_last):
                    points = second_last
                    desc_words = tokens[:-2]
                else:
                    desc_words = tokens[:-1]
            elif re.match(r'^\d+$', last_token):
                points = last_token
                desc_words = tokens[:-1]

        return {
            "Date": date,
            "RefNo": ser_no,
            "Description": " ".join(desc_words),
            "RewardPoints": points,
            "IntlAmount": intl_amt,
            "Amount": amount,
            "Type": "Income" if is_credit else "Expense"
        }

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if not text: continue
            lines = text.split('\n')

            for line in lines:
                raw_line = line
                line = line.strip()
                if not line: continue

                # GLOBAL FILTERS
                if "XXXX" in line: continue
                if "Date" in line and "SerNo" in line: continue
                if "International Spends" in line: continue
                if "Page " in line and " of " in line: continue

                # MERGED LINE DETECTION
                mid_match = middle_date_pattern.search(line)
                if mid_match and not start_date_pattern.match(line):
                    split_idx = mid_match.start()
                    part1 = line[:split_idx].strip()
                    part2 = line[split_idx:].strip()

                    if current_txn:
                         cutoff_idx = len(part1)
                         found_stop = False
                         for pat in STOP_PATTERNS:
                             m = re.search(pat, part1, re.IGNORECASE)
                             if m:
                                 cutoff_idx = min(cutoff_idx, m.start())
                                 found_stop = True

                         clean_part1 = part1[:cutoff_idx].strip()
                         if clean_part1 and not re.search(r'^\s*\d+%\s*$', clean_part1):
                             current_txn["Description"] += " " + clean_part1
                             extracted_data.append(current_txn)
                             current_txn = None

                    new_txn = process_transaction_line(part2)
                    if new_txn: current_txn = new_txn
                    continue

                # NEW TRANSACTION
                if start_date_pattern.match(line):
                    if current_txn:
                        extracted_data.append(current_txn)
                        current_txn = None
                    current_txn = process_transaction_line(line)

                else:
                    # CONTINUATION LOGIC
                    if current_txn:
                        # FILTER A: Indentation
                        leading_spaces = len(raw_line) - len(raw_line.lstrip())
                        if leading_spaces < 2: continue

                        # FILTER B: Regex Stop Patterns (Truncate In-Line)
                        stop_found = False
                        truncated_line = line

                        for pat in STOP_PATTERNS:
                            m = re.search(pat, line, re.IGNORECASE)
                            if m:
                                truncated_line = line[:m.start()].strip()
                                stop_found = True
                                break

                        if stop_found:
                            if truncated_line:
                                current_txn["Description"] += " " + truncated_line
                            extracted_data.append(current_txn)
                            current_txn = None
                            continue

                        # FILTER C: Artifacts
                        if re.search(r'^\s*\d+%\s*$', line): continue
                        if line.startswith("#") or line.startswith("*"): continue

                        current_txn["Description"] += " " + line

    if current_txn:
        extracted_data.append(current_txn)

    return pd.DataFrame(extracted_data)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        df = parse_icici_ultimate(input_file)

        if not df.empty:
            print(f"✅ Extracted {len(df)} transactions")
            df["RefNo"] = df["RefNo"].astype(str)
            df["Description"] = df["Description"].astype(str).str.replace(r'# I.*', '', regex=True).str.strip()
            print(df.tail())

            output_csv = os.path.splitext(input_file)[0] + "_parsed.csv"
            df.to_csv(output_csv, index=False)
            print(f"💾 Saved to {output_csv}")
        else:
            print("❌ No transactions found.")
    else:
        print("Usage: python icici.py <file.pdf>")
