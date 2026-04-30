import os
import uuid
from typing import Optional

from messenger_bot_api.data_classes import InlineMessageButton
from messenger_bot_api.util import MessageRequest

from app.bot.context_manager import ContextManager
from app.db.session import SessionLocal
from app.integrations.tdm_files import (
    download_event_file_to_storage,
    extract_file_from_event,
    is_xlsx_file,
)
from app.repositories.tasks import TaskRepository
from app.services.base import BaseService
from app.services.dadata_batch_service.batch_logic import DaDataBatchProcessor


from app.ui import texts, buttons
from app.ui.screens import (
    build_dadata_batch_analysis_screen,
    build_dadata_batch_done_screen,
    build_dadata_batch_intro_screen,
    build_dadata_batch_started_screen,
    build_dadata_batch_status_screen,
)

class DaDataBatchService(BaseService):
    code = "dadata_batch"
    name = "Пакетная проверка организаций"
    description = "Обработка xlsx-файла с ИНН и/или наименованиями организаций"

    def start(self, router, event, context: Optional[dict] = None) -> None:
        self._set_step(event, "awaiting_file", {})

        show_p2p_warning = event.workspace_id is None or event.workspace_id < 0

        event.reply_text_message(
            MessageRequest(
                text=build_dadata_batch_intro_screen(
                    show_p2p_warning=show_p2p_warning,
                ),
                buttons=[
                    InlineMessageButton(
                        id=1,
                        label=buttons.BTN_TO_MENU,
                        callback_message="Переход в меню",
                        callback_data="dadata_batch:menu",
                    )
                ],
            )
        )

    def handle_message(self, router, event, context: Optional[dict] = None) -> bool:
        context = context or {}
        step = context.get("step", "awaiting_file")

        if step == "awaiting_file":
            return self._handle_file_upload(router, event, context)

        if step == "awaiting_confirmation":
            return self._handle_confirmation(router, event, context)

        event.reply_text("Используйте /cancel для сброса или /menu для выбора сервиса.")
        return True

    def handle_button(self, router, event, context: Optional[dict] = None) -> bool:
        callback_data = event.selected_button.callback_data if event.selected_button else None
        if not callback_data:
            return False

        context = context or {}

        if callback_data == "dadata_batch:menu":
            self._clear_context(event)
            router.handle_menu(event)
            return True

        if callback_data == "dadata_batch:confirm":
            return self._start_processing(router, event, context)

        if callback_data == "dadata_batch:cancel":
            self._clear_context(event)
            event.reply_text(texts.DADATA_BATCH_CANCELLED_TEXT)
            return True

        if callback_data == "dadata_batch:check_status":
            return self._show_status(router, event, context)

        return False

    def _handle_file_upload(self, router, event, context: dict) -> bool:
        file_info = extract_file_from_event(event)

        if file_info is None:
            event.reply_text(texts.DADATA_BATCH_FILE_NOT_DETECTED_TEXT)
            return True

        if not is_xlsx_file(file_info):
            event.reply_text(
                f"{texts.DADATA_BATCH_WRONG_FILE_TYPE_TEXT}\n\n"
                f"Получен файл: {file_info['fileName']}"
            )
            return True

        event.reply_text(
                f"Файл: {file_info['fileName']}\n"
                f"Размер: {file_info['length']} байт\n\n"
                f"{texts.DADATA_BATCH_FILE_RECEIVED_TEXT}"
            )
        result = download_event_file_to_storage(event, sub_dir="input")
        if result is None:
            event.reply_text(texts.DADATA_BATCH_FILE_DOWNLOAD_ERROR_TEXT)
            return True

        file_path, _ = result

        try:
            processor = DaDataBatchProcessor()
            estimate = processor.estimate_file(file_path)
        except Exception as e:
            event.reply_text(
                f"{texts.DADATA_BATCH_ANALYZE_ERROR_TEXT}\n\n"
                f"Детали: {e}"
            )
            return True

        self._set_step(
            event=event,
            step="awaiting_confirmation",
            context_data={
                "file_path": file_path,
                "file_name": file_info["fileName"],
                "estimate": {
                    "total_rows": estimate.total_rows,
                    "unique_queries": estimate.unique_queries,
                    "cache_hits": estimate.cache_hits,
                    "required_api_calls": estimate.required_api_calls,
                    "available_tokens": estimate.available_tokens,
                    "enough_tokens": estimate.enough_tokens,
                },
            },
        )

        event.reply_text_message(
            MessageRequest(
                text=build_dadata_batch_analysis_screen(
                    file_name=file_info["fileName"],
                    estimate={
                        "total_rows": estimate.total_rows,
                        "unique_queries": estimate.unique_queries,
                        "cache_hits": estimate.cache_hits,
                        "required_api_calls": estimate.required_api_calls,
                        "available_tokens": estimate.available_tokens,
                        "enough_tokens": estimate.enough_tokens,
                    },
                ),
                buttons=[
                    InlineMessageButton(
                        id=1,
                        label=buttons.BTN_START_PROCESSING,
                        callback_message="Запуск обработки",
                        callback_data="dadata_batch:confirm",
                    ),
                    InlineMessageButton(
                        id=2,
                        label=buttons.BTN_CANCEL,
                        callback_message="Отмена",
                        callback_data="dadata_batch:cancel",
                    ),
                ],
            )
        )
        return True

    def _handle_confirmation(self, router, event, context: dict) -> bool:
        text = (event.message_text or "").strip().lower()
        if text in ("да", "yes", "y", "запустить"):
            return self._start_processing(router, event, context)

        event.reply_text_message(
            MessageRequest(
                text=texts.DADATA_BATCH_CONFIRM_BUTTON_HINT_TEXT,
                buttons=[
                    InlineMessageButton(
                        id=1,
                        label=buttons.BTN_START_PROCESSING,
                        callback_message="Запуск обработки",
                        callback_data="dadata_batch:confirm",
                    ),
                    InlineMessageButton(
                        id=2,
                        label=buttons.BTN_CANCEL,
                        callback_message="Отмена",
                        callback_data="dadata_batch:cancel",
                    ),
                ],
            )
        )
        return True

    def _start_processing(self, router, event, context: dict) -> bool:
        file_path = context.get("file_path")
        file_name = context.get("file_name", "file.xlsx")
        estimate = context.get("estimate", {})

        if not file_path or not os.path.exists(file_path):
            event.reply_text(texts.DADATA_BATCH_MISSING_FILE_TEXT)
            self._set_step(event, "awaiting_file", {})
            return True

        task_uuid = str(uuid.uuid4())
        total_rows = estimate.get("total_rows", 0)

        with SessionLocal() as session:
            task = TaskRepository(session).create_task(
                task_uuid=task_uuid,
                tdm_user_id=event.sender_id,
                service_code=self.code,
                task_type="xlsx_enrichment",
                input_payload={
                    "input_file_path": file_path,
                    "file_name": file_name,
                },
                progress_total=total_rows,
                message="Задача поставлена в очередь",
            )

        from app.tasks.dadata_batch_tasks import process_dadata_batch_task
        process_dadata_batch_task.delay(
            task_uuid=task_uuid,
            input_file_path=file_path,
        )

        self._set_step(
            event=event,
            step="awaiting_result",
            context_data={
                "task_uuid": task_uuid,
                "file_name": file_name,
            },
        )

        event.reply_text_message(
            MessageRequest(
                text=build_dadata_batch_started_screen(
                    file_name=file_name,
                    task_uuid=task_uuid,
                    total_rows=total_rows,
                ),
                buttons=[
                    InlineMessageButton(
                        id=1,
                        label=buttons.BTN_CHECK_TASK_STATUS,
                        callback_message="Проверка статуса",
                        callback_data="dadata_batch:check_status",
                    ),
                    InlineMessageButton(
                        id=2,
                        label=buttons.BTN_TO_MENU,
                        callback_message="Переход в меню",
                        callback_data="dadata_batch:menu",
                    ),
                ],
            )
        )
        return True

    def _show_status(self, router, event, context: dict) -> bool:
        task_uuid = context.get("task_uuid")
        if not task_uuid:
            event.reply_text(texts.DADATA_BATCH_TASK_NOT_FOUND_TEXT)
            return True

        with SessionLocal() as session:
            task = TaskRepository(session).get_by_uuid(task_uuid)

        if task is None:
            event.reply_text(texts.DADATA_BATCH_TASK_NOT_FOUND_DB_TEXT)
            return True

        status_map = {
            "queued": "⏳ В очереди",
            "running": "🔄 Выполняется",
            "done": "✅ Завершена",
            "failed": "❌ Ошибка",
        }
        status_text = status_map.get(task.status, task.status)

        if task.status == "done":
            buttons_list = [
                InlineMessageButton(
                    id=1,
                    label=buttons.BTN_TO_MENU,
                    callback_message="Переход в меню",
                    callback_data="dadata_batch:menu",
                ),
            ]
            event.reply_text_message(
                MessageRequest(
                    text=build_dadata_batch_done_screen(task),
                    buttons=buttons_list,
                )
            )
            self._send_result_file(event, task)
            return True

        if task.status == "failed":
            event.reply_text(
                f"{texts.DADATA_BATCH_TASK_FAILED_TEXT}\n\n"
                f"{task.error_text or 'Неизвестная ошибка'}"
            )
            return True

        progress_text = ""
        
        if task.progress_total and task.progress_total > 0:
            pct = int(task.progress_current / task.progress_total * 100)
            progress_text = f"📈 Прогресс: {task.progress_current}/{task.progress_total} ({pct}%)\n"

        event.reply_text_message(
            MessageRequest(
                text=(
                    f"🔄 Статус задачи:\n\n"
                    f"Состояние: {status_text}\n"
                    f"{progress_text}"
                    f"💬 {task.message or '-'}"
                ),
                buttons=[
                    InlineMessageButton(
                        id=1,
                        label="🔄 Обновить статус",
                        callback_message="dadata_batch:check_status",
                        callback_data="dadata_batch:check_status",
                    ),
                    InlineMessageButton(
                        id=2,
                        label="🏠 В меню",
                        callback_message="dadata_batch:menu",
                        callback_data="dadata_batch:menu",
                    ),
                ],
            )
        )
        return True

    def _send_result_file(self, event, task) -> None:
        result_file_path = task.result_file_path
        if not result_file_path or not os.path.exists(result_file_path):
            event.reply_text(texts.DADATA_BATCH_RESULT_FILE_NOT_FOUND_TEXT)
            return

        # Для P2P-чата TDM сейчас не дает надежно отправлять xlsx
        if event.workspace_id is None or event.workspace_id < 0:
            event.reply_text(
                texts.DADATA_BATCH_P2P_RESULT_WARNING_TEXT.format(
                    file_name=os.path.basename(result_file_path)
                )
            )
            return

        try:
            with open(result_file_path, "rb") as f:
                content = f.read()

            file_name = os.path.basename(result_file_path)

            from app.integrations.tdm_file_sender import TdmFileSender

            sender = TdmFileSender()
            success = sender.send_file(
                workspace_id=event.workspace_id,
                group_id=event.group_id,
                file_name=file_name,
                content=content,
                message_text="📎 Готовый результат обработки",
            )

            if success:
                self._clear_context(event)
                return

            event.reply_text(texts.DADATA_BATCH_RESULT_SEND_FAIL_TEXT)

        except Exception as e:
            import traceback
            error_text = f"{type(e).__name__}: {str(e)}"
            print("SEND RESULT FILE ERROR:", error_text, flush=True)
            print(traceback.format_exc(), flush=True)
            event.reply_text(f"❌ Ошибка при отправке файла: {error_text}")

    def _set_step(self, event, step: str, context_data: dict):
        with SessionLocal() as session:
            ContextManager(session).set_context(
                tdm_user_id=event.sender_id,
                workspace_id=event.workspace_id,
                group_id=event.group_id,
                active_service_code=self.code,
                step=step,
                context_data={"step": step, **context_data},
            )

    def _clear_context(self, event) -> None:
        with SessionLocal() as session:
            ContextManager(session).clear_context(event.sender_id)