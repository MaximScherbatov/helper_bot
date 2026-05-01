import re


def normalize_inn(value: str) -> str:
    return "".join(ch for ch in str(value) if ch.isdigit())


def normalize_name(value: str) -> str:
    value = str(value or "").strip().lower()
    if not value:
        return ""
    value = re.sub(r"[\r\n\t]+", " ", value) # управляющие символы -> пробел
    value = value.replace("«", '"').replace("»", '"') # типографские кавычки -> обычные
    value = re.sub(r"""[()"'\[\]{}<>\\/|`~^]+""", " ", value) # символы, которые часто вызывают проблемы при дальнейшей обработке/логировании/URL/и т.д.
    value = value.replace("_", " ") # подчёркивание тоже лучше убрать
    value = re.sub(r"[^\w\s\-\.,№]+", " ", value, flags=re.UNICODE) # убираем прочие странные знаки, оставляя буквы/цифры/пробел/дефис/точку/запятую/№
    value = re.sub(r"\s+", " ", value).strip() # схлопываем пробелы
    return value


def detect_query_type(value: str) -> str:
    inn = normalize_inn(value)
    if len(inn) in (10, 12, 13, 15):  # + ОГРН и ОГРНИП
        return "inn"
    return "name"


def normalize_query(value: str) -> tuple[str, str]:
    query_type = detect_query_type(value)
    if query_type == "inn":
        return query_type, normalize_inn(value)
    return query_type, normalize_name(value)