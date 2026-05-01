import re
import petrovna
from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class BatchInputRow:
    row_number: int
    source_col_1: Optional[str]
    source_col_2: Optional[str]
    source_col_3: Optional[str]
    detected_inn: Optional[str]
    detected_ogrn: Optional[str]
    detected_name: Optional[str]


def normalize_cell(value) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()

def sanitize_org_name(value: str) -> str:
    s = str(value or "").strip()
    if not s:
        return ""
    s = s.replace("«", '"').replace("»", '"')
    s = re.sub(r"[\r\n\t]+", " ", s)
    s = re.sub(r"""[()"'\[\]{}<>\\/|`~^]+""", " ", s)
    s = s.replace("_", " ")
    s = re.sub(r"[^\w\s\-\.,№]+", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_digits(value: str) -> str:
    return "".join(ch for ch in str(value) if ch.isdigit())


def looks_like_inn(value: str) -> bool:
    digits = extract_digits(value)
    if len(digits) not in (10, 12):
        return False
    return bool(petrovna.validate_inn(digits))

def looks_like_ogrn(value: str) -> bool:
    digits = extract_digits(value)
    if len(digits) == 13:
        return bool(petrovna.validate_ogrn(digits))
    if len(digits) == 15:
        return bool(petrovna.validate_ogrnip(digits))
    return False


def parse_input_excel(file_path: str) -> list[BatchInputRow]:
    df = pd.read_excel(file_path, dtype=str)

    if df.shape[1] < 1:
        return []

    rows: list[BatchInputRow] = []

    for idx, row in df.iterrows():
        values = [normalize_cell(v) for v in row.tolist()]
        values = values[:3]
        while len(values) < 3:
            values.append("")

        col1, col2, col3 = values[0], values[1], values[2]

        detected_inn = None
        detected_ogrn = None
        detected_name = None

        for value in (col1, col2, col3):
            if not value:
                continue

            if detected_inn is None and looks_like_inn(value):
                detected_inn = extract_digits(value)
                continue

            if detected_ogrn is None and looks_like_ogrn(value):
                detected_ogrn = extract_digits(value)
                continue

            if detected_name is None:
                cleaned = sanitize_org_name(value)
                detected_name = cleaned or None

        rows.append(
            BatchInputRow(
                row_number=idx + 2,  # excel row number if first row is header
                source_col_1=col1 or None,
                source_col_2=col2 or None,
                source_col_3=col3 or None,
                detected_inn=detected_inn,
                detected_ogrn=detected_ogrn,
                detected_name=detected_name,
            )
        )

    return rows