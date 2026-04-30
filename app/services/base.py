from abc import ABC, abstractmethod
from typing import Optional


class BaseService(ABC):
    code: str = ""
    name: str = ""
    description: str = ""

    @abstractmethod
    def start(self, router, event, context: Optional[dict] = None) -> None:
        pass

    @abstractmethod
    def handle_message(self, router, event, context: Optional[dict] = None) -> bool:
        pass

    def handle_button(self, router, event, context: Optional[dict] = None) -> bool:
        return False

    def resume(self, router, event, context: Optional[dict] = None) -> None:
        event.reply_text(
            f"Продолжаем сценарий: {self.name}\n"
            f"Текущий шаг сохранён. Отправьте данные или /cancel для выхода."
        )