from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BotService


class ServiceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_code(self, code: str) -> BotService | None:
        return self.session.scalar(
            select(BotService).where(BotService.code == code)
        )

    def create_if_not_exists(self, code: str, name: str, description: str | None = None) -> BotService:
        service = self.get_by_code(code)
        if service is not None:
            changed = False
            if service.name != name:
                service.name = name
                changed = True
            if service.description != description:
                service.description = description
                changed = True
            if changed:
                self.session.commit()
            return service

        service = BotService(
            code=code,
            name=name,
            description=description,
            is_enabled=True,
        )
        self.session.add(service)
        self.session.commit()
        self.session.refresh(service)
        return service

    def get_enabled_services(self) -> list[BotService]:
        rows = self.session.scalars(
            select(BotService).where(BotService.is_enabled.is_(True)).order_by(BotService.name.asc())
        )
        return list(rows)