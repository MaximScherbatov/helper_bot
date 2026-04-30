from typing import Optional

from messenger_bot_api.data_classes import InlineMessageButton
from messenger_bot_api.util import MessageRequest
#from sqlalchemy import text

from app.bot.context_manager import ContextManager
from app.db.session import SessionLocal
from app.repositories.users import UserRepository
from app.repositories.service_access import ServiceAccessRepository
from app.services.base import BaseService

from sqlalchemy import select
from app.db.models import BotUser
from app.ui import texts, buttons
from app.ui.screens import (
    build_admin_console_intro_screen,
    build_admin_grant_access_screen,
    build_admin_revoke_access_screen,
    build_admin_user_card_screen,
    build_admin_user_list_screen,
)

class AdminConsoleService(BaseService):
    code = "admin_console"
    name = "🛠 Панель администратора"
    description = "Управление пользователями и доступами"

    def start(self, router, event, context: Optional[dict] = None) -> None:
        self._set_step(event, "menu", {})
        self._show_menu(event)

    def handle_button(self, router, event, context: Optional[dict] = None) -> bool:
        callback = event.selected_button.callback_data if event.selected_button else None
        if not callback:
            return False

        context = context or {}

        if callback == "admin:menu":
            self._clear_context(event)
            router.handle_menu(event)
            return True

        if callback == "admin:main":
            self._set_step(event, "menu", {})
            self._show_menu(event)
            return True

        if callback == "admin:list_users":
            return self._list_users(event)

        if callback == "admin:find_user":
            self._set_step(event, "awaiting_user_id", {})
            event.reply_text(texts.ADMIN_CONSOLE_FIND_USER_TEXT)
            return True

        if callback == "admin:grant_access":
            target_user_id = context.get("target_user_id")
            if not target_user_id:
                event.reply_text(texts.ADMIN_CONSOLE_NO_TARGET_USER_TEXT)
                return True
            return self._show_services_for_grant(event, target_user_id)

        if callback == "admin:revoke_access":
            target_user_id = context.get("target_user_id")
            if not target_user_id:
                event.reply_text(texts.ADMIN_CONSOLE_NO_TARGET_USER_TEXT)
                return True
            return self._show_services_for_revoke(event, target_user_id)

        if callback.startswith("admin:grant_service:"):
            service_id = int(callback.split(":")[-1])
            target_user_id = context.get("target_user_id")
            if not target_user_id:
                event.reply_text(texts.ADMIN_CONSOLE_NO_TARGET_FOR_ACTION_TEXT)
                return True

            self._set_step(
                event,
                "awaiting_grant_days",
                {
                    "target_user_id": target_user_id,
                    "service_id": service_id,
                },
            )

            event.reply_text_message(
                MessageRequest(
                    text=texts.ADMIN_CONSOLE_GRANT_DAYS_TEXT,
                    buttons=[
                        InlineMessageButton(
                            id=1,
                            label=buttons.BTN_ADMIN_7_DAYS,
                            callback_message="Срок 7 дней",
                            callback_data="admin:grant_days:7",
                        ),
                        InlineMessageButton(
                            id=2,
                            label=buttons.BTN_ADMIN_30_DAYS,
                            callback_message="Срок 30 дней",
                            callback_data="admin:grant_days:30",
                        ),
                        InlineMessageButton(
                            id=3,
                            label=buttons.BTN_ADMIN_90_DAYS,
                            callback_message="Срок 90 дней",
                            callback_data="admin:grant_days:90",
                        ),
                        InlineMessageButton(
                            id=4,
                            label=buttons.BTN_ADMIN_UNLIMITED,
                            callback_message="Бессрочный доступ",
                            callback_data="admin:grant_days:0",
                        ),
                    ],
                )
            )
            return True

        if callback.startswith("admin:grant_days:"):
            days = int(callback.split(":")[-1])
            return self._grant_access_by_selected_service(event, context, days)

        if callback.startswith("admin:revoke_service:"):
            service_id = int(callback.split(":")[-1])
            target_user_id = context.get("target_user_id")
            return self._revoke_access_by_selected_service(event, target_user_id, service_id)

        return False

    def handle_message(self, router, event, context: Optional[dict] = None) -> bool:
        context = context or {}
        step = context.get("step")

        if step == "awaiting_user_id":
            return self._show_user_card(event)

        if step == "awaiting_grant_days":
            days_text = (event.message_text or "").strip()
            if not days_text.isdigit():
                event.reply_text(texts.ADMIN_CONSOLE_INVALID_DAYS_TEXT)
                return True

            days = int(days_text)
            return self._grant_access_by_selected_service(event, context, days)

        return False

    def _show_menu(self, event):
        event.reply_text_message(
            MessageRequest(
                text=build_admin_console_intro_screen(),
                buttons=[
                    InlineMessageButton(
                        id=1,
                        label=buttons.BTN_ADMIN_USERS,
                        callback_message="Показан список пользователей",
                        callback_data="admin:list_users",
                    ),
                    InlineMessageButton(
                        id=2,
                        label=buttons.BTN_ADMIN_FIND_USER,
                        callback_message="Поиск пользователя",
                        callback_data="admin:find_user",
                    ),
                    InlineMessageButton(
                        id=3,
                        label=buttons.BTN_TO_MENU,
                        callback_message="Переход в меню",
                        callback_data="admin:menu",
                    ),
                ],
            )
        )

    def _list_users(self, event):
        try:
            with SessionLocal() as session:
                users = list(
                    session.scalars(
                        select(BotUser)
                        .order_by(BotUser.id.desc())
                        .limit(20)
                    )
                )

                event.reply_text(build_admin_user_list_screen(users))
                return True

        except Exception as e:
            import traceback
            print("ADMIN LIST USERS ERROR:", str(e), flush=True)
            print(traceback.format_exc(), flush=True)
            event.reply_text(f"Ошибка при получении списка пользователей: {e}")
            return True

    def _show_user_card(self, event):
        tdm_id = (event.message_text or "").strip()
        if not tdm_id.isdigit():
            event.reply_text(texts.ADMIN_CONSOLE_INVALID_USER_ID_TEXT)
            return True

        with SessionLocal() as session:
            user_repo = UserRepository(session)
            access_repo = ServiceAccessRepository(session)

            user = user_repo.get_by_tdm_user_id(int(tdm_id))
            if not user:
                event.reply_text(texts.ADMIN_CONSOLE_USER_NOT_FOUND_TEXT)
                return True

            roles = user_repo.get_role_codes(user.id)
            access_rows = access_repo.get_active_user_accesses(user.id)
            services = {svc.id: svc for svc in access_repo.list_services()}

            access_items = []
            for access in access_rows:
                service = services.get(access.service_id)
                service_name = service.name if service else f"id={access.service_id}"
                expires = access.expires_at.date().isoformat() if access.expires_at else None
                access_items.append(
                    {
                        "service_name": service_name,
                        "expires_at": expires,
                    }
                )

            self._set_step(
                event,
                "user_card",
                {
                    "target_user_id": user.id,
                    "target_tdm_user_id": user.tdm_user_id,
                },
            )

            event.reply_text_message(
                MessageRequest(
                    text=build_admin_user_card_screen(
                        user=user,
                        roles=roles,
                        access_items=access_items,
                    ),
                    buttons=[
                        InlineMessageButton(
                            id=1,
                            label=buttons.BTN_ADMIN_GRANT_ACCESS,
                            callback_message="Выдача доступа",
                            callback_data="admin:grant_access",
                        ),
                        InlineMessageButton(
                            id=2,
                            label=buttons.BTN_ADMIN_REVOKE_ACCESS,
                            callback_message="Отзыв доступа",
                            callback_data="admin:revoke_access",
                        ),
                        InlineMessageButton(
                            id=3,
                            label=buttons.BTN_ADMIN_MAIN,
                            callback_message="Возврат в панель администратора",
                            callback_data="admin:main",
                        ),
                    ],
                )
            )
            return True

    def _show_services_for_grant(self, event, target_user_id: int):
        with SessionLocal() as session:
            access_repo = ServiceAccessRepository(session)
            services = access_repo.list_services()

            self._set_step(
                event,
                "select_service_for_grant",
                {"target_user_id": target_user_id},
            )

            buttons_list = []
            for idx, service in enumerate(services, start=1):
                buttons_list.append(
                    InlineMessageButton(
                        id=idx,
                        label=service.name,
                        callback_message=f"Выбран сервис {service.name}",
                        callback_data=f"admin:grant_service:{service.id}",
                    )
                )

            buttons_list.append(
                InlineMessageButton(
                    id=999,
                    label=buttons.BTN_ADMIN_BACK,
                    callback_message="Возврат к карточке пользователя",
                    callback_data="admin:main",
                )
            )

            event.reply_text_message(
                MessageRequest(
                    text=build_admin_grant_access_screen(),
                    buttons=buttons_list,
                )
            )
            return True

    def _show_services_for_revoke(self, event, target_user_id: int):
        with SessionLocal() as session:
            access_repo = ServiceAccessRepository(session)
            active_accesses = access_repo.get_active_user_accesses(target_user_id)
            services = {svc.id: svc for svc in access_repo.list_services()}

            if not active_accesses:
                event.reply_text(texts.ADMIN_CONSOLE_NO_ACTIVE_ACCESS_TEXT)
                return True

            buttons_list = []
            for idx, access in enumerate(active_accesses, start=1):
                service = services.get(access.service_id)
                if not service:
                    continue

                buttons_list.append(
                    InlineMessageButton(
                        id=idx,
                        label=service.name,
                        callback_message=f"Отзыв доступа к {service.name}",
                        callback_data=f"admin:revoke_service:{service.id}",
                    )
                )

            buttons_list.append(
                InlineMessageButton(
                    id=999,
                    label=buttons.BTN_ADMIN_BACK,
                    callback_message="Возврат к карточке пользователя",
                    callback_data="admin:main",
                )
            )

            event.reply_text_message(
                MessageRequest(
                    text=build_admin_revoke_access_screen(),
                    buttons=buttons_list,
                )
            )
            return True

    def _grant_access_by_selected_service(self, event, context: dict, days: int):
        target_user_id = context.get("target_user_id")
        service_id = context.get("service_id")

        if not target_user_id or not service_id:
            event.reply_text(texts.ADMIN_CONSOLE_NOT_ENOUGH_DATA_TEXT)
            return True

        with SessionLocal() as session:
            access_repo = ServiceAccessRepository(session)
            admin_user = UserRepository(session).get_by_tdm_user_id(event.sender_id)
            services = {svc.id: svc for svc in access_repo.list_services()}
            service = services.get(service_id)

            if service is None:
                event.reply_text(texts.ADMIN_CONSOLE_SERVICE_NOT_FOUND_TEXT)
                return True

            access_repo.grant_access(
                user_id=target_user_id,
                service_id=service_id,
                granted_by_user_id=admin_user.id if admin_user else None,
                access_role="user",
                days=None if days == 0 else days,
                comment="Выдано через admin_console",
            )

            self._set_step(event, "menu", {})
            event.reply_text(
                f"{texts.ADMIN_CONSOLE_ACCESS_GRANTED_TEXT}\n\n"
                f"Сервис: {service.name}\n"
                f"Срок: {'без ограничения' if days == 0 else str(days) + ' дней'}"
            )
            return True

    def _revoke_access_by_selected_service(self, event, target_user_id: int, service_id: int):
        if not target_user_id or not service_id:
            event.reply_text(texts.ADMIN_CONSOLE_NOT_ENOUGH_DATA_TEXT)
            return True

        with SessionLocal() as session:
            access_repo = ServiceAccessRepository(session)
            services = {svc.id: svc for svc in access_repo.list_services()}
            service = services.get(service_id)

            if service is None:
                event.reply_text(texts.ADMIN_CONSOLE_SERVICE_NOT_FOUND_TEXT)
                return True

            ok = access_repo.revoke_access(
                user_id=target_user_id,
                service_id=service_id,
            )

            self._set_step(event, "menu", {})

            if ok:
                event.reply_text(
                    f"{texts.ADMIN_CONSOLE_ACCESS_REVOKED_TEXT}\n\n"
                    f"Сервис: {service.name}"
                )
            else:
                event.reply_text(
                    f"{texts.ADMIN_CONSOLE_ACCESS_NOT_FOUND_TEXT}\n\n"
                    f"Сервис: {service.name}"
                )

            return True

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