from typing import Optional

from messenger_bot_api.data_classes import InlineMessageButton
from messenger_bot_api.util import MessageRequest

from app.bot.context_manager import ContextManager
from app.db.session import SessionLocal
from app.repositories.dadata import DaDataRepository
from app.services.base import BaseService


class DaDataAdminService(BaseService):
    code = "dadata_admin"
    name = "⚙️ Управление DaData"
    description = "Администрирование API-ключей DaData"

    def start(self, router, event, context: Optional[dict] = None) -> None:
        self._set_step(event, "menu", {})
        self._show_admin_menu(event)

    def handle_message(self, router, event, context: Optional[dict] = None) -> bool:
        text = (event.message_text or "").strip().lower()

        if text == "keys" or text == "ключи":
            self._show_keys_list(event)
            return True

        if text.startswith("add") or text.startswith("добавить"):
            self._set_step(event, "awaiting_new_key", {})
            event.reply_text("🔑 Введите новый API-ключ DaData:\n(или /cancel для отмены)")
            return True

        if text.startswith("toggle"):
            parts = text.split()
            if len(parts) != 2 or not parts[1].isdigit():
                event.reply_text("❌ Формат: `toggle <id>`\nПример: `toggle 1`")
                return True
            
            key_id = int(parts[1])
            self._toggle_key(event, key_id)
            return True

        # Обработка ввода нового ключа
        step = (context or {}).get("step")
        if step == "awaiting_new_key":
            api_key = event.message_text.strip()
            if not api_key:
                event.reply_text("Ключ не может быть пустым.")
                return True
            
            comment = "Добавлен через бота"
            with SessionLocal() as session:
                repo = DaDataRepository(session)
                try:
                    repo.create_api_key(api_key=api_key, comment=comment)
                    event.reply_text(f"✅ Ключ успешно добавлен!\nТеперь используйте команду `keys` для просмотра.")
                    self._set_step(event, "menu", {})
                except Exception as e:
                    event.reply_text(f"❌ Ошибка при добавлении: {e}")
            return True

        event.reply_text("Неизвестная команда. Доступные: `keys`, `add`, `toggle <id>`")
        return True

    def handle_button(self, router, event, context: Optional[dict] = None) -> bool:
        callback_data = event.selected_button.callback_data if event.selected_button else None
        if not callback_data:
            return False

        if callback_data == "dadata_admin:list":
            self._show_keys_list(event)
            return True
        
        if callback_data == "dadata_admin:add":
            self._set_step(event, "awaiting_new_key", {})
            event.reply_text(
                "🔑 Введите новый API-ключ DaData.\n"
                "Для выхода используйте /cancel"
            )
            return True

        if callback_data == "dadata_admin:back":
            self._set_step(event, "menu", {})
            self._show_admin_menu(event)
            return True

        return False

    def _set_step(self, event, step: str, context_data: dict):
        with SessionLocal() as session:
            ContextManager(session).set_context(
                tdm_user_id=event.sender_id,
                workspace_id=event.workspace_id,
                group_id=event.group_id,
                active_service_code=self.code,
                step=step,
                context_data=context_data,
            )

    def _show_admin_menu(self, event):
        buttons = [
            InlineMessageButton(
                id=1,
                label="📋 Список ключей",
                callback_data="dadata_admin:list",
                callback_message="Показан список ключей"
            ),
            InlineMessageButton(
                id=2,
                label="➕ Добавить ключ",
                callback_data="dadata_admin:add",
                callback_message="Добавление нового ключа"
            ),
        ]
        event.reply_text_message(
            MessageRequest(
                text="🛠 Панель управления DaData\n\nВыберите действие:",
                buttons=buttons
            )
        )

    def _show_keys_list(self, event):
        with SessionLocal() as session:
            repo = DaDataRepository(session)
            keys = repo.get_active_keys()
            
            # Получаем ВСЕ ключи, даже неактивные, для полного списка
            from sqlalchemy import select
            from app.db.models import DaDataApiKey
            all_keys = session.scalars(select(DaDataApiKey).order_by(DaDataApiKey.id.desc())).all()

        if not all_keys:
            event.reply_text("Ключи пока не добавлены.")
            return

        lines = ["🗝 Список API-ключей:"]

        for key in all_keys:
            status_icon = "🟢" if key.is_active else "🔴"
            masked_key = key.api_key[:6] + "..." + key.api_key[-4:] if len(key.api_key) > 10 else key.api_key
            limit_info = f"{key.used_today}/{key.daily_limit}"

            lines.append(
                f"{status_icon} ID: {key.id} | {masked_key}\n"
                f"Лимит: {limit_info}\n"
                f"Комментарий: {key.comment or '-'}\n"
                f"Команда: toggle {key.id}"
            )

        lines.append("\nℹ️ Используйте команду toggle <id> для включения/выключения.")

        buttons = [
            InlineMessageButton(
                id=99,
                label="🔙 Назад",
                callback_data="dadata_admin:back",
                callback_message="Открыто меню управления"
            )
        ]

        event.reply_text_message(
            MessageRequest(text="\n".join(lines), buttons=buttons)
        )

    def _toggle_key(self, event, key_id: int):
        with SessionLocal() as session:
            from app.db.models import DaDataApiKey
            key = session.get(DaDataApiKey, key_id)
            if not key:
                event.reply_text("❌ Ключ не найден.")
                return

            key.is_active = not key.is_active
            session.commit()
            
            status = "включен" if key.is_active else "отключен"
            event.reply_text(f"✅ Ключ ID {key.id} теперь {status}.")