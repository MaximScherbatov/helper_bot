# app/utils/okved.py
from __future__ import annotations

import logging
import os
import re
from functools import lru_cache

import pandas as pd

from app.config import get_settings

logger = logging.getLogger(__name__)


def _norm_okved(code: str | None) -> str | None:
    if not code:
        return None
    s = str(code).strip()
    if not s:
        return None
    # убираем всё кроме цифр
    digits = re.sub(r"\D+", "", s)
    return digits or None


@lru_cache(maxsize=1)
def load_okved_dict() -> dict[str, str]:
    """
    Загружает справочник ОКВЭД из Excel.
    Ожидается, что в файле есть либо колонки:
      - code / name
    либо первые две колонки: (код, описание).
    """
    settings = get_settings()
    path = settings.okved_dict_xlsx_path

    if not path:
        logger.warning("OKVED dict path is empty; okved descriptions disabled")
        return {}

    if not os.path.exists(path):
        logger.warning("OKVED dict file not found: %s; okved descriptions disabled", path)
        return {}

    try:
        df = pd.read_excel(path, dtype=str)
        if df.empty:
            return {}

        cols = [c.strip().lower() for c in df.columns.tolist()]
        df.columns = cols

        if "code" in cols and "name" in cols:
            code_col, name_col = "code", "name"
        else:
            # fallback: первые 2 колонки
            code_col = df.columns[0]
            name_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

        mapping: dict[str, str] = {}
        for _, row in df.iterrows():
            code = _norm_okved(row.get(code_col))
            name = str(row.get(name_col) or "").strip()
            if code and name:
                mapping[code] = name

        logger.info("OKVED dict loaded: %d items from %s", len(mapping), path)
        return mapping

    except Exception:
        logger.exception("Failed to load OKVED dict from %s", path)
        return {}


def okved_description(okved_code: str | None) -> str | None:
    """
    Возвращает описание ОКВЭД по коду.
    """
    code = _norm_okved(okved_code)
    if not code:
        return None
    mapping = load_okved_dict()
    return mapping.get(code)