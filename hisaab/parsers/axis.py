import re

import pandas as pd
import pdfplumber

from hisaab.parsers.base import StatementParser


class AxisParser(StatementParser):

    def parse(self, file_path: str) -> pd.DataFrame:
        extracted_data = []

        try:
            pdf = pdfplumber.open(file_path)
        except Exception:
            return self.validate(pd.DataFrame(columns=["Date", "Description", "Amount"]))

        with pdf:
            for page in pdf.pages:
                tables = page.extract_tables({
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 4,
                })

                for t_idx, table in enumerate(tables):
                    header_idx = -1
                    col_map = {}

                    for i, row in enumerate(table):
                        row_str = [str(c).lower().replace('\n', ' ') for c in row if c]
                        full_text = " ".join(row_str)

                        if "date" in full_text and "transaction details" in full_text:
                            header_idx = i
                            for col_i, cell in enumerate(row):
                                val = str(cell).lower()
                                if "date" in val:
                                    col_map['date'] = col_i
                                elif "transaction details" in val:
                                    col_map['desc'] = col_i
                                elif "amount" in val:
                                    col_map['amount'] = col_i
                                elif "cashback earned" in val:
                                    col_map['cashback'] = col_i
                            break

                    if header_idx == -1:
                        continue

                    for row in table[header_idx + 1:]:
                        if len(row) < 2:
                            continue

                        date_idx = col_map.get('date', 0)
                        date_val = row[date_idx]
                        if not date_val or not re.match(
                            r'\d{2}/\d{2}/\d{4}', str(date_val).strip()
                        ):
                            continue

                        amt_idx = col_map.get('amount', -2)
                        raw_amt = str(row[amt_idx]).replace(',', '').strip()
                        is_credit = "cr" in raw_amt.lower()
                        amt_match = re.search(r'([\d\.]+)', raw_amt)
                        if not amt_match:
                            continue

                        amount = float(amt_match.group(1))
                        final_amount = amount if is_credit else -amount

                        desc_idx = col_map.get('desc', 1)
                        desc = str(row[desc_idx]).replace('\n', ' ').strip()

                        cb_idx = col_map.get('cashback', -1)
                        raw_cashback = str(row[cb_idx]).replace('\n', ' ').strip() if cb_idx >= 0 else "0"
                        cb_match = re.search(r'([\d\.]+)', raw_cashback)
                        cb_amount = float(cb_match.group(1)) if cb_match else 0.0

                        extracted_data.append({
                            "Date": str(date_val).strip(),
                            "Description": desc,
                            "Amount": final_amount,
                            "RewardPoints": cb_amount,
                        })

        return self.validate(pd.DataFrame(extracted_data))
