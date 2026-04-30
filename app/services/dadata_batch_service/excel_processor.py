from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class BatchInputRow:
    row_number: int
    source_col_1: Optional[str]
    source_col_2: Optional[str]
    detected_inn: Optional[str]
    detected_name: Optional[str]


def normalize_cell(value) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def extract_digits(value: str) -> str:
    return "".join(ch for ch in str(value) if ch.isdigit())


def looks_like_inn(value: str) -> bool:
    digits = extract_digits(value)
    return len(digits) in (10, 12)


def parse_input_excel(file_path: str) -> list[BatchInputRow]:
    df = pd.read_excel(file_path, dtype=str)

    if df.shape[1] < 1:
        return []

    rows: list[BatchInputRow] = []

    for idx, row in df.iterrows():
        values = [normalize_cell(v) for v in row.tolist()]
        values = values[:2] if len(values) >= 2 else values + [""]

        col1 = values[0] if len(values) > 0 else ""
        col2 = values[1] if len(values) > 1 else ""

        detected_inn = None
        detected_name = None

        for value in [col1, col2]:
            if not value:
                continue

            if looks_like_inn(value) and detected_inn is None:
                detected_inn = extract_digits(value)
            elif detected_name is None:
                detected_name = value

        rows.append(
            BatchInputRow(
                row_number=idx + 2,  # excel row number if first row is header
                source_col_1=col1 or None,
                source_col_2=col2 or None,
                detected_inn=detected_inn,
                detected_name=detected_name,
            )
        )

    return rows