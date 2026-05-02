from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Optional

import pandas as pd

from app.db.session import SessionLocal
from app.repositories.dadata import DaDataRepository
from app.services.dadata_service.cache import normalize_query
from app.services.dadata_service.client import DaDataClient
from app.services.dadata_service.key_manager import DaDataKeyManager
from app.services.dadata_batch_service.excel_processor import BatchInputRow, parse_input_excel
from app.utils.okved import okved_description

@dataclass
class BatchEstimate:
    total_rows: int
    unique_queries: int
    cache_hits: int
    required_api_calls: int
    available_tokens: int
    enough_tokens: bool


class DaDataBatchProcessor:
    OUTPUT_COLUMNS = [
        "Строка",
        "Исходное_значение_1",
        "Исходное_значение_2",
        "Исходное_значение_3",
        "ИНН",
        "КПП",
        "ОГРН",
        "Полное_наименование",
        "Краткое_наименование",
        "Статус_организации",
        "Дата_регистрации",
        "Дата_ликвидации",
        "Адрес",
        "Индекс",
        "Руководитель",
        "Должность",
        "ОКВЭД",
        "ОКВЭД_описание",
        "Москва_флаг",
        "Ошибка",
    ]

    def estimate_file(self, file_path: str) -> BatchEstimate:
        rows = parse_input_excel(file_path)

        queries = []
        for row in rows:
            query_value = row.detected_inn or row.detected_ogrn or row.detected_name
            if not query_value:
                continue

            digits = "".join(ch for ch in str(query_value) if ch.isdigit())
            has_letters = any(ch.isalpha() for ch in str(query_value))
            if (not has_letters) and digits:
                # цифры без букв должны быть ИНН/ОГРН/ОГРНИП по длине, иначе считаем ошибочным вводом
                if len(digits) not in (10, 12, 13, 15):
                    continue

            query_type, normalized_query = normalize_query(query_value)
            queries.append((query_type, normalized_query))

        unique_queries = list(set(queries))

        with SessionLocal() as session:
            repo = DaDataRepository(session)

            cache_hits = 0
            for query_type, normalized_query in unique_queries:
                if repo.get_cache(query_type, normalized_query) is not None:
                    cache_hits += 1

            available_tokens = 0
            keys = repo.get_active_keys()
            for key in keys:
                # reset done inside repository get_first_available_key usually,
                # but for estimate we count current state as-is
                available_tokens += max(0, key.daily_limit - key.used_today)

        required_api_calls = max(0, len(unique_queries) - cache_hits)

        return BatchEstimate(
            total_rows=len(rows),
            unique_queries=len(unique_queries),
            cache_hits=cache_hits,
            required_api_calls=required_api_calls,
            available_tokens=available_tokens,
            enough_tokens=available_tokens >= required_api_calls,
        )

    def process_file(self, file_path: str, output_path: str, task_callback=None) -> dict:
        rows = parse_input_excel(file_path)

        with SessionLocal() as session:
            repo = DaDataRepository(session)
            key_manager = DaDataKeyManager(repo)
            client = DaDataClient()

            result_rows = []
            total = len(rows)

            for idx, row in enumerate(rows, start=1):
                if task_callback:
                    task_callback(
                        current=idx,
                        total=total,
                        message=f"Обработка строки {idx} из {total}",
                    )

                try:
                    result_rows.append(
                        self._process_one_row(
                            row=row,
                            repo=repo,
                            key_manager=key_manager,
                            client=client,
                        )
                    )
                except Exception as e:
                    result_rows.append(
                        {
                            "Строка": getattr(row, "row_number", None),
                            "Исходное_значение_1": getattr(row, "source_col_1", None),
                            "Исходное_значение_2": getattr(row, "source_col_2", None),
                            "Исходное_значение_3": getattr(row, "source_col_3", None),
                            "ИНН": None,
                            "КПП": None,
                            "ОГРН": None,
                            "Полное_наименование": None,
                            "Краткое_наименование": None,
                            "Статус_организации": None,
                            "Дата_регистрации": None,
                            "Дата_ликвидации": None,
                            "Адрес": None,
                            "Индекс": None,
                            "Руководитель": None,
                            "Должность": None,
                            "ОКВЭД": None,
                            "ОКВЭД_описание": None,
                            "Москва_флаг": None,
                            "Ошибка": f"Unhandled row error: {str(e)[:500]}",
                        }
                    )

        df = pd.DataFrame(result_rows, columns=self.OUTPUT_COLUMNS)
        df.to_excel(output_path, index=False)

        return {
            "total_rows": len(rows),
            "output_path": output_path,
        }

    def _process_one_row(self, row: BatchInputRow, repo: DaDataRepository, key_manager: DaDataKeyManager, client: DaDataClient) -> dict:
        base = {
            "Строка": row.row_number,
            "Исходное_значение_1": row.source_col_1,
            "Исходное_значение_2": row.source_col_2,
            "Исходное_значение_3": row.source_col_3,
            "ИНН": None,
            "КПП": None,
            "ОГРН": None,
            "Полное_наименование": None,
            "Краткое_наименование": None,
            "Статус_организации": None,
            "Дата_регистрации": None,
            "Дата_ликвидации": None,
            "Адрес": None,
            "Индекс": None,
            "Руководитель": None,
            "Должность": None,
            "ОКВЭД": None,
            "ОКВЭД_описание": None,
            "Москва_флаг": None,
            "Ошибка": None,
        }
        
        query_value = row.detected_inn or row.detected_ogrn or row.detected_name
        digits = "".join(ch for ch in str(query_value) if ch.isdigit())
        has_letters = any(ch.isalpha() for ch in str(query_value))

        if (not has_letters) and digits:
            if len(digits) not in (10, 12, 13, 15):
                base["Ошибка"] = "Некорректный идентификатор (ожидался ИНН 10/12, ОГРН 13 или ОГРНИП 15 цифр)"
                return base

        if not query_value:
            base["Ошибка"] = "Не найден ИНН/ОГРН или наименование"
            return base

        query_type, normalized_query = normalize_query(query_value)
        if not normalized_query:
            base["Ошибка"] = "Пустой запрос после очистки"
            return base

        if query_type == "name" and len(normalized_query) < 3:
            base["Ошибка"] = "Слишком короткое наименование для поиска"
            return base

        cached = repo.get_cache(query_type, normalized_query)
        response_json = None

        if cached is not None:
            response_json = cached.response_json
            repo.log_usage(
                query_type=query_type,
                query_value=query_value,
                normalized_query=normalized_query,
                status="cache",
                api_key_id=cached.source_key_id,
            )
        else:
            api_key_row = key_manager.get_available_key()
            if api_key_row is None:
                base["Ошибка"] = "Нет доступных API-ключей DaData"
                return base

            try:
                count = 20 if query_type == "name" else 1
                response_json = client.suggest_party(
                    api_key=api_key_row.api_key,
                    query=normalized_query,
                    count=count,
                )
                key_manager.mark_success_usage(api_key_row.id)

                ttl_days = 30 if query_type == "inn" else 7
                repo.upsert_cache(
                    query_type=query_type,
                    query_value=query_value,
                    normalized_query=normalized_query,
                    response_json=response_json,
                    source_key_id=api_key_row.id,
                    expires_at=datetime.utcnow() + timedelta(days=ttl_days),
                )

                repo.log_usage(
                    query_type=query_type,
                    query_value=query_value,
                    normalized_query=normalized_query,
                    status="success",
                    api_key_id=api_key_row.id,
                )
            except Exception as e:
                base["Ошибка"] = str(e)[:500]
                repo.log_usage(
                    query_type=query_type,
                    query_value=query_value,
                    normalized_query=normalized_query,
                    status="error",
                    error_text=str(e)[:500],
                )
                return base

        suggestions = response_json.get("suggestions", []) if response_json else []
        if not suggestions:
            base["Ошибка"] = "Ничего не найдено"
            return base

        selected = self._select_best_suggestion(suggestions, query_type)
        if selected is None:
            base["Ошибка"] = "Ничего не найдено"
            return base

        try:
            data = (selected.get("data") or {}) if isinstance(selected, dict) else {}

            name_data = data.get("name") or {}
            address_data = data.get("address") or {}
            management_data = data.get("management") or {}
            state_data = data.get("state") or {}

            address_inner = address_data.get("data") or {} 

            base["ИНН"] = data.get("inn")
            base["КПП"] = data.get("kpp")
            base["ОГРН"] = data.get("ogrn")
            base["Полное_наименование"] = name_data.get("full_with_opf")
            base["Краткое_наименование"] = name_data.get("short_with_opf")
            base["Статус_организации"] = self._format_status(state_data.get("status"))
            base["Дата_регистрации"] = self._format_timestamp_ms(state_data.get("registration_date"))
            base["Дата_ликвидации"] = self._format_timestamp_ms(state_data.get("liquidation_date"))
            base["Адрес"] = address_data.get("value")
            base["Индекс"] = address_inner.get("postal_code")
            base["Руководитель"] = self._format_management_names(management_data)
            base["Должность"] = management_data.get("post")
            base["ОКВЭД"] = data.get("okved")
            base["ОКВЭД_описание"] = okved_description(base["ОКВЭД"])
            base["Москва_флаг"] = "Да" if self._is_moscow_candidate(selected) else "Нет"

            return base

        except Exception as e:
            base["Ошибка"] = f"Row parse error: {str(e)[:500]}"
            return base

    def _select_best_suggestion(self, suggestions: list[dict], query_type: str) -> Optional[dict]:
        if not suggestions:
            return None

        if query_type == "inn":
            return suggestions[0]

        # Для наименований: сначала ищем московские
        moscow_candidates = [item for item in suggestions if self._is_moscow_candidate(item)]
        if moscow_candidates:
            return moscow_candidates[0]

        return suggestions[0]

    def _is_moscow_candidate(self, suggestion: dict) -> bool:
        data = suggestion.get("data", {})
        address_data = data.get("address", {}).get("data", {}) if data else {}

        inn = str(data.get("inn", "") or "")
        region = str(address_data.get("region", "") or "").lower()
        city = str(address_data.get("city", "") or "").lower()
        area = str(address_data.get("area", "") or "").lower()

        if inn.startswith("77"):
            return True

        if "москва" in region or city == "москва" or "москва" in area:
            return True

        return False

    def _format_timestamp_ms(self, value: Any) -> Optional[str]:
        if value in (None, "", "None"):
            return None
        try:
            value_int = int(value)
            if value_int <= 0:
                return None
            dt = datetime.utcfromtimestamp(value_int / 1000)
            return dt.strftime("%d.%m.%Y")
        except Exception:
            return str(value)

    def _format_status(self, value: Any) -> Optional[str]:
        mapping = {
            "ACTIVE": "Действующая",
            "LIQUIDATING": "В процессе ликвидации",
            "LIQUIDATED": "Ликвидирована",
            "BANKRUPT": "Банкротство",
            "REORGANIZING": "В процессе реорганизации",
        }
        if value is None:
            return None
        value = str(value)
        return mapping.get(value, value)

    def _format_management_names(self, management_data: Any) -> Optional[str]:
        if management_data is None:
            return None

        if isinstance(management_data, dict):
            name = management_data.get("name")
            if isinstance(name, list):
                values = [str(x).strip() for x in name if str(x).strip()]
                return ", ".join(values) if values else None
            if isinstance(name, str):
                return name.strip() or None

        if isinstance(management_data, list):
            names = []
            for item in management_data:
                if isinstance(item, dict):
                    val = str(item.get("name", "")).strip()
                    if val:
                        names.append(val)
                else:
                    val = str(item).strip()
                    if val:
                        names.append(val)
            return ", ".join(names) if names else None

        return str(management_data).strip() or None