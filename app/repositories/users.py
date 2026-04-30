from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BotUser, SystemRole, UserSystemRole


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_tdm_user_id(self, tdm_user_id: int) -> BotUser | None:
        return self.session.scalar(
            select(BotUser).where(BotUser.tdm_user_id == tdm_user_id)
        )

    def create(
        self,
        tdm_user_id: int,
        display_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        middle_name: str | None = None,
    ) -> BotUser:
        user = BotUser(
            tdm_user_id=tdm_user_id,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            is_active=True,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_or_create(
        self,
        tdm_user_id: int,
        display_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        middle_name: str | None = None,
    ) -> BotUser:
        user = self.get_by_tdm_user_id(tdm_user_id)
        if user is not None:
            changed = False

            if display_name and user.display_name != display_name:
                user.display_name = display_name
                changed = True

            if first_name and user.first_name != first_name:
                user.first_name = first_name
                changed = True

            if last_name and user.last_name != last_name:
                user.last_name = last_name
                changed = True

            if middle_name and user.middle_name != middle_name:
                user.middle_name = middle_name
                changed = True

            if changed:
                self.session.commit()

            return user

        return self.create(
            tdm_user_id=tdm_user_id,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
        )

    def get_role_codes(self, user_id: int) -> list[str]:
        rows = self.session.execute(
            select(SystemRole.code)
            .join(UserSystemRole, UserSystemRole.role_id == SystemRole.id)
            .where(UserSystemRole.user_id == user_id)
        ).all()
        return [row[0] for row in rows]

    def add_role(self, user_id: int, role_code: str) -> None:
        role = self.session.scalar(
            select(SystemRole).where(SystemRole.code == role_code)
        )
        if role is None:
            return

        existing = self.session.scalar(
            select(UserSystemRole).where(
                UserSystemRole.user_id == user_id,
                UserSystemRole.role_id == role.id,
            )
        )
        if existing is not None:
            return

        self.session.add(UserSystemRole(user_id=user_id, role_id=role.id))
        self.session.commit()