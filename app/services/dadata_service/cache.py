import re


def normalize_inn(value: str) -> str:
    return "".join(ch for ch in str(value) if ch.isdigit())


def normalize_name(value: str) -> str:
    value = str(value).strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def detect_query_type(value: str) -> str:
    inn = normalize_inn(value)
    if len(inn) in (10, 12) and inn == value.strip():
        return "inn"
    if len(inn) in (10, 12):
        return "inn"
    return "name"


def normalize_query(value: str) -> tuple[str, str]:
    query_type = detect_query_type(value)
    if query_type == "inn":
        return query_type, normalize_inn(value)
    return query_type, normalize_name(value)