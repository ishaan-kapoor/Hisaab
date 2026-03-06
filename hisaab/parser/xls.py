from datetime import datetime

import pandas as pd

from hisaab.parsers.base import StatementParser


def _parse_amount(val) -> float:
    if pd.isna(val) or str(val).strip() in ('', 'nan', 'NaN', '-', 'None'):
        return 0.0
    try:
        return float(str(val).replace(',', '').strip())
    except ValueError:
        return 0.0


def _normalize_date(val) -> str:
    s = str(val).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d %b %Y', '%d-%b-%Y', '%d %B %Y'):
        try:
            return datetime.strptime(s, fmt).strftime('%d/%m/%Y')
        except ValueError:
            continue
    return s


def _find_col(cols: list[str], keyword: str) -> str | None:
    """Return first column name containing keyword (case-insensitive), or None."""
    for col in cols:
        if keyword.lower() in col.lower():
            return col
    return None


def _load_xls(file_path: str, key_cols: list[str]) -> pd.DataFrame:
    """Load XLS/XLSX, auto-detecting the header row by searching for key_cols."""
    raw = pd.read_excel(file_path, header=None, dtype=str)
    header_row: int = 0
    for i, row in raw.iterrows():
        vals = [str(v).strip().lower() for v in row]
        matches = sum(1 for k in key_cols if any(k.lower() in v for v in vals))
        if matches >= len(key_cols):
            header_row = int(i)  # type: ignore[arg-type]
            break
    df = pd.read_excel(file_path, header=header_row, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    return df


class _XLSParser(StatementParser):
    """Shared logic for debit/credit column XLS bank statements."""

    def _parse_xls(self, file_path: str, key_cols: list[str],
                   date_kw: str, desc_kw: str, dr_kw: str, cr_kw: str,
                   ref_kw: str = None) -> pd.DataFrame:
        try:
            df = _load_xls(file_path, key_cols)
        except Exception:
            return self.validate(pd.DataFrame(columns=["Date", "Description", "Amount"]))

        cols = list(df.columns)
        date_col = _find_col(cols, date_kw)
        desc_col = _find_col(cols, desc_kw)
        dr_col = _find_col(cols, dr_kw)
        cr_col = _find_col(cols, cr_kw)
        ref_col = _find_col(cols, ref_kw) if ref_kw else None

        if not all([date_col, desc_col, dr_col, cr_col]):
            return self.validate(pd.DataFrame(columns=["Date", "Description", "Amount"]))

        rows = []
        for _, row in df.iterrows():
            date_val = str(row.get(date_col, '')).strip()
            if not date_val or date_val.lower() in ('nan', 'none', ''):
                continue
            dr = _parse_amount(row.get(dr_col, 0))
            cr = _parse_amount(row.get(cr_col, 0))
            if dr == 0.0 and cr == 0.0:
                continue
            ref_no = str(row.get(ref_col, '')).strip() if ref_col else None
            if ref_no and ref_no.lower() in ('nan', 'none', '0', ''):
                ref_no = None
            rows.append({
                'Date': _normalize_date(date_val),
                'Description': str(row.get(desc_col, '')).strip(),
                'Amount': cr - dr,
                'RefNo': ref_no,
            })

        return self.validate(pd.DataFrame(rows))


class AxisXLSParser(_XLSParser):

    def parse(self, file_path: str) -> pd.DataFrame:
        return self._parse_xls(
            file_path,
            key_cols=['Tran Date', 'PARTICULARS', 'DR', 'CR'],
            date_kw='Tran Date',
            desc_kw='PARTICULARS',
            dr_kw='DR',
            cr_kw='CR',
            ref_kw='CHQNO',
        )


class ICICIXLSParser(_XLSParser):

    def parse(self, file_path: str) -> pd.DataFrame:
        return self._parse_xls(
            file_path,
            key_cols=['Transaction Date', 'Transaction Remarks', 'Withdrawal', 'Deposit'],
            date_kw='Transaction Date',
            desc_kw='Transaction Remarks',
            dr_kw='Withdrawal',
            cr_kw='Deposit',
            ref_kw='Cheque Number',
        )


class HDFCXLSParser(_XLSParser):

    def parse(self, file_path: str) -> pd.DataFrame:
        return self._parse_xls(
            file_path,
            key_cols=['Narration', 'Withdrawal Amt', 'Deposit Amt'],
            date_kw='Date',
            desc_kw='Narration',
            dr_kw='Withdrawal Amt',
            cr_kw='Deposit Amt',
            ref_kw='Chq',
        )

