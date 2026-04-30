from datetime import datetime, timedelta
from typing import Optional, Any

from messenger_bot_api.data_classes import InlineMessageButton
from messenger_bot_api.util import MessageRequest

from app.bot.context_manager import ContextManager
from app.db.session import SessionLocal
from app.repositories.dadata import DaDataRepository
from app.services.base import BaseService
from app.services.dadata_service.cache import normalize_query
from app.services.dadata_service.client import DaDataClient
from app.services.dadata_service.key_manager import DaDataKeyManager

from app.ui import texts, buttons
from app.ui.screens import (
    build_dadata_intro_screen,
    build_dadata_result_screen,
    build_dadata_variants_screen,
)

class DaDataService(BaseService):
    code = "dadata"
    name = "Проверка организаций"
    description = "Поиск организаций по ИНН или наименованию через DaData"

    PAGE_SIZE = 5

    def start(self, router, event, context: Optional[dict] = None) -> None:
        self._set_step(
            event=event,
            step="awaiting_query",
            context_data={},
        )
        event.reply_text(build_dadata_intro_screen())

    def handle_message(self, router, event, context: Optional[dict] = None) -> bool:
        query = (event.message_text or "").strip()
        if not query:
            event.reply_text(texts.DADATA_EMPTY_QUERY_TEXT)
            return True

        if not self._is_valid_query(query):
            event.reply_text(texts.DADATA_INVALID_QUERY_TEXT)
            return True

        query_type, normalized_query = normalize_query(query)

        with SessionLocal() as session:
            repo = DaDataRepository(session)
            key_manager = DaDataKeyManager(repo)
            client = DaDataClient()

            cached = repo.get_cache(query_type, normalized_query)
            if cached is not None:
                suggestions = cached.response_json.get("suggestions", [])

                # Для кэшированного name-search с несколькими вариантами снова показываем список
                if query_type == "name" and len(suggestions) > 1:
                    variants = self._build_sorted_variants(suggestions)

                    self._set_step(
                        event=event,
                        step="awaiting_selection",
                        context_data={
                            "last_query": query,
                            "query_type": query_type,
                            "normalized_query": normalized_query,
                            "variants": variants,
                            "page": 0,
                            "page_size": self.PAGE_SIZE,
                            "selected_index": None,
                        },
                    )

                    repo.log_usage(
                        query_type=query_type,
                        query_value=query,
                        normalized_query=normalized_query,
                        status="cache",
                        api_key_id=cached.source_key_id,
                    )

                    self._send_variants(event, variants, page=0)
                    return True

                self._set_step(
                    event=event,
                    step="awaiting_query",
                    context_data={
                        "last_query": query,
                        "query_type": query_type,
                        "normalized_query": normalized_query,
                        "last_response_json": cached.response_json,
                        "selected_index": 0,
                    },
                )
                repo.log_usage(
                    query_type=query_type,
                    query_value=query,
                    normalized_query=normalized_query,
                    status="cache",
                    api_key_id=cached.source_key_id,
                )
                self._send_result(
                    event,
                    cached.response_json,
                    from_cache=True,
                    variants=None,
                    selected_index=0,
                )
                return True

            api_key_row = key_manager.get_available_key()
            if api_key_row is None:
                repo.log_usage(
                    query_type=query_type,
                    query_value=query,
                    normalized_query=normalized_query,
                    status="error",
                    error_text="Нет доступных API-ключей DaData",
                )
                event.reply_text(texts.DADATA_NO_KEYS_TEXT)
                return True

            try:
                count = 20 if query_type == "name" else 1

                response_json = client.suggest_party(
                    api_key=api_key_row.api_key,
                    query=normalized_query,
                    count=count,
                )

                suggestions = response_json.get("suggestions", [])
                key_manager.mark_success_usage(api_key_row.id)

                if not suggestions:
                    repo.log_usage(
                        query_type=query_type,
                        query_value=query,
                        normalized_query=normalized_query,
                        status="no_results",
                        api_key_id=api_key_row.id,
                    )
                    event.reply_text(texts.DADATA_NOT_FOUND_TEXT)
                    return True

                ttl_days = 30 if query_type == "inn" else 7
                repo.upsert_cache(
                    query_type=query_type,
                    query_value=query,
                    normalized_query=normalized_query,
                    response_json=response_json,
                    source_key_id=api_key_row.id,
                    expires_at=datetime.utcnow() + timedelta(days=ttl_days),
                )

                repo.log_usage(
                    query_type=query_type,
                    query_value=query,
                    normalized_query=normalized_query,
                    status="success",
                    api_key_id=api_key_row.id,
                )

                if query_type == "inn":
                    self._set_step(
                        event=event,
                        step="awaiting_query",
                        context_data={
                            "last_query": query,
                            "query_type": query_type,
                            "normalized_query": normalized_query,
                            "last_response_json": response_json,
                            "selected_index": 0,
                        },
                    )
                    self._send_result(
                        event,
                        response_json,
                        from_cache=False,
                        variants=None,
                        selected_index=0,
                    )
                    return True

                # Для поиска по name сортируем все варианты по приоритету
                variants = self._build_sorted_variants(suggestions)

                if len(variants) == 1:
                    response_json = {"suggestions": [variants[0]["item"]]}
                    self._set_step(
                        event=event,
                        step="awaiting_query",
                        context_data={
                            "last_query": query,
                            "query_type": query_type,
                            "normalized_query": normalized_query,
                            "last_response_json": response_json,
                            "variants": variants,
                            "selected_index": 0,
                        },
                    )
                    self._send_result(
                        event,
                        response_json,
                        from_cache=False,
                        variants=variants,
                        selected_index=0,
                    )
                    return True

                self._set_step(
                    event=event,
                    step="awaiting_selection",
                    context_data={
                        "last_query": query,
                        "query_type": query_type,
                        "normalized_query": normalized_query,
                        "variants": variants,
                        "page": 0,
                        "page_size": self.PAGE_SIZE,
                        "selected_index": None,
                    },
                )

                self._send_variants(event, variants, page=0)
                return True

            except Exception as e:
                repo.log_usage(
                    query_type=query_type,
                    query_value=query,
                    normalized_query=normalized_query,
                    status="error",
                    api_key_id=api_key_row.id,
                    error_text=str(e)[:500],
                )
                event.reply_text(texts.DADATA_EXTERNAL_ERROR_TEXT)
                return True

    def handle_button(self, router, event, context: Optional[dict] = None) -> bool:
        callback_data = event.selected_button.callback_data if event.selected_button else None
        if not callback_data:
            return False

        context = context or {}

        if callback_data == "dadata:new_search":
            self._set_step(
                event=event,
                step="awaiting_query",
                context_data={},
            )
            event.reply_text(texts.DADATA_NEW_SEARCH_TEXT)
            return True

        if callback_data == "dadata:menu":
            self._clear_context(event)
            router.handle_menu(event)
            return True

        if callback_data == "dadata:next_page":
            variants = context.get("variants", [])
            page = int(context.get("page", 0)) + 1

            self._set_step(
                event=event,
                step="awaiting_selection",
                context_data={
                    "last_query": context.get("last_query"),
                    "query_type": context.get("query_type"),
                    "normalized_query": context.get("normalized_query"),
                    "variants": variants,
                    "page": page,
                    "page_size": context.get("page_size", self.PAGE_SIZE),
                    "selected_index": context.get("selected_index"),
                },
            )
            self._send_variants(event, variants, page=page)
            return True

        if callback_data == "dadata:prev_page":
            variants = context.get("variants", [])
            page = max(0, int(context.get("page", 0)) - 1)

            self._set_step(
                event=event,
                step="awaiting_selection",
                context_data={
                    "last_query": context.get("last_query"),
                    "query_type": context.get("query_type"),
                    "normalized_query": context.get("normalized_query"),
                    "variants": variants,
                    "page": page,
                    "page_size": context.get("page_size", self.PAGE_SIZE),
                    "selected_index": context.get("selected_index"),
                },
            )
            self._send_variants(event, variants, page=page)
            return True

        if callback_data == "dadata:card_next":
            variants = context.get("variants", [])
            selected_index = context.get("selected_index")
            if selected_index is None:
                event.reply_text(texts.DADATA_NO_ACTIVE_VARIANTS_TEXT)
                return True

            next_index = selected_index + 1
            if next_index >= len(variants):
                event.reply_text(texts.DADATA_LAST_VARIANT_TEXT)
                return True

            selected_item = variants[next_index]["item"]
            response_json = {"suggestions": [selected_item]}

            self._set_step(
                event=event,
                step="awaiting_query",
                context_data={
                    "last_query": context.get("last_query"),
                    "query_type": "name",
                    "normalized_query": context.get("normalized_query"),
                    "last_response_json": response_json,
                    "variants": variants,
                    "selected_index": next_index,
                },
            )

            self._send_result(
                event,
                response_json,
                from_cache=False,
                variants=variants,
                selected_index=next_index,
            )
            return True

        if callback_data == "dadata:card_prev":
            variants = context.get("variants", [])
            selected_index = context.get("selected_index")
            if selected_index is None:
                event.reply_text(texts.DADATA_NO_ACTIVE_VARIANTS_TEXT)
                return True

            prev_index = selected_index - 1
            if prev_index < 0:
                event.reply_text(texts.DADATA_FIRST_VARIANT_TEXT)
                return True

            selected_item = variants[prev_index]["item"]
            response_json = {"suggestions": [selected_item]}

            self._set_step(
                event=event,
                step="awaiting_query",
                context_data={
                    "last_query": context.get("last_query"),
                    "query_type": "name",
                    "normalized_query": context.get("normalized_query"),
                    "last_response_json": response_json,
                    "variants": variants,
                    "selected_index": prev_index,
                },
            )

            self._send_result(
                event,
                response_json,
                from_cache=False,
                variants=variants,
                selected_index=prev_index,
            )
            return True

        if callback_data.startswith("dadata:select:"):
            idx_str = callback_data.split(":")[-1]
            if not idx_str.isdigit():
                event.reply_text(texts.DADATA_INVALID_SELECTION_TEXT)
                return True

            idx = int(idx_str)
            variants = context.get("variants", [])
            if idx < 0 or idx >= len(variants):
                event.reply_text(texts.DADATA_SELECTION_NOT_FOUND_TEXT)
                return True

            selected_item = variants[idx]["item"]
            response_json = {"suggestions": [selected_item]}

            self._set_step(
                event=event,
                step="awaiting_query",
                context_data={
                    "last_query": context.get("last_query"),
                    "query_type": "name",
                    "normalized_query": context.get("normalized_query"),
                    "last_response_json": response_json,
                    "variants": variants,
                    "selected_index": idx,
                },
            )

            self._send_result(
                event,
                response_json,
                from_cache=False,
                variants=variants,
                selected_index=idx,
            )
            return True

        return False

    def resume(self, router, event, context: Optional[dict] = None) -> None:
        context = context or {}
        step = context.get("step")

        if step == "awaiting_selection":
            variants = context.get("variants", [])
            page = int(context.get("page", 0))
            if variants:
                self._send_variants(event, variants, page=page)
                return

        event.reply_text(texts.DADATA_RESUME_TEXT)

    def _set_step(self, event, step: str, context_data: dict):
        with SessionLocal() as session:
            context_manager = ContextManager(session)
            payload = {"step": step, **context_data}
            context_manager.set_context(
                tdm_user_id=event.sender_id,
                workspace_id=event.workspace_id,
                group_id=event.group_id,
                active_service_code=self.code,
                step=step,
                context_data=payload,
            )

    def _clear_context(self, event) -> None:
        with SessionLocal() as session:
            context_manager = ContextManager(session)
            context_manager.clear_context(event.sender_id)

    def _is_valid_query(self, query: str) -> bool:
        query = (query or "").strip()
        if not query:
            return False
        return any(ch.isalnum() for ch in query)

    def _build_sorted_variants(self, suggestions: list[dict]) -> list[dict]:
        variants = []

        for idx, item in enumerate(suggestions):
            data = item.get("data", {})
            name_data = data.get("name", {}) if data else {}
            company_name = (
                name_data.get("short_with_opf")
                or name_data.get("full_with_opf")
                or item.get("value")
                or f"Вариант {idx + 1}"
            )
            inn = data.get("inn", "—")
            address = data.get("address", {}).get("value", "—")

            priority = self._get_region_priority(item)

            variants.append(
                {
                    "index": idx,
                    "label": company_name,
                    "inn": inn,
                    "address": address,
                    "item": item,
                    "priority": priority,
                }
            )

        variants.sort(key=lambda x: (x["priority"], x["label"].lower()))
        return variants

    def _get_region_priority(self, suggestion: dict) -> int:
        """
        0 = Москва
        1 = Московская область
        2 = регионы
        """
        data = suggestion.get("data", {})
        address_data = data.get("address", {}).get("data", {}) if data else {}

        inn = str(data.get("inn", "") or "")
        region = str(address_data.get("region", "") or "").lower()
        city = str(address_data.get("city", "") or "").lower()
        area = str(address_data.get("area", "") or "").lower()

        # Москва
        if inn.startswith("77") or inn.startswith("97"):
            return 0
        if "москва" in region or city == "москва" or "москва" in area:
            return 0

        # Московская область
        if inn.startswith("50"):
            return 1
        if "московская" in region:
            return 1

        return 2

    def _send_variants(self, event, variants: list[dict], page: int = 0) -> None:
        page_size = self.PAGE_SIZE
        start = page * page_size
        end = start + page_size
        page_items = variants[start:end]

        if not page_items:
            event.reply_text(texts.DADATA_PAGE_EMPTY_TEXT)
            return

        screen_text = build_dadata_variants_screen(
            variants=variants,
            page=page,
            page_size=page_size,
        )

        buttons_list = []

        for item in page_items:
            real_idx = variants.index(item)
            short_label = self._truncate(item["label"], 40)
            buttons_list.append(
                InlineMessageButton(
                    id=real_idx + 1,
                    label=f"{real_idx + 1}. {short_label}",
                    callback_message="Выбран вариант организации",
                    callback_data=f"dadata:select:{real_idx}",
                )
            )

        if page > 0:
            buttons_list.append(
                InlineMessageButton(
                    id=1000 + page,
                    label=buttons.BTN_BACK,
                    callback_message="Показана предыдущая страница",
                    callback_data="dadata:prev_page",
                )
            )

        if end < len(variants):
            buttons_list.append(
                InlineMessageButton(
                    id=2000 + page,
                    label=buttons.BTN_DADATA_MORE,
                    callback_message="Показана следующая страница",
                    callback_data="dadata:next_page",
                )
            )

        buttons_list.append(
            InlineMessageButton(
                id=3000,
                label=buttons.BTN_TO_MENU,
                callback_message="Переход в меню",
                callback_data="dadata:menu",
            )
        )

        event.reply_text_message(
            MessageRequest(
                text=screen_text,
                buttons=buttons_list,
            )
        )

    def _send_result(
        self,
        event,
        response_json: dict,
        from_cache: bool = False,
        variants: Optional[list[dict]] = None,
        selected_index: Optional[int] = None,
    ) -> None:
        text = build_dadata_result_screen(
            response_json=response_json,
            from_cache=from_cache,
            continue_hint=True,
        )

        buttons_list = []

        if variants is not None and selected_index is not None:
            if selected_index > 0:
                buttons_list.append(
                    InlineMessageButton(
                        id=2,
                        label=buttons.BTN_DADATA_PREV,
                        callback_message="Показана предыдущая организация",
                        callback_data="dadata:card_prev",
                    )
                )

            if selected_index < len(variants) - 1:
                buttons_list.append(
                    InlineMessageButton(
                        id=3,
                        label=buttons.BTN_DADATA_NEXT,
                        callback_message="Показана следующая организация",
                        callback_data="dadata:card_next",
                    )
                )

        buttons_list.append(
            InlineMessageButton(
                id=1,
                label=buttons.BTN_DADATA_NEW_SEARCH,
                callback_message="Новый поиск",
                callback_data="dadata:new_search",
            )
        )
        buttons_list.append(
            InlineMessageButton(
                id=4,
                label=buttons.BTN_DADATA_TO_MENU,
                callback_message="Переход в меню",
                callback_data="dadata:menu",
            )
        )

        event.reply_text_message(
            MessageRequest(
                text=text,
                buttons=buttons_list,
            )
        )

    def _format_response(self, response_json: dict, from_cache: bool = False) -> str:
        suggestions = response_json.get("suggestions", [])
        if not suggestions:
            return "🔍 По вашему запросу ничего не найдено."

        suggestion = suggestions[0]
        data = suggestion.get("data", {})

        name_data = data.get("name", {}) if data else {}
        address_data = data.get("address", {}) if data else {}
        management_data = data.get("management", {}) if data else {}
        state_data = data.get("state", {}) if data else {}

        company_short = (
            name_data.get("short_with_opf")
            or suggestion.get("value")
            or "Без названия"
        )
        company_full = self._safe_value(name_data.get("full_with_opf"))

        inn = self._safe_value(data.get("inn"))
        ogrn = self._safe_value(data.get("ogrn"))
        kpp = self._safe_value(data.get("kpp"))
        address = self._safe_value(address_data.get("value"))
        postal_code = self._safe_value(address_data.get("data", {}).get("postal_code"))

        manager = self._format_management_names(management_data)
        manager_post = self._safe_value(management_data.get("post"))

        okved = self._safe_value(data.get("okved"))
        org_status = self._format_status(state_data.get("status"))
        registration_date = self._format_timestamp_ms(state_data.get("registration_date"))
        liquidation_date = self._format_timestamp_ms(state_data.get("liquidation_date"))

        cache_mark = "\n🧠 Ответ из кэша" if from_cache else ""
        continue_hint = "\n💬 Введите следующий ИНН или название."

        return (
            f"🏢 {company_short}\n"
            f"🏛 {company_full}\n"
            f"📌 ИНН: {inn}\n"
            f"📌 ОГРН: {ogrn}\n"
            f"📌 КПП: {kpp}\n"
            f"📍 Адрес: {address}\n"
            f"📮 Индекс: {postal_code}\n"
            f"📊 Статус: {org_status}\n"
            f"📅 Регистрация: {registration_date}\n"
            f"📅 Ликвидация: {liquidation_date}\n"
            f"👤 Руководитель: {manager}\n"
            f"💼 Должность: {manager_post}\n"
            f"🧾 ОКВЭД: {okved}"
            f"{cache_mark}"
            f"{continue_hint}"
        )

    def _safe_value(self, value: Any, default: str = "—") -> str:
        if value is None:
            return default
        if value == "":
            return default
        if str(value).lower() == "none":
            return default
        return str(value)

    def _truncate(self, text: str, max_len: int) -> str:
        text = self._safe_value(text, "")
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"

    def _format_timestamp_ms(self, value: Any) -> str:
        if value in (None, "", "None"):
            return "—"

        try:
            value_int = int(value)
            if value_int <= 0:
                return "—"
            dt = datetime.utcfromtimestamp(value_int / 1000)
            return dt.strftime("%d.%m.%Y")
        except Exception:
            return self._safe_value(value)

    def _format_status(self, value: Any) -> str:
        mapping = {
            "ACTIVE": "Действующая",
            "LIQUIDATING": "В процессе ликвидации",
            "LIQUIDATED": "Ликвидирована",
            "BANKRUPT": "Банкротство",
            "REORGANIZING": "В процессе реорганизации",
        }
        value = self._safe_value(value)
        return mapping.get(value, value)

    def _format_management_names(self, management_data: Any) -> str:
        if management_data is None:
            return "—"

        if isinstance(management_data, dict):
            name = management_data.get("name")
            if isinstance(name, list):
                return ", ".join([self._safe_value(x, "") for x in name if self._safe_value(x, "")])
            if isinstance(name, str):
                return self._safe_value(name)

            names = []
            for key, value in management_data.items():
                if "name" in str(key).lower():
                    if isinstance(value, list):
                        names.extend([self._safe_value(x, "") for x in value if self._safe_value(x, "")])
                    elif isinstance(value, str):
                        names.append(self._safe_value(value, ""))
            if names:
                return ", ".join([x for x in names if x])

        if isinstance(management_data, list):
            names = []
            for item in management_data:
                if isinstance(item, dict):
                    names.append(self._safe_value(item.get("name"), ""))
                else:
                    names.append(self._safe_value(item, ""))
            names = [x for x in names if x]
            return ", ".join(names) if names else "—"

        return self._safe_value(management_data)