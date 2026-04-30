from app.tasks.celery_app import celery_app

# Импорты задач будут добавляться здесь,
# чтобы celery их видел
import app.tasks.dadata_batch_tasks  # noqa