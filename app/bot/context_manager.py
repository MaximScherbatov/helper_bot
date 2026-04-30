from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.repositories.contexts import ContextRepository


class ContextManager:
    DEFAULT_TTL_MINUTES = 5

    SERVICE_TTL_MINUTES = {
        "dadata": 30,
        "dadata_batch": 120,
        "dadata_admin": 10,
        "echo": 5,
    }

    def __init__(self, session: Session):
        self.session = session
        self.repo = ContextRepository(session)

    def get_context(self, tdm_user_id: int):
        context = self.repo.get_active(tdm_user_id)
        if context is None:
            return None

        if context.updated_at is None:
            return context

        service_code = context.active_service_code or ""
        ttl_minutes = self.SERVICE_TTL_MINUTES.get(service_code, self.DEFAULT_TTL_MINUTES)
        ttl_border = datetime.utcnow() - timedelta(minutes=ttl_minutes)

        if context.updated_at < ttl_border:
            context.is_active = False
            self.session.commit()
            return None

        return context

    def set_context(
        self,
        tdm_user_id: int,
        workspace_id: int | None,
        group_id: int | None,
        active_service_code: str | None,
        step: str | None,
        context_data: dict | None,
    ):
        return self.repo.set_context(
            tdm_user_id=tdm_user_id,
            workspace_id=workspace_id,
            group_id=group_id,
            active_service_code=active_service_code,
            step=step,
            context_data=context_data,
        )

    def clear_context(self, tdm_user_id: int) -> None:
        self.repo.clear_context(tdm_user_id)