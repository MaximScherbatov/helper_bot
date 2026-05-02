import os
import logging
import time
from collections import OrderedDict

from app.config import get_settings
from app.bot.access_manager import AccessManager
from app.bot.context_manager import ContextManager
from app.repositories.audit import AuditRepository
from app.repositories.services import ServiceRepository
from app.repositories.users import UserRepository
from app.services.registry import ServiceRegistry
from messenger_bot_api.data_classes import InlineMessageButton
from messenger_bot_api.util import MessageRequest

from app.ui import texts
from app.ui.screens import (
    build_help_screen,
    build_menu_screen,
    build_start_screen,
    build_status_screen,
    build_tasks_screen,
    build_whoami_screen,
)

logger = logging.getLogger(__name__)


class BotRouter:
    def __init__(self, session_factory, service_registry: ServiceRegistry):
        self.session_factory = session_factory
        self.settings = get_settings()
        self.service_registry = service_registry
        self._processed_events: OrderedDict = OrderedDict()
        self._max_event_cache = 500

    def _is_duplicate_event(self, event) -> bool:
        """
        Дедупликация для SSE.
        Важно: кнопочные события могут приходить с тем же message id, поэтому
        для них нужно добавлять callback_data/clientRandomId/date в ключ.
        """
        key = None

        # 1) Если у платформы есть event_id — это лучший ключ
        if event.event_id is not None:
            key = f"ev:{event.event_id}"

        else:
            # 2) Fallback: строим ключ из payload
            try:
                payload = event.get_payload_data() or {}
                msgs = payload.get("messages") or []
                msg0 = msgs[0] if msgs and isinstance(msgs[0], dict) else {}

                msg_id = msg0.get("id") or msg0.get("stringId")
                sender_id = msg0.get("senderId") if "senderId" in msg0 else event.sender_id
                client_random_id = msg0.get("clientRandomId")
                dt = msg0.get("date")

                # Кнопка: добавляем callback_data
                callback_data = None
                if getattr(event, "has_selected_button", False) and getattr(event, "selected_button", None):
                    callback_data = event.selected_button.callback_data

                # Собираем максимально устойчивый ключ
                parts = ["msg", str(msg_id), str(sender_id)]

                if callback_data:
                    parts.append(f"btn:{callback_data}")

                # clientRandomId обычно уникален для пользовательских сообщений
                if client_random_id is not None:
                    parts.append(f"cr:{client_random_id}")
                elif dt is not None:
                    parts.append(f"dt:{dt}")

                # если вообще ничего нет — ключ не строим
                if msg_id is None and callback_data is None and client_random_id is None and dt is None:
                    key = None
                else:
                    key = "|".join(parts)

            except Exception:
                logger.exception("Failed to build dedup key")
                key = None

        if key is None:
            return False

        if key in self._processed_events:
            logger.warning("Duplicate event detected, key=%s", key)
            return True

        self._processed_events[key] = time.time()
        if len(self._processed_events) > self._max_event_cache:
            self._processed_events.popitem(last=False)

        return False

    def _register_user_if_needed(self, session, event):
        user_repo = UserRepository(session)

        tdm_user_id = event.sender_id

        # системные/технические события не регистрируем
        if tdm_user_id in (None, -1):
            return None

        user_info = self._extract_user_info_from_event(event)

        first_name = user_info.get("first_name")
        last_name = user_info.get("last_name")
        middle_name = user_info.get("middle_name")

        display_name_parts = [last_name, first_name, middle_name]
        display_name = " ".join([p for p in display_name_parts if p]).strip()

        # ВАЖНО: НЕ ходим в get_states() (может зависать/падать SSL)
        if not display_name:
            display_name = f"user_{tdm_user_id}"

        user = user_repo.get_or_create(
            tdm_user_id=tdm_user_id,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
        )

        roles = user_repo.get_role_codes(user.id)
        if not roles:
            if tdm_user_id in self.settings.admin_tdm_user_ids:
                user_repo.add_role(user.id, "admin")
            else:
                user_repo.add_role(user.id, "user")

        return user_repo.get_by_tdm_user_id(tdm_user_id)

    def sync_services(self):
        with self.session_factory() as session:
            service_repo = ServiceRepository(session)
            for service in self.service_registry.all():
                service_repo.create_if_not_exists(
                    code=service.code,
                    name=service.name,
                    description=service.description,
                )

    def handle_start(self, event):
        try:
            if self._is_duplicate_event(event):
                return

            if self._is_system_event(event):
                return

            with self.session_factory() as session:
                user = self._register_user_if_needed(session, event)
                if user is not None:
                    AuditRepository(session).log(
                        tdm_user_id=user.tdm_user_id,
                        action="command_start",
                        status="ok",
                    )

            event.reply_text(build_start_screen())

        finally:
            self._confirm_event_safe(event)

    def handle_help(self, event):
        if self._is_duplicate_event(event):
            return

        try:
            if event.sender_id == -1:
                return

            with self.session_factory() as session:
                user = self._register_user_if_needed(session, event)
                if user is not None:
                    AuditRepository(session).log(
                        tdm_user_id=user.tdm_user_id,
                        action="command_help",
                        status="ok",
                    )

            event.reply_text(build_help_screen())

        finally:
            self._confirm_event_safe(event)

    def handle_status(self, event):
        if self._is_duplicate_event(event):
            return

        try:
            if event.sender_id == -1:
                return

            with self.session_factory() as session:
                user = self._register_user_if_needed(session, event)
                if user is None:
                    return

                context_manager = ContextManager(session)
                context = context_manager.get_context(user.tdm_user_id)

                AuditRepository(session).log(
                    tdm_user_id=user.tdm_user_id,
                    action="command_status",
                    status="ok",
                )

            event.reply_text(build_status_screen(context))

        finally:
            self._confirm_event_safe(event)

    def handle_cancel(self, event):
        if self._is_duplicate_event(event):
            return

        try:
            if event.sender_id == -1:
                return

            with self.session_factory() as session:
                user = self._register_user_if_needed(session, event)
                if user is None:
                    return

                ContextManager(session).clear_context(user.tdm_user_id)
                AuditRepository(session).log(
                    tdm_user_id=user.tdm_user_id,
                    action="command_cancel",
                    status="ok",
                )

            event.reply_text(texts.SCENARIO_RESET_TEXT)

        finally:
            self._confirm_event_safe(event)

    def handle_resume(self, event):
        if self._is_duplicate_event(event):
            return

        try:
            if event.sender_id == -1:
                return

            with self.session_factory() as session:
                user = self._register_user_if_needed(session, event)
                if user is None:
                    return

                context_manager = ContextManager(session)
                context = context_manager.get_context(user.tdm_user_id)

                AuditRepository(session).log(
                    tdm_user_id=user.tdm_user_id,
                    action="command_resume",
                    status="ok",
                )

            if context is None or not context.active_service_code:
                event.reply_text(texts.RESUME_NOTHING_TEXT)
                return

            service = self.service_registry.get(context.active_service_code)
            if service is None:
                event.reply_text(texts.SERVICE_NOT_FOUND_TEXT)
                return

            service_ctx = dict(context.context_data or {})
            service_ctx["step"] = context.step
            service.resume(self, event, context=service_ctx)

        finally:
            self._confirm_event_safe(event)

    def handle_whoami(self, event):
        if self._is_duplicate_event(event):
            return

        try:
            if event.sender_id == -1:
                return

            with self.session_factory() as session:
                user = self._register_user_if_needed(session, event)
                if user is None:
                    return

                roles = UserRepository(session).get_role_codes(user.id)

                AuditRepository(session).log(
                    tdm_user_id=user.tdm_user_id,
                    action="command_whoami",
                    status="ok",
                )

            event.reply_text(
                build_whoami_screen(
                    tdm_user_id=user.tdm_user_id,
                    user_id=user.id,
                    roles=roles,
                )
            )

        finally:
            self._confirm_event_safe(event)

    def handle_menu(self, event):
        try:
            if self._is_duplicate_event(event):
                return

            if self._is_system_event(event):
                return

            with self.session_factory() as session:
                user = self._register_user_if_needed(session, event)
                if user is None:
                    return

                AuditRepository(session).log(
                    tdm_user_id=user.tdm_user_id,
                    action="command_menu",
                    status="ok",
                )

                # ВАЖНО: меню отправляем напрямую, без повторного dedup
                self._send_menu_screen(event, session, user)

        finally:
            self._confirm_event_safe(event)

    def handle_button(self, event):
        try:
            if self._is_duplicate_event(event):
                return

            if self._is_system_event(event):
                return

            with self.session_factory() as session:
                user = self._register_user_if_needed(session, event)
                if user is None:
                    return

                access_manager = AccessManager(session)
                context_manager = ContextManager(session)
                audit_repo = AuditRepository(session)

                if not event.has_selected_button or not event.selected_button:
                    return

                callback_data = event.selected_button.callback_data
                if not callback_data:
                    return

                # Глобальный выход в меню из любого сервиса: dadata:menu, field_inspection:menu и т.п.
                if (not callback_data.startswith("service:")) and callback_data.endswith(":menu"):
                    ContextManager(session).clear_context(user.tdm_user_id)

                    audit_repo.log(
                        tdm_user_id=user.tdm_user_id,
                        action="global_menu_from_button",
                        payload={"callback_data": callback_data},
                        status="ok",
                    )

                    # ВАЖНО: не вызываем handle_menu(event) — будет dedup на том же button-event
                    self._send_menu_screen(event, session, user)
                    return

                if callback_data.startswith("service:"):
                    service_code = callback_data.split(":", 1)[1]
                    service = self.service_registry.get(service_code)
                    if service is None:
                        event.reply_text(texts.SERVICE_NOT_FOUND_TEXT)
                        return

                    if not access_manager.has_service_access(user.id, service_code):
                        event.reply_text(texts.ACCESS_DENIED_TEXT)
                        return

                    audit_repo.log(
                        tdm_user_id=user.tdm_user_id,
                        action="service_open",
                        service_code=service_code,
                        status="ok",
                    )
                    service.start(self, event)
                    return

                context = context_manager.get_context(user.tdm_user_id)
                if context is None or not context.active_service_code:
                    event.reply_text(texts.OUTDATED_ACTION_TEXT)
                    return

                service = self.service_registry.get(context.active_service_code)
                if service is None:
                    event.reply_text(texts.SERVICE_NOT_FOUND_TEXT)
                    return

                service_ctx = dict(context.context_data or {})
                service_ctx["step"] = context.step
                handled = service.handle_button(self, event, context=service_ctx)

                if handled:
                    audit_repo.log(
                        tdm_user_id=user.tdm_user_id,
                        action="service_button",
                        service_code=context.active_service_code,
                        payload={"callback_data": callback_data},
                        status="ok",
                    )
                return

        finally:
            self._confirm_event_safe(event)

    def handle_message(self, event):
        try:
            if self._is_duplicate_event(event):
                return

            if self._is_system_event(event):
                return

            service_to_start = None

            with self.session_factory() as session:
                user = self._register_user_if_needed(session, event)
                if user is None:
                    return

                context_manager = ContextManager(session)
                access_manager = AccessManager(session)
                audit_repo = AuditRepository(session)

                context = context_manager.get_context(user.tdm_user_id)

                logger.info(
                    "Incoming message: event_id=%s sender_id=%s workspace_id=%s group_id=%s text=%s",
                    event.event_id,
                    event.sender_id,
                    event.workspace_id,
                    event.group_id,
                    event.message_text,
                )
                try:
                    logger.info("RAW PAYLOAD: %s", event.get_payload_data())
                except Exception:
                    logger.exception("Failed to log raw payload")

                message_text = (event.message_text or "").strip()

                # 1) Открытие сервиса "service:code" — только если есть текст
                if message_text and message_text.startswith("service:"):
                    service_code = message_text.split(":", 1)[1]
                    service = self.service_registry.get(service_code)
                    if service is None:
                        event.reply_text(texts.SERVICE_NOT_FOUND_TEXT)
                        return

                    if not access_manager.has_service_access(user.id, service_code):
                        event.reply_text(texts.ACCESS_DENIED_TEXT)
                        return

                    audit_repo.log(
                        tdm_user_id=user.tdm_user_id,
                        action="service_open_by_text",
                        service_code=service_code,
                        payload={"message_text": message_text},
                        status="ok",
                    )
                    service_to_start = service

                # 2) Если есть активный сервис — передаём событие ему ВСЕГДА,
                # даже если message_text пустой (например, пришёл файл)
                elif context and context.active_service_code:
                    service = self.service_registry.get(context.active_service_code)

                    if service:
                        service_ctx = dict(context.context_data or {})
                        service_ctx["step"] = context.step
                        handled = service.handle_message(self, event, context=service_ctx)

                        if handled:
                            audit_repo.log(
                                tdm_user_id=user.tdm_user_id,
                                action="service_message",
                                service_code=context.active_service_code,
                                payload={"message_text": event.message_text},
                                status="ok",
                            )
                            return

                    # если активный сервис не понял событие
                    event.reply_text(texts.UNKNOWN_MESSAGE_TEXT)
                    return

                # 3) Нет активного сервиса
                else:
                    if not message_text:
                        return

                    # Если пользователь ввёл команду, но она не была поймана CommandHandler-ом
                    if message_text.startswith("/"):
                        audit_repo.log(
                            tdm_user_id=user.tdm_user_id,
                            action="unknown_command",
                            payload={"message_text": event.message_text},
                            status="ok",
                        )
                        event.reply_text("Неизвестная команда. Откройте /help или /menu.")
                        return

                    # В групповых чатах не вмешиваемся в обычную переписку
                    # (workspace_id > 0 — групповой чат/рабочее пространство)
                    if event.workspace_id is not None and event.workspace_id > 0:
                        audit_repo.log(
                            tdm_user_id=user.tdm_user_id,
                            action="group_chatter_ignored",
                            payload={"message_text": event.message_text},
                            status="ok",
                        )
                        return

                    # В личном чате подсказываем, что делать дальше
                    audit_repo.log(
                        tdm_user_id=user.tdm_user_id,
                        action="message_fallback",
                        payload={"message_text": event.message_text},
                        status="ok",
                    )
                    event.reply_text(texts.UNKNOWN_MESSAGE_TEXT)
                    return

            if service_to_start is not None:
                service_to_start.start(self, event)

        finally:
            self._confirm_event_safe(event)


    def handle_tasks(self, event):
        if self._is_duplicate_event(event):
            return

        try:
            if event.sender_id == -1:
                return

            with self.session_factory() as session:
                user = self._register_user_if_needed(session, event)
                if user is None:
                    return

                from app.repositories.tasks import TaskRepository
                tasks = TaskRepository(session).get_latest_user_tasks(user.tdm_user_id, limit=10)

                AuditRepository(session).log(
                    tdm_user_id=user.tdm_user_id,
                    action="command_tasks",
                    status="ok",
                )

            event.reply_text(build_tasks_screen(tasks))

        finally:
            self._confirm_event_safe(event)

    def handle_send_test_xlsx(self, event):
        if self._is_duplicate_event(event):
            return

        try:
            if event.sender_id in (None, -1):
                return

            import io
            import pandas as pd
            from app.integrations.tdm_file_sender import TdmFileSender

            df = pd.DataFrame([{"col1": "test", "col2": 123}])
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False)
            content = buffer.getvalue()

            sender = TdmFileSender()
            success = sender.send_file(
                workspace_id=event.workspace_id,
                group_id=event.group_id,
                file_name="test.xlsx",
                content=content,
                message_text="📎 Тестовый xlsx-файл",
            )

            if success:
                event.reply_text(texts.TEST_XLSX_SUCCESS_TEXT)
            else:
                event.reply_text(texts.TEST_XLSX_FAIL_TEXT)

        except Exception as e:
            import traceback
            error_text = f"{type(e).__name__}: {str(e)}"
            print("TEST XLSX SEND ERROR:", error_text, flush=True)
            print(traceback.format_exc(), flush=True)
            event.reply_text(f"❌ Ошибка: {error_text}")

        finally:
            self._confirm_event_safe(event)

    def _confirm_event_safe(self, event):
        try:
            if event.workspace_id is None or event.group_id is None:
                return

            confirm_id = event.event_id

            if confirm_id is None:
                payload = event.get_payload_data() or {}
                msgs = payload.get("messages") or []
                if msgs and isinstance(msgs[0], dict):
                    # В первую очередь id (int), а не stringId
                    confirm_id = msgs[0].get("id") or msgs[0].get("stringId")

            if confirm_id is None:
                return

            # stringId может быть строкой "101196792"
            confirm_id_int = int(confirm_id)

            event.confirm_event(event.workspace_id, event.group_id, confirm_id_int)

        except Exception:
            logger.exception("Failed to confirm event")

    def _send_result_file(self, event, task) -> None:
        result_file_path = task.result_file_path
        if not result_file_path or not os.path.exists(result_file_path):
            event.reply_text(texts.RESULT_FILE_NOT_FOUND_TEXT)
            return

        try:
            with open(result_file_path, "rb") as f:
                content = f.read()

            file_name = os.path.basename(result_file_path)

            from messenger_bot_api.util import File, MessageRequest

            resp = event.reply_file_message(
                File(file_name, content),
                MessageRequest("📎 Готовый результат обработки")
            )

            if resp is None:
                event.reply_text("❌ Ошибка при отправке файла: API вернул пустой ответ.")
                return

        except Exception as e:
            import traceback
            error_text = f"{type(e).__name__}: {str(e)}"
            print("SEND RESULT FILE ERROR:", error_text, flush=True)
            print(traceback.format_exc(), flush=True)
            event.reply_text(f"❌ Ошибка при отправке файла: {error_text}")

    def _normalize_command(self, message_text: str | None) -> str | None:
        if not message_text:
            return None
        text = message_text.strip()
        if not text:
            return None
        return text[1:].strip().lower() if text.startswith("/") else text.lower()

    def _extract_user_info_from_event(self, event):
        """
        Пытается извлечь ФИО пользователя из payload события.
        """
        first_name = None
        last_name = None
        middle_name = None

        try:
            payload = event.get_payload_data()

            # Вариант 1: sender в payload
            sender = payload.get("sender")
            if isinstance(sender, dict):
                first_name = sender.get("firstName") or first_name
                last_name = sender.get("lastName") or last_name
                middle_name = sender.get("middleName") or middle_name

            # Вариант 2: user в payload
            user = payload.get("user")
            if isinstance(user, dict):
                first_name = user.get("firstName") or first_name
                last_name = user.get("lastName") or last_name
                middle_name = user.get("middleName") or middle_name

            # Вариант 3: messages[0].sender
            messages = payload.get("messages", [])
            if messages and isinstance(messages[0], dict):
                sender = messages[0].get("sender")
                if isinstance(sender, dict):
                    first_name = sender.get("firstName") or first_name
                    last_name = sender.get("lastName") or last_name
                    middle_name = sender.get("middleName") or middle_name

        except Exception:
            logger.exception("Failed to extract user info from event payload")

        return {
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
        }

    def _resolve_sender_id(self, event) -> int | None:
        """
        Надёжно пытается определить sender_id.
        В TDM иногда event.sender_id может быть None, поэтому достаём senderId из payload.
        """
        sid = event.sender_id
        if sid not in (None, -1):
            return sid

        try:
            payload = event.get_payload_data() or {}

            # messages[0].senderId (часто самый надёжный вариант)
            msgs = payload.get("messages") or []
            if msgs and isinstance(msgs[0], dict):
                sid2 = msgs[0].get("senderId")
                if sid2 not in (None, -1):
                    return sid2

            # payload.sender.id (если встречается)
            sender = payload.get("sender")
            if isinstance(sender, dict):
                sid3 = sender.get("id")
                if sid3 not in (None, -1):
                    return sid3

            # payload.user.id (если встречается)
            user = payload.get("user")
            if isinstance(user, dict):
                sid4 = user.get("id")
                if sid4 not in (None, -1):
                    return sid4

        except Exception:
            logger.exception("Failed to resolve sender_id from payload")

        return sid

    def _is_system_event(self, event) -> bool:
        # sender_id = -1 — почти всегда системное событие
        if event.sender_id == -1:
            return True

        try:
            payload = event.get_payload_data() or {}
            msgs = payload.get("messages") or []
            if msgs and isinstance(msgs[0], dict):
                if msgs[0].get("senderId") == -1:
                    return True
                # system-объект в messages[0] — это точно системное сообщение
                if msgs[0].get("system"):
                    return True
        except Exception:
            pass

        return False

    def _send_menu_screen(self, event, session, user) -> None:
        access_manager = AccessManager(session)

        # Единый набор иконок для меню
        menu_icons = {
            "dadata": "🔎",
            "dadata_batch": "📦",
            "dadata_admin": "🔑",
            "admin_console": "⚙️",
            "field_inspection": "🧭",
            # "echo": "🧪",  # если вдруг сервис когда-нибудь вернётся
        }

        def _clean_name(name: str) -> str:
            # убираем “нестандартные” префиксы, если имя сервисов где-то было украшено
            # и приводим к аккуратному виду в меню
            s = (name or "").strip()
            # если начинается не с буквы/цифры (в т.ч. всякие декоративные символы),
            # уберём их до первого буквенно-цифрового символа
            while s and not s[0].isalnum():
                s = s[1:].lstrip()
            return s or (name or "").strip()

        buttons = []
        for service in self.service_registry.all():
            # на всякий случай: если тестовый сервис где-то ещё остался — не показываем
            if service.code == "echo":
                continue

            if not access_manager.has_service_access(user.id, service.code):
                continue

            icon = menu_icons.get(service.code, "🧩")
            label = f"{icon} {_clean_name(service.name)}".strip()

            buttons.append(
                InlineMessageButton(
                    id=len(buttons) + 1,
                    label=label,
                    callback_message=f"Открыт сервис: {service.name}",
                    callback_data=f"service:{service.code}",
                )
            )

        if not buttons:
            event.reply_text("У вас пока нет доступных сервисов.")
            return

        event.reply_text_message(
            MessageRequest(
                text=build_menu_screen(),
                buttons=buttons,
            )
        )

    '''def _confirm_read_safe(self, event):
        """
        confirm_read в messenger_bot_api ожидает int last_msg_id.
        В P2P (workspace_id = -1) часто либо не работает, либо не нужно — отключаем.
        """
        try:
            if event.workspace_id is None or event.group_id is None:
                return

            # В P2P выключаем confirm_read, чтобы не ловить ошибки/шумы
            if isinstance(event.workspace_id, int) and event.workspace_id < 0:
                return

            message_id = getattr(event, "message_id", None)

            if message_id is None:
                try:
                    payload = event.get_payload_data() or {}
                    msgs = payload.get("messages") or []
                    if msgs and isinstance(msgs[0], dict):
                        message_id = msgs[0].get("id")
                except Exception:
                    message_id = None

            if message_id is None:
                return

            # ВАЖНО: передаём int, НЕ список
            event.confirm_read(int(message_id))

        except Exception:
            logger.exception("Failed to confirm read")'''

    def _confirm_read_safe(self, event):
        return