import pdfplumber
import pandas as pd
import re
import sys
import os

def parse_icici_smart_indent(pdf_path):
    print(f"🚀 Processing ICICI (Smart Indent Mode): {pdf_path}")
    extracted_data = []

    date_pattern = re.compile(r'^(\d{2}/\d{2}/\d{4})')

    current_txn = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # layout=True preserves spaces roughly corresponding to position
            text = page.extract_text(layout=True)
            if not text: continue

            lines = text.split('\n')

            for line in lines:
                # We need the RAW line to check indentation (leading spaces)
                raw_line = line
                stripped_line = line.strip()

                if not stripped_line: continue

                # --- 1. DETECT NEW TRANSACTION ---
                # We check the stripped line for the Date
                date_match = date_pattern.match(stripped_line)

                if date_match:
                    # Save previous transaction
                    if current_txn:
                        extracted_data.append(current_txn)
                        current_txn = None

                    # --- PARSE NEW TRANSACTION ---
                    date = date_match.group(1)

                    # Remove Date (and leading whitespace)
                    # "18/12/2025   1253..." -> "1253..."
                    # We rebuild the 'rest' string from the stripped version for easier regex
                    rest = stripped_line[len(date):].strip()

                    # A. Amount (Look for "3,881.00 CR" at end)
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

                    # B. SerNo (Look for digits at start)
                    ser_match = re.match(r'^(\d+)', rest)
                    ser_no = ""
                    if ser_match:
                        ser_no = ser_match.group(1)
                        rest = rest[len(ser_no):].strip()

                    # C. Points & Intl (Look at the end of the remaining string)
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

                    description = " ".join(desc_words)

                    current_txn = {
                        "Date": date,
                        "RefNo": ser_no,
                        "Description": description,
                        "RewardPoints": points,
                        "IntlAmount": intl_amt,
                        "Amount": amount,
                        "Type": "Income" if is_credit else "Expense"
                    }

                else:
                    # --- 2. SMART CONTINUATION CHECK ---
                    if current_txn:
                        # Safety 1: It's a date we missed?
                        if date_pattern.match(stripped_line): continue

                        # SMART CHECK: Indentation
                        # Count leading spaces
                        leading_spaces = len(raw_line) - len(raw_line.lstrip())

                        # Logic:
                        # A valid description continuation MUST be indented.
                        # The Date column is at 0. The RefNo is at ~15. The Description starts at ~25-30.
                        # Footer text usually starts at 0 or 2 spaces.
                        # We set a Threshold.
                        # If indentation < 10 spaces, it's starting at the margin -> It's a Footer/Header -> IGNORE.

                        INDENT_THRESHOLD = 10

                        if leading_spaces < INDENT_THRESHOLD:
                            # This line is too far left. It's likely "Total Due", "Page 1", or "ICICl Bank..."
                            # Stop appending.
                            continue

                        # Safety 2: Check for artifacts like "25%" alone (from header overlap)
                        if re.search(r'^\s*\d+%\s*$', raw_line): continue

                        # If it passes, append to description
                        current_txn["Description"] += " " + stripped_line

    if current_txn:
        extracted_data.append(current_txn)

    return pd.DataFrame(extracted_data)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        df = parse_icici_smart_indent(input_file)

        if not df.empty:
            print(f"✅ Extracted {len(df)} transactions")
            df["RefNo"] = df["RefNo"].astype(str)

            # Final Safety Cleaning (just in case)
            df["Description"] = df["Description"].astype(str).str.replace(r'# I.*', '', regex=True).str.strip()

            print(df.head())

            output_csv = os.path.splitext(input_file)[0] + "_parsed.csv"
            df.to_csv(output_csv, index=False)
            print(f"💾 Saved to {output_csv}")
        else:
            print("❌ No transactions found.")
    else:
        print("Usage: python icici.py <file.pdf>")
