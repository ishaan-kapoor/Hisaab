import pdfplumber
import pandas as pd
import re
import sys

def clean_description(desc):
    STOP_PATTERNS = [
        r"For further information.*",
        r"ask iPal.*",
        r"contact our Customer Care.*",
        r"IMPORTANT MESSAGES.*",
        r"Safe Banking Tips.*",
        r"Our registered office address.*",
        r"Page \d+ of \d+.*",
        r"CIN No\..*"
    ]
    for pattern in STOP_PATTERNS:
        desc = re.sub(pattern, "", desc, flags=re.IGNORECASE | re.DOTALL).strip()
    return desc

def parse_icici_final(pdf_path):
    print(f"🚀 Processing: {pdf_path}")
    extracted_data = []
    date_pattern = re.compile(r'(\d{2}/\d{2}/\d{4})')
    
    with pdfplumber.open(pdf_path) as pdf:
        # Focusing on the main transaction page
        page = pdf.pages[0]
        words = page.extract_words(use_text_flow=True)
        
        # Group by vertical position
        lines = {}
        for w in words:
            # COORDINATE FILTER: Your table starts at 207.8. 
            # Setting threshold to 200 safely ignores the 96% and 4% labels.
            # 1. Find the horizontal position (x0) of the 'Date' header
            date_header = next((w for w in words if w['text'] == "Date"), None)
            table_left_boundary = date_header['x0'] - 5 if date_header else 200

            # 2. Use that boundary for filtering
            if w['x0'] < table_left_boundary: continue
                
            top = round(w['top'], 1)
            lines.setdefault(top, []).append(w)
            
        sorted_tops = sorted(lines.keys())
        current_txn = None
        
        for top in sorted_tops:
            line_text = " ".join([w['text'] for w in sorted(lines[top], key=lambda x: x['x0'])])
            date_match = date_pattern.search(line_text)
            
            if date_match:
                if current_txn:
                    # Apply footer cleaning before saving the finished transaction
                    current_txn["Description"] = clean_description(current_txn["Description"])
                    extracted_data.append(current_txn)
                
                date = date_match.group(1)
                
                # 1. Capture Amount
                amt_match = re.search(r'([\d,]+\.\d{2}(\s*(?:CR|Cr|Dr))?)$', line_text)
                amount = 0.0
                amt_str_full = ""
                if amt_match:
                    amt_str_full = amt_match.group(1)
                    is_credit = "CR" in amt_str_full.upper()
                    amount = float(re.sub(r'[^\d\.]', '', amt_str_full))
                    if not is_credit: amount = -amount
                
                # 2. Extract Reward Points (usually digits right before the amount)
                # We look at the end of the line, excluding the amount we just found
                pre_amt_text = line_text.replace(amt_str_full, "").strip()
                points_match = re.search(r'(\d+)$', pre_amt_text)
                points = points_match.group(1) if points_match else "0"
                
                # 3. Clean up Middle (RefNo + Description)
                middle = pre_amt_text
                if points_match:
                    # Remove points from the end of the middle section
                    middle = middle[:points_match.start()].strip()
                
                middle = middle.replace(date, "").strip()
                ref_match = re.search(r'^(\d+)', middle)
                ref_no = ref_match.group(1) if ref_match else ""
                desc = middle[len(ref_no):].strip()

                current_txn = {
                    "Date": date,
                    "RefNo": ref_no,
                    "Description": desc,
                    "RewardPoints": points,
                    "Amount": amount
                }
            elif current_txn and len(line_text) > 2:
                # Handle multi-line descriptions (like Rentomojo's "IN")
                if "International" not in line_text and "Points" not in line_text:
                    current_txn["Description"] += " " + line_text.strip()

    if current_txn:
        STOP_PATTERNS = [
            r"For further information.*",
            r"ask iPal.*",
            r"contact our Customer Care.*",
            r"International Spends.*",
            r"Points.*",
            r"T&C.*"
        ]

        # Apply it to your description
        for pattern in STOP_PATTERNS:
            current_txn["Description"] = re.sub(pattern, "", current_txn["Description"], flags=re.IGNORECASE).strip()
        extracted_data.append(current_txn)

    return pd.DataFrame(extracted_data)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        df = parse_icici_final(sys.argv[1])
        if not df.empty:
            print(f"✅ Extracted {len(df)} transactions")
            # Filter out bank fees for personal spending analysis if desired
            print(df)
            # df.to_csv("master_parsed.csv", index=False)
        else:
            print("❌ Error: No transactions detected.")
