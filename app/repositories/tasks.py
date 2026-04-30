from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BackgroundTask


class TaskRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_task(
        self,
        task_uuid: str,
        tdm_user_id: int,
        service_code: str,
        task_type: str,
        input_payload: dict | None = None,
        progress_total: int = 0,
        message: str | None = None,
    ) -> BackgroundTask:
        row = BackgroundTask(
            task_uuid=task_uuid,
            tdm_user_id=tdm_user_id,
            service_code=service_code,
            task_type=task_type,
            status="queued",
            input_payload=input_payload,
            progress_total=progress_total,
            progress_current=0,
            message=message,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get_by_uuid(self, task_uuid: str) -> BackgroundTask | None:
        return self.session.scalar(
            select(BackgroundTask).where(BackgroundTask.task_uuid == task_uuid)
        )

    def get_latest_user_tasks(self, tdm_user_id: int, limit: int = 10) -> list[BackgroundTask]:
        rows = self.session.scalars(
            select(BackgroundTask)
            .where(BackgroundTask.tdm_user_id == tdm_user_id)
            .order_by(BackgroundTask.created_at.desc())
            .limit(limit)
        )
        return list(rows)

    def mark_running(self, task_uuid: str, message: str | None = None) -> None:
        row = self.get_by_uuid(task_uuid)
        if row is None:
            return
        row.status = "running"
        row.started_at = datetime.utcnow()
        if message is not None:
            row.message = message
        self.session.commit()

    def update_progress(self, task_uuid: str, current: int, total: int | None = None, message: str | None = None) -> None:
        row = self.get_by_uuid(task_uuid)
        if row is None:
            return
        row.progress_current = current
        if total is not None:
            row.progress_total = total
        if message is not None:
            row.message = message
        self.session.commit()

    def mark_done(
        self,
        task_uuid: str,
        result_payload: dict | None = None,
        result_file_path: str | None = None,
        message: str | None = None,
    ) -> None:
        row = self.get_by_uuid(task_uuid)
        if row is None:
            return
        row.status = "done"
        row.finished_at = datetime.utcnow()
        row.result_payload = result_payload
        row.result_file_path = result_file_path
        if message is not None:
            row.message = message
        self.session.commit()

    def mark_failed(self, task_uuid: str, error_text: str, message: str | None = None) -> None:
        row = self.get_by_uuid(task_uuid)
        if row is None:
            return
        row.status = "failed"
        row.finished_at = datetime.utcnow()
        row.error_text = error_text
        if message is not None:
            row.message = message
        self.session.commit()