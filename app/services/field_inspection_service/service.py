from typing import Optional

from messenger_bot_api.data_classes import InlineMessageButton
from messenger_bot_api.util import MessageRequest

from app.bot.context_manager import ContextManager
from app.db.session import SessionLocal
from app.repositories.field_inspection import FieldInspectionRepository
from app.repositories.users import UserRepository
from app.services.base import BaseService
from app.services.field_inspection_service.constants import (
    SERVICE_CODE,
    ROLE_CURATOR,
    ROLE_INSPECTOR,
)
from app.ui import buttons, texts
from app.ui.screens import (
    build_field_inspection_curator_screen,
    build_field_inspection_inspector_screen,
    build_field_inspection_no_profile_screen,
    build_field_inspection_campaign_list_screen,
    build_field_inspection_campaign_card_screen,
    build_field_inspection_task_list_screen,
    build_field_inspection_task_card_screen,
    build_field_inspection_progress_screen,
)


class FieldInspectionService(BaseService):
    code = SERVICE_CODE
    name = "Полевые проверки"
    description = "Управление проверками, заданиями инспекторам и фиксацией результатов"

    def start(self, router, event, context: Optional[dict] = None) -> None:
        with SessionLocal() as session:
            bot_user = UserRepository(session).get_by_tdm_user_id(event.sender_id)
            if not bot_user:
                event.reply_text(texts.FIELD_INSPECTION_PROFILE_NOT_FOUND_TEXT)
                return

            repo = FieldInspectionRepository(session)
            inspector = repo.get_inspector_by_bot_user_id(bot_user.id)

            if not inspector:
                self._set_step(event, "no_profile", {})
                event.reply_text(build_field_inspection_no_profile_screen())
                return

            role = inspector.get("role")
            self._set_step(
                event,
                "main_menu",
                {
                    "inspector_id": inspector["inspector_id"],
                    "role": role,
                },
            )

            if role == ROLE_CURATOR:
                self._show_curator_menu(event, inspector_id=inspector["inspector_id"])
                return

            else:
                self._show_inspector_menu(event, inspector_id=inspector["inspector_id"])
                return

            self._show_inspector_menu(event)

    def handle_message(self, router, event, context: Optional[dict] = None) -> bool:
        # На этапе FI-2 текстовый сценарий почти пустой
        context = context or {}
        step = context.get("step")

        if step == "no_profile":
            event.reply_text(texts.FIELD_INSPECTION_CONTACT_ADMIN_TEXT)
            return True

        event.reply_text(texts.FIELD_INSPECTION_USE_BUTTONS_TEXT)
        return True

    def handle_button(self, router, event, context: Optional[dict] = None) -> bool:
        callback_data = event.selected_button.callback_data if event.selected_button else None
        if callback_data in ("field_inspection:main", "field_inspection:back"):
            self.start(router, event, context=context)
            return True
            
        if not callback_data:
            return False

        context = context or {}
        role = context.get("role")

        if callback_data == "field_inspection:menu":
            self._clear_context(event)
            router.handle_menu(event)
            return True

        if callback_data == "field_inspection:main":
            if role == ROLE_CURATOR:
                self._show_curator_menu(event)
                return True
            if role == ROLE_INSPECTOR:
                self._show_inspector_menu(event)
                return True

            event.reply_text(build_field_inspection_no_profile_screen())
            return True

        if callback_data == "field_inspection:curator:create":
            event.reply_text(texts.FIELD_INSPECTION_CURATOR_CREATE_STUB_TEXT)
            return True

        if callback_data == "field_inspection:inspector:campaigns":
            inspector_id = context.get("inspector_id")
            if not inspector_id:
                event.reply_text(build_field_inspection_no_profile_screen())
                return True

            with SessionLocal() as session:
                repo = FieldInspectionRepository(session)
                campaigns = repo.get_campaigns_for_inspector(inspector_id)

            # кнопки на кампании
            buttons_list = []
            for idx, c in enumerate(campaigns[:10], start=1):
                buttons_list.append(
                    InlineMessageButton(
                        id=idx,
                        label=f"#{c['id']} {c.get('name') or 'Проверка'}",
                        callback_message="Открыта проверка",
                        callback_data=f"field_inspection:campaign:{c['id']}",
                    )
                )

            buttons_list.append(
                InlineMessageButton(
                    id=99,
                    label=buttons.BTN_FIELD_INSPECTION_BACK,
                    callback_message="Назад",
                    callback_data="field_inspection:main",
                )
            )

            event.reply_text_message(
                MessageRequest(
                    text=build_field_inspection_campaign_list_screen(campaigns),
                    buttons=buttons_list,
                )
            )
            return True

        if callback_data.startswith("field_inspection:campaign:"):
            campaign_id = int(callback_data.split(":")[-1])
            inspector_id = context.get("inspector_id")

            with SessionLocal() as session:
                repo = FieldInspectionRepository(session)
                campaign = repo.get_campaign_by_id(campaign_id)
                stats = repo.get_campaign_stats(campaign_id)

            if not campaign:
                event.reply_text("Проверка не найдена.")
                return True

            # сохраняем выбранную кампанию в контекст
            self._set_step(event, "campaign_card", {
                "role": context.get("role"),
                "inspector_id": inspector_id,
                "campaign_id": campaign_id,
            })

            event.reply_text_message(
                MessageRequest(
                    text=build_field_inspection_campaign_card_screen(campaign, stats),
                    buttons=[
                        InlineMessageButton(
                            id=1,
                            label=buttons.BTN_FIELD_INSPECTION_TASKS_IN_CAMPAIGN,
                            callback_message="Показаны задачи по проверке",
                            callback_data="field_inspection:inspector:tasks",
                        ),
                        InlineMessageButton(
                            id=2,
                            label=buttons.BTN_FIELD_INSPECTION_BACK,
                            callback_message="Назад",
                            callback_data="field_inspection:inspector:campaigns",
                        ),
                        InlineMessageButton(
                            id=3,
                            label=buttons.BTN_TO_MENU,
                            callback_message="В меню",
                            callback_data="field_inspection:menu",
                        ),
                    ],
                )
            )
            return True

        if callback_data.startswith("field_inspection:task:"):
            task_id = int(callback_data.split(":")[-1])

            with SessionLocal() as session:
                repo = FieldInspectionRepository(session)
                task = repo.get_task_by_id(task_id)

            if not task:
                event.reply_text("Задача не найдена.")
                return True

            event.reply_text_message(
                MessageRequest(
                    text=build_field_inspection_task_card_screen(task),
                    buttons=[
                        InlineMessageButton(
                            id=1,
                            label=buttons.BTN_FIELD_INSPECTION_BACK,
                            callback_message="Назад",
                            callback_data="field_inspection:inspector:tasks",
                        ),
                        InlineMessageButton(
                            id=2,
                            label=buttons.BTN_TO_MENU,
                            callback_message="В меню",
                            callback_data="field_inspection:menu",
                        ),
                    ],
                )
            )
            return True

        if callback_data == "field_inspection:curator:stats":
            event.reply_text(texts.FIELD_INSPECTION_CURATOR_STATS_STUB_TEXT)
            return True

        if callback_data == "field_inspection:inspector:campaigns":
            event.reply_text(texts.FIELD_INSPECTION_INSPECTOR_CAMPAIGNS_STUB_TEXT)
            return True

        if callback_data == "field_inspection:inspector:tasks":
            inspector_id = context.get("inspector_id")
            campaign_id = context.get("campaign_id")  # может быть None
            if not inspector_id:
                event.reply_text(build_field_inspection_no_profile_screen())
                return True

            with SessionLocal() as session:
                repo = FieldInspectionRepository(session)
                tasks = repo.get_tasks_for_inspector(inspector_id, campaign_id=campaign_id, limit=50)

            buttons_list = []
            for idx, t in enumerate(tasks[:10], start=1):
                name = t.get("object_name") or f"#{t['id']}"
                buttons_list.append(
                    InlineMessageButton(
                        id=idx,
                        label=f"#{t['id']} {name[:40]}",
                        callback_message="Открыта задача",
                        callback_data=f"field_inspection:task:{t['id']}",
                    )
                )

            buttons_list.append(
                InlineMessageButton(
                    id=98,
                    label=buttons.BTN_FIELD_INSPECTION_ALL_TASKS,
                    callback_message="Показаны все задачи",
                    callback_data="field_inspection:inspector:tasks_all",
                )
            )

            buttons_list.append(
                InlineMessageButton(
                    id=99,
                    label=buttons.BTN_FIELD_INSPECTION_BACK,
                    callback_message="Назад",
                    callback_data="field_inspection:main",
                )
            )

            event.reply_text_message(
                MessageRequest(
                    text=build_field_inspection_task_list_screen(tasks, campaign_id=campaign_id),
                    buttons=buttons_list,
                )
            )
            return True

        if callback_data == "field_inspection:inspector:progress":
            inspector_id = context.get("inspector_id")
            if not inspector_id:
                event.reply_text(build_field_inspection_no_profile_screen())
                return True

            with SessionLocal() as session:
                repo = FieldInspectionRepository(session)
                progress = repo.get_inspector_progress(inspector_id)

            event.reply_text_message(
                MessageRequest(
                    text=build_field_inspection_progress_screen(progress),
                    buttons=[
                        InlineMessageButton(
                            id=1,
                            label=buttons.BTN_FIELD_INSPECTION_BACK,
                            callback_message="Назад",
                            callback_data="field_inspection:main",
                        ),
                        InlineMessageButton(
                            id=2,
                            label=buttons.BTN_TO_MENU,
                            callback_message="В меню",
                            callback_data="field_inspection:menu",
                        ),
                    ],
                )
            )
            return True

        return False

        if callback_data == "field_inspection:inspector:tasks_all":
            inspector_id = context.get("inspector_id")
            if not inspector_id:
                event.reply_text(build_field_inspection_no_profile_screen())
                return True

            # сброс фильтра кампании
            self._set_step(event, "main_menu", {
                "role": context.get("role"),
                "inspector_id": inspector_id,
                "campaign_id": None,
            })

            with SessionLocal() as session:
                repo = FieldInspectionRepository(session)
                tasks = repo.get_tasks_for_inspector(inspector_id, campaign_id=None, limit=50)

            buttons_list = []
            for idx, t in enumerate(tasks[:10], start=1):
                name = t.get("object_name") or f"#{t['id']}"
                buttons_list.append(
                    InlineMessageButton(
                        id=idx,
                        label=f"#{t['id']} {name[:40]}",
                        callback_message="Открыта задача",
                        callback_data=f"field_inspection:task:{t['id']}",
                    )
                )

            buttons_list.append(
                InlineMessageButton(
                    id=99,
                    label=buttons.BTN_FIELD_INSPECTION_BACK,
                    callback_message="Назад",
                    callback_data="field_inspection:main",
                )
            )

            event.reply_text_message(
                MessageRequest(
                    text=build_field_inspection_task_list_screen(tasks, campaign_id=None),
                    buttons=buttons_list,
                )
            )
            return True



    def _show_curator_menu(self, event, inspector_id: int) -> None:
        self._set_step(event, "main_menu", {"role": ROLE_CURATOR, "inspector_id": inspector_id})

        event.reply_text_message(
            MessageRequest(
                text=build_field_inspection_curator_screen(),
                buttons=[
                    InlineMessageButton(
                        id=1,
                        label=buttons.BTN_FIELD_INSPECTION_CREATE,
                        callback_message="Создание проверки",
                        callback_data="field_inspection:curator:create",
                    ),
                    InlineMessageButton(
                        id=2,
                        label=buttons.BTN_FIELD_INSPECTION_CAMPAIGNS,
                        callback_message="Мои проверки",
                        callback_data="field_inspection:curator:campaigns",
                    ),
                    InlineMessageButton(
                        id=3,
                        label=buttons.BTN_FIELD_INSPECTION_STATS,
                        callback_message="Статистика",
                        callback_data="field_inspection:curator:stats",
                    ),
                    InlineMessageButton(
                        id=4,
                        label=buttons.BTN_TO_MENU,
                        callback_message="Переход в меню",
                        callback_data="field_inspection:menu",
                    ),
                ],
            )
        )

    def _show_inspector_menu(self, event, inspector_id: int) -> None:
        self._set_step(event, "main_menu", {"role": ROLE_INSPECTOR, "inspector_id": inspector_id})

        event.reply_text_message(
            MessageRequest(
                text=build_field_inspection_inspector_screen(),
                buttons=[
                    InlineMessageButton(
                        id=1,
                        label=buttons.BTN_FIELD_INSPECTION_CAMPAIGNS,
                        callback_message="Мои проверки",
                        callback_data="field_inspection:inspector:campaigns",
                    ),
                    InlineMessageButton(
                        id=2,
                        label=buttons.BTN_FIELD_INSPECTION_TASKS,
                        callback_message="Мои задачи",
                        callback_data="field_inspection:inspector:tasks",
                    ),
                    InlineMessageButton(
                        id=3,
                        label=buttons.BTN_FIELD_INSPECTION_PROGRESS,
                        callback_message="Мой прогресс",
                        callback_data="field_inspection:inspector:progress",
                    ),
                    InlineMessageButton(
                        id=4,
                        label=buttons.BTN_TO_MENU,
                        callback_message="Переход в меню",
                        callback_data="field_inspection:menu",
                    ),
                ],
            )
        )

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

    def _clear_context(self, event):
        with SessionLocal() as session:
            ContextManager(session).clear_context(event.sender_id)