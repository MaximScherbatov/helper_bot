from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import UserContext


class ContextRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_active(self, tdm_user_id: int) -> UserContext | None:
        return self.session.scalar(
            select(UserContext)
            .where(UserContext.tdm_user_id == tdm_user_id, UserContext.is_active.is_(True))
            .order_by(UserContext.updated_at.desc())
        )

    def set_context(
        self,
        tdm_user_id: int,
        workspace_id: int | None,
        group_id: int | None,
        active_service_code: str | None,
        step: str | None,
        context_data: dict | None,
    ) -> UserContext:
        current = self.get_active(tdm_user_id)
        if current is None:
            current = UserContext(
                tdm_user_id=tdm_user_id,
                workspace_id=workspace_id,
                group_id=group_id,
                active_service_code=active_service_code,
                step=step,
                context_data=context_data,
                is_active=True,
            )
            self.session.add(current)
        else:
            current.updated_at = datetime.utcnow()
            current.workspace_id = workspace_id
            current.group_id = group_id
            current.active_service_code = active_service_code
            current.step = step
            current.context_data = context_data
            current.is_active = True

        self.session.commit()
        self.session.refresh(current)
        return current

    def clear_context(self, tdm_user_id: int) -> None:
        current = self.get_active(tdm_user_id)
        if current is None:
            return

        current.is_active = False
        self.session.commit()