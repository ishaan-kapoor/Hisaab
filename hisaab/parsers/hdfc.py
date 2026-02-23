import re

import pandas as pd
import pdfplumber

from hisaab.parsers.base import StatementParser


class HDFCParser(StatementParser):

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

                for table in tables:
                    if not table or not table[0]:
                        continue

                    header_row = [str(c).replace('\n', ' ').strip() for c in table[0]]
                    header_str = " ".join(header_row).lower()

                    if "date" not in header_str or "description" not in header_str:
                        continue

                    for row in table[1:]:
                        if not row or not row[0]:
                            continue

                        raw_col0 = str(row[0]).replace('\n', ' ').strip()
                        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', raw_col0)
                        if not date_match:
                            continue
                        date = date_match.group(1)

                        if "|" in raw_col0:
                            parts = raw_col0.split('|')
                            if len(parts) > 1:
                                temp_desc = re.sub(r'\s*\d{2}:\d{2}\s*', '', parts[1]).strip()
                                desc_part1 = temp_desc
                            else:
                                desc_part1 = raw_col0
                        else:
                            desc_part1 = raw_col0.replace(date, "").strip()

                        desc_part2 = (
                            str(row[1]).replace('\n', ' ').strip()
                            if len(row) > 1 and row[1] else ""
                        )
                        full_desc = f"{desc_part1} {desc_part2}".strip()

                        neu_coins = 0.0
                        coin_match = re.search(r'\+\s*(\d+(\.\d+)?)', full_desc)
                        if coin_match:
                            neu_coins = float(coin_match.group(1))

                        amount = 0.0
                        found_amount = False

                        for col in reversed(row):
                            if not col:
                                continue
                            clean_col = str(col).replace(',', '').strip()
                            clean_col_numeric = re.sub(r'[^\d\.\w\s]', '', clean_col)
                            amt_match = re.search(r'(\d+\.\d{2})', clean_col_numeric)
                            if amt_match:
                                val = float(amt_match.group(1))
                                is_credit = "cr" in clean_col.lower()
                                amount = val if is_credit else -val
                                found_amount = True
                                break

                        if not found_amount:
                            continue

                        amt_str = f"{abs(amount):,.2f}"
                        full_desc = full_desc.replace(amt_str, "")
                        if coin_match:
                            full_desc = full_desc.replace(coin_match.group(0), "")

                        full_desc = full_desc.strip()
                        while len(full_desc) > 0:
                            if full_desc.upper().endswith(" CR") or full_desc.upper().endswith(" DR"):
                                full_desc = full_desc[:-3].strip()
                                continue
                            if full_desc[-1] in ['C', 'l', '|', '\u20b9', '.', ' ', '-', ':', 'Cr', 'Dr']:
                                full_desc = full_desc[:-1].strip()
                            else:
                                break

                        extracted_data.append({
                            "Date": date,
                            "Description": full_desc.strip(),
                            "RewardPoints": neu_coins,
                            "Amount": amount,
                        })

        return self.validate(pd.DataFrame(extracted_data))
