import re

import pandas as pd
import pdfplumber

from hisaab.parsers.base import StatementParser


def clean_description(desc):
    STOP_PATTERNS = [
        r"For further information.*",
        r"ask iPal.*",
        r"contact our Customer Care.*",
        r"IMPORTANT MESSAGES.*",
        r"Safe Banking Tips.*",
        r"Our registered office address.*",
        r"Page \d+ of \d+.*",
        r"CIN No\..*",
    ]
    for pattern in STOP_PATTERNS:
        desc = re.sub(pattern, "", desc, flags=re.IGNORECASE | re.DOTALL).strip()
    return desc


class ICICIParser(StatementParser):

    def parse(self, file_path: str) -> pd.DataFrame:
        extracted_data = []
        date_pattern = re.compile(r'(\d{2}/\d{2}/\d{4})')

        try:
            pdf = pdfplumber.open(file_path)
        except Exception:
            return self.validate(pd.DataFrame(columns=["Date", "Description", "Amount"]))

        with pdf:
            page = pdf.pages[0]
            words = page.extract_words(use_text_flow=True)

            lines = {}
            for w in words:
                date_header = next((w2 for w2 in words if w2['text'] == "Date"), None)
                table_left_boundary = date_header['x0'] - 5 if date_header else 200
                if w['x0'] < table_left_boundary:
                    continue
                top = round(w['top'], 1)
                lines.setdefault(top, []).append(w)

            sorted_tops = sorted(lines.keys())
            current_txn = None

            for top in sorted_tops:
                line_text = " ".join(
                    [w['text'] for w in sorted(lines[top], key=lambda x: x['x0'])]
                )
                date_match = date_pattern.search(line_text)

                if date_match:
                    if current_txn:
                        current_txn["Description"] = clean_description(current_txn["Description"])
                        extracted_data.append(current_txn)

                    date = date_match.group(1)

                    amt_match = re.search(r'([\d,]+\.\d{2}(\s*(?:CR|Cr|Dr))?)$', line_text)
                    amount = 0.0
                    amt_str_full = ""
                    if amt_match:
                        amt_str_full = amt_match.group(1)
                        is_credit = "CR" in amt_str_full.upper()
                        amount = float(re.sub(r'[^\d\.]', '', amt_str_full))
                        if not is_credit:
                            amount = -amount

                    pre_amt_text = line_text.replace(amt_str_full, "").strip()
                    points_match = re.search(r'(\d+)$', pre_amt_text)
                    points = points_match.group(1) if points_match else "0"

                    middle = pre_amt_text
                    if points_match:
                        middle = middle[:points_match.start()].strip()

                    middle = middle.replace(date, "").strip()
                    ref_match = re.search(r'^(\d+)', middle)
                    ref_no = ref_match.group(1) if ref_match else None
                    desc = middle[len(ref_no or ""):].strip()

                    current_txn = {
                        "Date": date,
                        "RefNo": ref_no,
                        "Description": desc,
                        "RewardPoints": int(points),
                        "Amount": amount,
                    }
                elif current_txn and len(line_text) > 2:
                    if "International" not in line_text and "Points" not in line_text:
                        current_txn["Description"] += " " + line_text.strip()

            if current_txn:
                STOP_PATTERNS = [
                    r"For further information.*",
                    r"ask iPal.*",
                    r"contact our Customer Care.*",
                    r"International Spends.*",
                    r"Points.*",
                    r"T&C.*",
                ]
                for pattern in STOP_PATTERNS:
                    current_txn["Description"] = re.sub(
                        pattern, "", current_txn["Description"], flags=re.IGNORECASE
                    ).strip()
                extracted_data.append(current_txn)

        return self.validate(pd.DataFrame(extracted_data))
