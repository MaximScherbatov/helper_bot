from sqlalchemy.orm import Session

from app.db.models import AuditLog


class AuditRepository:
    def __init__(self, session: Session):
        self.session = session

    def log(
        self,
        tdm_user_id: int,
        action: str,
        service_code: str | None = None,
        payload: dict | None = None,
        status: str | None = None,
    ) -> None:
        row = AuditLog(
            tdm_user_id=tdm_user_id,
            action=action,
            service_code=service_code,
            payload=payload,
            status=status,
        )
        self.session.add(row)
        self.session.commit()