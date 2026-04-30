from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BotService, UserServiceAccess


class ServiceAccessRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_user_accesses(self, user_id: int) -> list[UserServiceAccess]:
        rows = self.session.scalars(
            select(UserServiceAccess).where(
                UserServiceAccess.user_id == user_id
            )
        )
        return list(rows)

    def get_active_user_accesses(self, user_id: int) -> list[UserServiceAccess]:
        rows = self.session.scalars(
            select(UserServiceAccess).where(
                UserServiceAccess.user_id == user_id,
                UserServiceAccess.is_active.is_(True),
            )
        )
        return list(rows)

    def grant_access(
        self,
        user_id: int,
        service_id: int,
        granted_by_user_id: int | None = None,
        access_role: str = "user",
        days: int | None = None,
        comment: str | None = None,
    ) -> UserServiceAccess:
        existing = self.session.scalar(
            select(UserServiceAccess).where(
                UserServiceAccess.user_id == user_id,
                UserServiceAccess.service_id == service_id,
            )
        )

        starts_at = datetime.utcnow()
        expires_at = starts_at + timedelta(days=days) if days else None

        if existing:
            existing.is_active = True
            existing.access_role = access_role
            existing.starts_at = starts_at
            existing.expires_at = expires_at
            existing.granted_by_user_id = granted_by_user_id
            existing.comment = comment
            existing.updated_at = datetime.utcnow()
            self.session.commit()
            self.session.refresh(existing)
            return existing

        row = UserServiceAccess(
            user_id=user_id,
            service_id=service_id,
            access_role=access_role,
            starts_at=starts_at,
            expires_at=expires_at,
            is_active=True,
            granted_by_user_id=granted_by_user_id,
            comment=comment,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def revoke_access(self, user_id: int, service_id: int) -> bool:
        row = self.session.scalar(
            select(UserServiceAccess).where(
                UserServiceAccess.user_id == user_id,
                UserServiceAccess.service_id == service_id,
                UserServiceAccess.is_active.is_(True),
            )
        )
        if row is None:
            return False

        row.is_active = False
        row.updated_at = datetime.utcnow()
        self.session.commit()
        return True

    def get_service_by_code(self, service_code: str) -> BotService | None:
        return self.session.scalar(
            select(BotService).where(BotService.code == service_code)
        )

    def list_services(self) -> list[BotService]:
        rows = self.session.scalars(
            select(BotService).order_by(BotService.name.asc())
        )
        return list(rows)