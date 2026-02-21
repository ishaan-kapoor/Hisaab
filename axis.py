import pdfplumber
import pandas as pd
import re

def parse_axis_final(pdf_path):
    extracted_data = []

    with pdfplumber.open(pdf_path) as pdf:
        print(f"📄 Processing {pdf_path}...")

        for page in pdf.pages:
            # Use 'lines' strategy as it found 6 tables (which is correct structure)
            tables = page.extract_tables({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "snap_tolerance": 4,
            })

            print(f"   Found {len(tables)} tables on Page {page.page_number}")

            for t_idx, table in enumerate(tables):
                # 1. SEARCH FOR HEADER
                header_idx = -1
                col_map = {}

                for i, row in enumerate(table):
                    # Flatten row to string to search for keywords
                    row_str = [str(c).lower().replace('\n', ' ') for c in row if c]
                    full_text = " ".join(row_str)

                    # We are looking for the Transaction Table Header
                    if "date" in full_text and "transaction details" in full_text:
                        header_idx = i
                        # print(f"   ✅ Transaction Table found at Index {t_idx}, Row {i}")

                        # Map columns dynamically
                        for col_i, cell in enumerate(row):
                            val = str(cell).lower()
                            if "date" in val: col_map['date'] = col_i
                            elif "transaction details" in val: col_map['desc'] = col_i
                            elif "amount" in val: col_map['amount'] = col_i
                            elif "cashback earned" in val: col_map['cashback'] = col_i
                        break

                # If this table doesn't have the header, check the next one
                if header_idx == -1: continue

                # 2. EXTRACT ROWS
                for row in table[header_idx + 1:]:
                    if len(row) < 2: continue # Skip junk rows

                    # Get Date Column
                    date_idx = col_map.get('date', 0)
                    date_val = row[date_idx]

                    # Strict Date Regex: DD/MM/YYYY
                    if not date_val or not re.match(r'\d{2}/\d{2}/\d{4}', str(date_val).strip()):
                        continue

                    # Get Amount Column
                    amt_idx = col_map.get('amount', -2) # Default to 2nd last if mapping fails
                    raw_amt = str(row[amt_idx]).replace(',', '').strip()

                    # Handle Dr/Cr logic
                    is_credit = "cr" in raw_amt.lower()
                    # Extract numeric part
                    amt_match = re.search(r'([\d\.]+)', raw_amt)
                    if not amt_match: continue

                    amount = float(amt_match.group(1))
                    final_amount = amount if is_credit else -amount

                    # Get Description
                    desc_idx = col_map.get('desc', 1)
                    desc = str(row[desc_idx]).replace('\n', ' ').strip()

                    # Get Description
                    cb_idx = col_map.get('cashback', 1)
                    raw_cashback = str(row[cb_idx]).replace('\n', ' ').strip()

                    cb_is_credit = "cr" in raw_cashback.lower()
                    # Extract numeric part
                    cb_match = re.search(r'([\d\.]+)', raw_cashback)
                    if not cb_match: continue

                    cb_amount = float(cb_match.group(1))
                    final_cb_amount = cb_amount if cb_is_credit else -cb_amount

                    extracted_data.append({
                        "Date": str(date_val).strip(),
                        "Description": desc,
                        "Amount": final_amount,
                        "cashback": final_cb_amount
                    })

    return pd.DataFrame(extracted_data)

if __name__ == "__main__":
    df = parse_axis_final("./Cards/25-12Dec-Axis.pdf")
    print(f"\n✅ Total Transactions Extracted: {len(df)}")
    if not df.empty:
        print(df)
        df.to_csv("Axis_Final_Parsed.csv", index=False)
    else:
        print("❌ Still found 0 transactions. Check the table iteration logic.")
