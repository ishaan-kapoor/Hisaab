import pdfplumber
import pandas as pd
import re
import sys
import os

def parse_hdfc_tataneu(pdf_path):
    print(f"🚀 Processing HDFC Tata Neu: {pdf_path}")
    extracted_data = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # HDFC Tata Neu typically has grid lines.
            tables = page.extract_tables({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "snap_tolerance": 4,
            })

            for table in tables:
                if not table or not table[0]: continue

                # Check Header for "DATE" and "DESCRIPTION"
                header_row = [str(c).replace('\n', ' ').strip() for c in table[0]]
                header_str = " ".join(header_row).lower()

                if "date" in header_str and "description" in header_str:

                    for row in table[1:]:
                        if not row or not row[0]: continue

                        # Flatten the row for easy searching first
                        row_str = " ".join([str(c) for c in row if c])

                        raw_col0 = str(row[0]).replace('\n', ' ').strip()

                        # --- 1. DATE Extraction ---
                        # Matches: "05/12/2025" inside "05/12/2025| 21:03..."
                        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', raw_col0)
                        if not date_match: continue
                        date = date_match.group(1)

                        # --- 2. RAW DESCRIPTION Construction ---
                        # If Col 0 has pipe/time, strip it
                        if "|" in raw_col0:
                            parts = raw_col0.split('|')
                            if len(parts) > 1:
                                # Remove time pattern "21:03"
                                temp_desc = re.sub(r'\s*\d{2}:\d{2}\s*', '', parts[1]).strip()
                                desc_part1 = temp_desc
                            else:
                                desc_part1 = raw_col0
                        else:
                            # Just remove the date
                            desc_part1 = raw_col0.replace(date, "").strip()

                        # Add Col 1 if it exists (sometimes desc spills over or contains the coins)
                        desc_part2 = str(row[1]).replace('\n', ' ').strip() if len(row) > 1 and row[1] else ""
                        full_desc = f"{desc_part1} {desc_part2}".strip()

                        # --- 3. NEUCOINS Extraction ---
                        # Look for pattern "+ 5", "+ 10.0", etc. inside the description or row
                        # We extract it and then REMOVE it from description later
                        neu_coins = 0.0
                        # Regex: literal '+', optional space, digits, optional decimal
                        coin_match = re.search(r'\+\s*(\d+(\.\d+)?)', full_desc)

                        if coin_match:
                            neu_coins = float(coin_match.group(1))
                            # We will remove this string from full_desc in Step 5

                        # --- 4. AMOUNT Extraction (Scan from Right) ---
                        amount = 0.0
                        is_credit = False
                        found_amount = False

                        for col in reversed(row):
                            if not col: continue
                            clean_col = str(col).replace(',', '').strip()

                            # Remove currency symbols (₹, Rs) and noise chars
                            clean_col_numeric = re.sub(r'[^\d\.\w\s]', '', clean_col)

                            # Look for number pattern: 751.00
                            amt_match = re.search(r'(\d+\.\d{2})', clean_col_numeric)

                            if amt_match:
                                val = float(amt_match.group(1))
                                is_credit = "cr" in clean_col.lower()
                                amount = val if is_credit else -val
                                found_amount = True
                                break

                        if not found_amount: continue

                        # --- 5. CLEAN DESCRIPTION (Deep Clean) ---

                        # A. Remove the Amount itself (e.g. "751.00")
                        amt_str = f"{abs(amount):,.2f}"
                        full_desc = full_desc.replace(amt_str, "")

                        # B. Remove the NeuCoins string (e.g. "+ 5")
                        if coin_match:
                            full_desc = full_desc.replace(coin_match.group(0), "")

                        # C. Remove generic noise like "UPI-" (Optional, personal preference)
                        # full_desc = full_desc.replace("UPI-", "")

                        # D. Aggressive Trailing Garbage Removal (The "C" Fix)
                        # We loop until the last character is a valid letter or number or close-parenthesis
                        full_desc = full_desc.strip()
                        garbage_chars = ['C', 'l', '|', '₹', '.', ' ', '-', ':', 'Cr', 'Dr']

                        # Loop to peel off garbage from the end
                        while len(full_desc) > 0:
                            # Check if it ends with known garbage words "Cr" or "Dr"
                            if full_desc.upper().endswith(" CR") or full_desc.upper().endswith(" DR"):
                                full_desc = full_desc[:-3].strip()
                                continue

                            # Check single char garbage
                            if full_desc[-1] in garbage_chars:
                                full_desc = full_desc[:-1].strip()
                            else:
                                break

                        extracted_data.append({
                            "Date": date,
                            "Description": full_desc.strip(),
                            "NeuCoins": neu_coins,
                            "Amount": amount,
                        })

    return pd.DataFrame(extracted_data)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        df = parse_hdfc_tataneu(input_file)

        if not df.empty:
            print(f"✅ Extracted {len(df)} transactions")
            print(df)

            output_csv = os.path.splitext(input_file)[0] + "_parsed.csv"
            df.to_csv(output_csv, index=False)
            print(f"💾 Saved to {output_csv}")
        else:
            print("❌ No transactions found.")
    else:
        print("Usage: python hdfc.py <file.pdf>")
