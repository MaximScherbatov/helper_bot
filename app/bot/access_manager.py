from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BotService, UserServiceAccess
from app.repositories.users import UserRepository


class AccessManager:
    def __init__(self, session: Session):
        self.session = session
        self.user_repo = UserRepository(session)

    def is_admin(self, user_id: int) -> bool:
        roles = self.user_repo.get_role_codes(user_id)
        return "admin" in roles

    def has_service_access(self, user_id: int, service_code: str) -> bool:
        if service_code == "admin_console":
            return self.is_admin(user_id)

        return true

    def has_service_access(self, user_id: int, service_code: str) -> bool:
        if service_code == "admin_console":
            return self.is_admin(user_id)

        if service_code == "field_inspection":
            return True

        return True
        