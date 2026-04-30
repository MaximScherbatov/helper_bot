from app.ui import texts
from typing import Any, Optional
from app.utils.okved import okved_description

def compose_screen(title: str | None, body: str, footer: str | None = None) -> str:
    parts = []
    if title:
        parts.append(title)
    if body:
        parts.append(body)
    if footer:
        parts.append(footer)
    return "\n\n".join(parts)


def build_start_screen() -> str:
    return compose_screen(
        title=texts.START_TITLE,
        body=texts.START_TEXT,
    )


def build_help_screen() -> str:
    return compose_screen(
        title=texts.HELP_TITLE,
        body=texts.HELP_TEXT,
    )


def build_menu_screen() -> str:
    return compose_screen(
        title=texts.MENU_TITLE,
        body=texts.MENU_TEXT,
    )


def build_status_screen(context) -> str:
    if context is None:
        return compose_screen(
            title="🧭 Текущий статус",
            body="Активный сценарий отсутствует.",
        )

    service_code = context.active_service_code or "—"
    step = context.step or "—"

    details_lines = [
        f"Сервис: {service_code}",
        f"Шаг: {step}",
    ]

    if context.context_data:
        details_lines.append(f"Данные контекста: {context.context_data}")

    return compose_screen(
        title="🧭 Текущий статус",
        body="\n".join(details_lines),
    )


def build_tasks_screen(tasks: list) -> str:
    if not tasks:
        return compose_screen(
            title="📦 Последние задачи",
            body=texts.EMPTY_TASKS_TEXT,
        )

    blocks = []
    for task in tasks:
        progress = (
            f"{task.progress_current}/{task.progress_total}"
            if task.progress_total
            else str(task.progress_current)
        )
        blocks.append(
            "\n".join(
                [
                    f"ID: {task.task_uuid}",
                    f"Сервис: {task.service_code}",
                    f"Тип: {task.task_type}",
                    f"Статус: {task.status}",
                    f"Прогресс: {progress}",
                    f"Комментарий: {task.message or '—'}",
                ]
            )
        )

    return compose_screen(
        title="📦 Последние задачи",
        body="\n\n".join(blocks),
    )


def build_whoami_screen(tdm_user_id: int, user_id: int, roles: list[str]) -> str:
    return compose_screen(
        title="👤 Профиль пользователя",
        body="\n".join(
            [
                f"TDM ID: {tdm_user_id}",
                f"Внутренний ID: {user_id}",
                f"Роли: {', '.join(roles) if roles else '—'}",
            ]
        ),
    )



def build_dadata_intro_screen() -> str:
    return compose_screen(
        title=texts.DADATA_TITLE,
        body=texts.DADATA_INTRO_TEXT,
    )


def build_dadata_variants_screen(
    variants: list[dict],
    page: int,
    page_size: int,
) -> str:
    if not variants:
        return compose_screen(
            title=texts.DADATA_TITLE,
            body=texts.DADATA_PAGE_EMPTY_TEXT,
        )

    start = page * page_size
    end = start + page_size
    page_items = variants[start:end]

    if not page_items:
        return compose_screen(
            title=texts.DADATA_TITLE,
            body=texts.DADATA_PAGE_EMPTY_TEXT,
        )

    total = len(variants)
    total_pages = (total + page_size - 1) // page_size

    moscow_count = sum(1 for v in variants if v["priority"] == 0)
    mo_count = sum(1 for v in variants if v["priority"] == 1)
    regions_count = sum(1 for v in variants if v["priority"] == 2)

    lines = [
        f"Найдено организаций: {total}",
        f"Москва — {moscow_count}, Московская область — {mo_count}, регионы — {regions_count}",
        f"Страница {page + 1} из {total_pages}",
        "",
    ]

    for item in page_items:
        real_idx = variants.index(item)
        lines.append(
            "\n".join(
                [
                    f"{real_idx + 1}. {item['label']}",
                    f"ИНН: {item['inn']}",
                    f"Адрес: {truncate_text(item['address'], 110)}",
                ]
            )
        )

    lines.append("")
    lines.append("Выберите организацию с помощью кнопок ниже.")

    return compose_screen(
        title=texts.DADATA_TITLE,
        body="\n\n".join(lines),
    )


def build_dadata_result_screen(
    response_json: dict,
    from_cache: bool = False,
    continue_hint: bool = True,
) -> str:
    suggestions = response_json.get("suggestions", [])
    if not suggestions:
        return compose_screen(
            title=texts.DADATA_TITLE,
            body=texts.DADATA_NOT_FOUND_TEXT,
        )

    suggestion = suggestions[0]
    data = suggestion.get("data", {}) or {}
    name_data = data.get("name", {}) or {}
    address_data = data.get("address", {}) or {}
    management_data = data.get("management", {}) or {}
    state_data = data.get("state", {}) or {}

    company_short = (
        name_data.get("short_with_opf")
        or suggestion.get("value")
        or "Без названия"
    )
    company_full = safe_value(name_data.get("full_with_opf"))
    inn = safe_value(data.get("inn"))
    ogrn = safe_value(data.get("ogrn"))
    kpp = safe_value(data.get("kpp"))
    address = safe_value(address_data.get("value"))
    postal_code = safe_value(address_data.get("data", {}).get("postal_code"))
    manager = format_management_names(management_data)
    manager_post = safe_value(management_data.get("post"))
    okved = safe_value(data.get("okved"))
    okved_desc = okved_description(okved)
    okved_line = f"🧩 ОКВЭД: {okved}"
    if okved_desc:
        okved_line += f" — {okved_desc}"
    org_status = format_status(state_data.get("status"))
    registration_date = format_timestamp_ms(state_data.get("registration_date"))
    liquidation_date = format_timestamp_ms(state_data.get("liquidation_date"))

    lines = [
        f"🏢 {company_short}",
        f"📘 {company_full}",
        "",
        f"🆔 ИНН: {inn}",
        f"🆔 ОГРН: {ogrn}",
        f"🆔 КПП: {kpp}",
        "",
        f"📊 Статус: {org_status}",
        f"📅 Регистрация: {registration_date}",
        f"📅 Ликвидация: {liquidation_date}",
        "",
        f"📍 Адрес: {address}",
        f"📮 Индекс: {postal_code}",
        "",
        f"👤 Руководитель: {manager}",
        f"💼 Должность: {manager_post}",
        okved_line,
    ]

    if from_cache:
        lines.extend(["", f"🗂 {texts.DADATA_CACHE_MARK}"])

    if continue_hint:
        lines.extend(["", f"💬 {texts.DADATA_CONTINUE_HINT}"])

    return compose_screen(
        title=texts.DADATA_TITLE,
        body="\n".join(lines),
    )


def safe_value(value: Any, default: str = "—") -> str:
    if value is None:
        return default
    if value == "":
        return default
    if str(value).lower() == "none":
        return default
    return str(value)


def truncate_text(text: str, max_len: int) -> str:
    text = safe_value(text, "")
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def format_timestamp_ms(value: Any) -> str:
    from datetime import datetime

    if value in (None, "", "None"):
        return "—"
    try:
        value_int = int(value)
        if value_int <= 0:
            return "—"
        dt = datetime.utcfromtimestamp(value_int / 1000)
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return safe_value(value)


def format_status(value: Any) -> str:
    mapping = {
        "ACTIVE": "Действующая",
        "LIQUIDATING": "В процессе ликвидации",
        "LIQUIDATED": "Ликвидирована",
        "BANKRUPT": "Банкротство",
        "REORGANIZING": "В процессе реорганизации",
    }
    value = safe_value(value)
    return mapping.get(value, value)


def format_management_names(management_data: Any) -> str:
    if management_data is None:
        return "—"

    if isinstance(management_data, dict):
        name = management_data.get("name")
        if isinstance(name, list):
            values = [safe_value(x, "") for x in name if safe_value(x, "")]
            return ", ".join(values) if values else "—"
        if isinstance(name, str):
            return safe_value(name)

        names = []
        for key, value in management_data.items():
            if "name" in str(key).lower():
                if isinstance(value, list):
                    names.extend([safe_value(x, "") for x in value if safe_value(x, "")])
                elif isinstance(value, str):
                    names.append(safe_value(value, ""))
        names = [x for x in names if x]
        return ", ".join(names) if names else "—"

    if isinstance(management_data, list):
        names = []
        for item in management_data:
            if isinstance(item, dict):
                names.append(safe_value(item.get("name"), ""))
            else:
                names.append(safe_value(item, ""))
        names = [x for x in names if x]
        return ", ".join(names) if names else "—"

    return safe_value(management_data)



def build_dadata_batch_intro_screen(show_p2p_warning: bool = False) -> str:
    body_parts = []
    if show_p2p_warning:
        body_parts.append(texts.DADATA_BATCH_P2P_WARNING_TEXT)
    body_parts.append(texts.DADATA_BATCH_INTRO_TEXT)

    return compose_screen(
        title=texts.DADATA_BATCH_TITLE,
        body="\n\n".join(body_parts),
    )


def build_dadata_batch_analysis_screen(file_name: str, estimate: dict) -> str:
    limit_status = (
        texts.DADATA_BATCH_LIMIT_OK_TEXT
        if estimate.get("enough_tokens")
        else texts.DADATA_BATCH_LIMIT_WARNING_TEXT
    )

    body = "\n".join(
        [
            f"Файл: {file_name}",
            "",
            f"Всего строк: {estimate.get('total_rows', 0)}",
            f"Уникальных запросов: {estimate.get('unique_queries', 0)}",
            f"Найдено в кэше: {estimate.get('cache_hits', 0)}",
            f"Потребуется API-вызовов: {estimate.get('required_api_calls', 0)}",
            f"Доступно токенов сегодня: {estimate.get('available_tokens', 0)}",
            "",
            limit_status,
            "",
            texts.DADATA_BATCH_CONFIRM_TEXT,
        ]
    )

    return compose_screen(
        title=texts.DADATA_BATCH_ANALYSIS_TITLE,
        body=body,
    )


def build_dadata_batch_started_screen(file_name: str, task_uuid: str, total_rows: int) -> str:
    short_task_id = task_uuid[:8]
    body = "\n".join(
        [
            texts.DADATA_BATCH_TASK_STARTED_TEXT,
            "",
            f"Файл: {file_name}",
            f"Строк к обработке: {total_rows}",
            f"ID задачи: {short_task_id}...",
            "",
            "Используйте кнопку ниже, чтобы проверить статус.",
        ]
    )

    return compose_screen(
        title=texts.DADATA_BATCH_STARTED_TITLE,
        body=body,
    )


def build_dadata_batch_status_screen(task) -> str:
    status_map = {
        "queued": "В очереди",
        "running": "Выполняется",
        "done": "Завершена",
        "failed": "Ошибка",
    }

    status_text = status_map.get(task.status, task.status)

    lines = [f"Состояние: {status_text}"]

    if task.progress_total and task.progress_total > 0:
        pct = int(task.progress_current / task.progress_total * 100)
        lines.append(
            f"Прогресс: {task.progress_current}/{task.progress_total} ({pct}%)"
        )

    lines.append(f"Комментарий: {task.message or '—'}")

    return compose_screen(
        title=texts.DADATA_BATCH_STATUS_TITLE,
        body="\n".join(lines),
    )


def build_dadata_batch_done_screen(task) -> str:
    body = "\n".join(
        [
            texts.DADATA_BATCH_TASK_DONE_TEXT,
            "",
            f"Обработано строк: {task.progress_current}",
            texts.DADATA_BATCH_RESULT_SENDING_TEXT,
        ]
    )

    return compose_screen(
        title=texts.DADATA_BATCH_DONE_TITLE,
        body=body,
    )

def build_admin_console_intro_screen() -> str:
    return compose_screen(
        title=texts.ADMIN_CONSOLE_TITLE,
        body=texts.ADMIN_CONSOLE_INTRO_TEXT,
    )


def build_admin_user_list_screen(users: list) -> str:
    if not users:
        return compose_screen(
            title=texts.ADMIN_CONSOLE_TITLE,
            body=texts.ADMIN_CONSOLE_NO_USERS_TEXT,
        )

    lines = ["Последние пользователи:", ""]
    for user in users:
        name = user.display_name or f"user_{user.tdm_user_id}"
        lines.append(f"TDM ID: {user.tdm_user_id} — {name}")

    return compose_screen(
        title=texts.ADMIN_CONSOLE_TITLE,
        body="\n".join(lines),
    )


def build_admin_user_card_screen(user, roles: list[str], access_items: list[dict]) -> str:
    name = user.display_name or f"user_{user.tdm_user_id}"

    lines = [
        f"👤 {name}",
        f"TDM ID: {user.tdm_user_id}",
        f"Внутренний ID: {user.id}",
        f"Роли: {', '.join(roles) if roles else '—'}",
        "",
        "🔐 Активные доступы:",
    ]

    if not access_items:
        lines.append("Нет активных доступов.")
    else:
        for item in access_items:
            expires = item["expires_at"] or "без ограничения"
            lines.append(f"• {item['service_name']} — до {expires}")

    return compose_screen(
        title=texts.ADMIN_CONSOLE_TITLE,
        body="\n".join(lines),
    )


def build_admin_grant_access_screen() -> str:
    return compose_screen(
        title=texts.ADMIN_CONSOLE_TITLE,
        body="Выберите сервис для выдачи доступа.",
    )


def build_admin_revoke_access_screen() -> str:
    return compose_screen(
        title=texts.ADMIN_CONSOLE_TITLE,
        body="Выберите сервис для отзыва доступа.",
    )


def build_field_inspection_intro_screen() -> str:
    return compose_screen(
        title=texts.FIELD_INSPECTION_TITLE,
        body=texts.FIELD_INSPECTION_INTRO_TEXT,
    )


def build_field_inspection_no_profile_screen() -> str:
    return compose_screen(
        title=texts.FIELD_INSPECTION_TITLE,
        body=texts.FIELD_INSPECTION_NO_PROFILE_TEXT,
    )


def build_field_inspection_curator_screen() -> str:
    return compose_screen(
        title=texts.FIELD_INSPECTION_TITLE,
        body=texts.FIELD_INSPECTION_CURATOR_TEXT,
    )


def build_field_inspection_inspector_screen() -> str:
    return compose_screen(
        title=texts.FIELD_INSPECTION_TITLE,
        body=texts.FIELD_INSPECTION_INSPECTOR_TEXT,
    )


def _fmt_date(d) -> str:
    if not d:
        return "—"
    try:
        return d.isoformat()
    except Exception:
        return str(d)


def _status_ru(status: str | None) -> str:
    mapping = {
        "assigned": "Назначено",
        "in_progress": "В работе",
        "completed": "Выполнено",
        "done": "Выполнено",
    }
    if not status:
        return "—"
    return mapping.get(status, status)


def build_field_inspection_campaign_list_screen(campaigns: list[dict]) -> str:
    if not campaigns:
        return compose_screen(
            title=texts.FIELD_INSPECTION_MY_CAMPAIGNS_TITLE,
            body=texts.FIELD_INSPECTION_EMPTY_CAMPAIGNS_TEXT,
        )

    blocks = []
    for c in campaigns[:20]:
        total = int(c.get("total_tasks") or 0)
        done = int(c.get("completed_tasks") or 0)
        pct = int(done / total * 100) if total else 0
        blocks.append(
            "\n".join(
                [
                    f"#{c['id']} — {c.get('name') or 'Без названия'}",
                    f"Период: {_fmt_date(c.get('date_start'))} — {_fmt_date(c.get('date_end'))}",
                    f"Прогресс: {done}/{total} ({pct}%)",
                ]
            )
        )

    return compose_screen(
        title=texts.FIELD_INSPECTION_MY_CAMPAIGNS_TITLE,
        body="\n\n".join(blocks) + "\n\n" + texts.FIELD_INSPECTION_SELECT_CAMPAIGN_HINT,
    )


def build_field_inspection_campaign_card_screen(campaign: dict, stats: dict) -> str:
    total = int(stats.get("total_tasks") or 0)
    done = int(stats.get("completed_tasks") or 0)
    in_progress = int(stats.get("in_progress_tasks") or 0)
    assigned = int(stats.get("assigned_tasks") or 0)
    pct = int(done / total * 100) if total else 0

    body = "\n".join(
        [
            f"🗂 #{campaign['id']} — {campaign.get('name') or 'Без названия'}",
            "",
            (campaign.get("description") or "").strip() or "Описание: —",
            "",
            f"📅 Период: {_fmt_date(campaign.get('date_start'))} — {_fmt_date(campaign.get('date_end'))}",
            f"📌 Статус задач: назначено {assigned}, в работе {in_progress}, выполнено {done}",
            f"📊 Прогресс: {done}/{total} ({pct}%)",
        ]
    )

    return compose_screen(
        title=texts.FIELD_INSPECTION_CAMPAIGN_CARD_TITLE,
        body=body,
    )


def build_field_inspection_task_list_screen(tasks: list[dict], campaign_id: int | None = None) -> str:
    if not tasks:
        return compose_screen(
            title=texts.FIELD_INSPECTION_MY_TASKS_TITLE,
            body=texts.FIELD_INSPECTION_EMPTY_TASKS_TEXT,
        )

    blocks = []
    for t in tasks[:20]:
        name = t.get("object_name") or f"{t.get('object_type') or 'object'} #{t.get('object_id')}"
        addr = t.get("address") or "—"
        status = _status_ru(t.get("status"))
        blocks.append(
            "\n".join(
                [
                    f"Задача #{t['id']} — {name}",
                    f"Адрес: {addr}",
                    f"Статус: {status}",
                ]
            )
        )

    header = texts.FIELD_INSPECTION_MY_TASKS_TITLE
    if campaign_id:
        header = f"{texts.FIELD_INSPECTION_MY_TASKS_TITLE} (проверка #{campaign_id})"

    return compose_screen(
        title=header,
        body="\n\n".join(blocks) + "\n\n" + texts.FIELD_INSPECTION_SELECT_TASK_HINT,
    )


def build_field_inspection_task_card_screen(task: dict) -> str:
    name = task.get("object_name") or f"{task.get('object_type') or 'object'} #{task.get('object_id')}"
    addr = task.get("address") or "—"
    district = task.get("district_name") or "—"
    status = _status_ru(task.get("status"))

    body = "\n".join(
        [
            f"🏠 Задача #{task['id']}",
            f"Объект: {name}",
            "",
            f"📍 Адрес: {addr}",
            f"🗺 Район: {district}",
            f"📌 Статус: {status}",
            "",
            texts.FIELD_INSPECTION_TASK_ACTIONS_STUB,
        ]
    )

    return compose_screen(
        title=texts.FIELD_INSPECTION_TASK_CARD_TITLE,
        body=body,
    )


def build_field_inspection_progress_screen(progress: dict) -> str:
    total = int(progress.get("total_tasks") or 0)
    done = int(progress.get("completed_tasks") or 0)
    in_progress = int(progress.get("in_progress_tasks") or 0)
    assigned = int(progress.get("assigned_tasks") or 0)
    pct = int(done / total * 100) if total else 0

    body = "\n".join(
        [
            f"Всего задач: {total}",
            f"Назначено: {assigned}",
            f"В работе: {in_progress}",
            f"Выполнено: {done}",
            "",
            f"Готовность: {pct}%",
        ]
    )

    return compose_screen(
        title=texts.FIELD_INSPECTION_MY_PROGRESS_TITLE,
        body=body,
    )