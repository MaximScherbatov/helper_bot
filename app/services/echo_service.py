from typing import Optional

from app.db.session import SessionLocal
from app.bot.context_manager import ContextManager
from app.services.base import BaseService


class EchoService(BaseService):
    code = "echo"
    name = "Тестовый сервис"
    description = "Простой сервис для проверки контекста и маршрутизации"

    def start(self, router, event, context: Optional[dict] = None) -> None:
        with SessionLocal() as session:
            context_manager = ContextManager(session)
            context_manager.set_context(
                tdm_user_id=event.sender_id,
                workspace_id=event.workspace_id,
                group_id=event.group_id,
                active_service_code=self.code,
                step="awaiting_text",
                context_data={},
            )

        event.reply_text(
            "Вы вошли в тестовый сервис.\n"
            "Отправьте любой текст, и я отвечу через сервисный роутинг.\n\n"
            "Для выхода используйте /cancel"
        )

    def handle_message(self, router, event, context: Optional[dict] = None) -> bool:
        if not event.message_text:
            event.reply_text("Я жду текстовое сообщение.")
            return True

        event.reply_text(f"Тестовый сервис получил: {event.message_text}")
        return True