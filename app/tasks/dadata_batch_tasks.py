import logging
import os
import uuid

from app.config import get_settings
from app.db.session import SessionLocal
from app.repositories.tasks import TaskRepository
from app.services.dadata_batch_service.batch_logic import DaDataBatchProcessor
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="dadata_batch.process_file")
def process_dadata_batch_task(task_uuid: str, input_file_path: str):
    os.makedirs(os.path.join(settings.files_base_dir, "output"), exist_ok=True)

    output_file_name = f"dadata_result_{task_uuid[:8]}.xlsx"
    output_file_path = os.path.join(settings.files_base_dir, "output", output_file_name)

    def update_progress(current: int, total: int, message: str):
        with SessionLocal() as session:
            TaskRepository(session).update_progress(
                task_uuid=task_uuid,
                current=current,
                total=total,
                message=message,
            )

    with SessionLocal() as session:
        TaskRepository(session).mark_running(task_uuid, "Задача запущена")

    try:
        processor = DaDataBatchProcessor()
        result = processor.process_file(
            file_path=input_file_path,
            output_path=output_file_path,
            task_callback=update_progress,
        )

        with SessionLocal() as session:
            TaskRepository(session).mark_done(
                task_uuid=task_uuid,
                result_payload=result,
                result_file_path=output_file_path,
                message="Обработка завершена",
            )

        logger.info("Task %s done. Output: %s", task_uuid, output_file_path)
        return result

    except Exception as e:
        logger.exception("Task %s failed", task_uuid)
        with SessionLocal() as session:
            TaskRepository(session).mark_failed(
                task_uuid=task_uuid,
                error_text=str(e)[:1000],
                message="Ошибка обработки",
            )
        raise