# app/ui/texts.py

START_TITLE = "👋 Добро пожаловать"

START_TEXT = (
    "Я корпоративный бот-ассистент.\n\n"
    "В боте доступны рабочие сервисы: поиск данных, пакетная обработка, "
    "администрирование и другие инструменты.\n\n"
    "Основные команды:\n"
    "/menu — открыть меню\n"
    "/help — помощь\n"
    "/status — показать текущий сценарий\n"
    "/cancel — завершить текущий сценарий\n"
    "/resume — продолжить текущий сценарий\n"
    "/whoami — показать ваш TDM ID\n\n"
    "Чтобы начать работу, откройте меню."
)

HELP_TITLE = "ℹ️ Помощь"

HELP_TEXT = (
    "Бот поддерживает сценарную работу с сервисами.\n\n"
    "Основные команды:\n"
    "/start — стартовый экран\n"
    "/menu — доступные сервисы\n"
    "/status — текущий сценарий\n"
    "/cancel — завершить текущий сценарий\n"
    "/resume — продолжить текущий сценарий\n"
    "/whoami — показать ваш TDM ID\n"
    "/tasks — показать последние задачи\n\n"
    "Если бот находится не в том сценарии, используйте /cancel и начните заново.\n"
    "Если нужен нужный раздел — откройте /menu."
)

MENU_TITLE = "📌 Главное меню"
MENU_TEXT = "Выберите нужный сервис."

NO_ACTIVE_CONTEXT_TEXT = (
    "Сейчас нет активного сценария.\n"
    "Откройте меню и выберите нужный сервис."
)

SCENARIO_RESET_TEXT = "Текущий сценарий завершен."

RESUME_NOTHING_TEXT = (
    "Нет активного сценария для продолжения.\n"
    "Откройте меню и выберите нужный сервис."
)

SERVICE_NOT_FOUND_TEXT = "Сервис не найден."
ACCESS_DENIED_TEXT = "У вас нет доступа к этому сервису."

UNKNOWN_MESSAGE_TEXT = (
    "Не удалось распознать сообщение.\n"
    "Откройте меню и выберите нужный сервис."
)

EMPTY_TASKS_TEXT = "У вас пока нет задач."

RESULT_FILE_NOT_FOUND_TEXT = "Файл результата не найден."

TEST_FILE_SUCCESS_TEXT = "Тестовый файл успешно отправлен."
TEST_FILE_EMPTY_RESPONSE_TEXT = "Файл не отправлен: API вернул пустой ответ."
TEST_XLSX_SUCCESS_TEXT = "Тестовый xlsx-файл успешно отправлен."
TEST_XLSX_FAIL_TEXT = "Не удалось отправить xlsx. Подробности смотрите в логах."

OUTDATED_ACTION_TEXT = (
    "Это действие больше неактуально.\n"
    "Откройте меню и начните заново."
)

INVALID_STATE_TEXT = (
    "Состояние сценария устарело или недоступно.\n"
    "Откройте меню и начните заново."
)

# === DADATA ===

DADATA_TITLE = "🔎 Проверка организаций"

DADATA_INTRO_TEXT = (
    "Введите ИНН или наименование организации.\n\n"
    "Примеры:\n"
    "• 7707083893\n"
    "• Сбербанк"
)

DADATA_EMPTY_QUERY_TEXT = "Введите ИНН или наименование организации."

DADATA_INVALID_QUERY_TEXT = (
    "Не удалось распознать запрос.\n"
    "Введите корректный ИНН или наименование организации."
)

DADATA_NOT_FOUND_TEXT = (
    "По вашему запросу ничего не найдено.\n"
    "Попробуйте уточнить ИНН или наименование."
)

DADATA_NO_KEYS_TEXT = (
    "Сейчас сервис временно недоступен.\n"
    "Нет доступных API-ключей DaData. Обратитесь к администратору."
)

DADATA_EXTERNAL_ERROR_TEXT = (
    "Не удалось получить данные из DaData.\n"
    "Попробуйте позже или обратитесь к администратору."
)

DADATA_NEW_SEARCH_TEXT = "Введите новый ИНН или наименование организации."

DADATA_NO_ACTIVE_VARIANTS_TEXT = (
    "Список результатов недоступен.\n"
    "Выполните поиск заново."
)

DADATA_LAST_VARIANT_TEXT = "Это последняя организация в списке."
DADATA_FIRST_VARIANT_TEXT = "Это первая организация в списке."

DADATA_INVALID_SELECTION_TEXT = "Некорректный выбор варианта."
DADATA_SELECTION_NOT_FOUND_TEXT = "Выбранная организация не найдена."

DADATA_PAGE_EMPTY_TEXT = "Для этой страницы варианты не найдены."

DADATA_RESUME_TEXT = (
    "Продолжаем работу с сервисом проверки организаций.\n"
    "Введите ИНН или наименование организации."
)

DADATA_CACHE_MARK = "Ответ получен из кэша"
DADATA_CONTINUE_HINT = "Чтобы выполнить новый поиск, отправьте ИНН или наименование организации."

# === DADATA BATCH ===

DADATA_BATCH_TITLE = "📦 Пакетная проверка организаций"

DADATA_BATCH_INTRO_TEXT = (
    "Загрузите xlsx-файл с данными для пакетной проверки.\n\n"
    "Требования к файлу:\n"
    "• до 2 колонок: ИНН и/или наименование\n"
    "• названия колонок не важны\n"
    "• можно передавать только ИНН, только названия или оба значения\n\n"
    "После загрузки бот проанализирует файл и покажет, "
    "сколько запросов потребуется для обработки."
)

DADATA_BATCH_P2P_WARNING_TEXT = (
    "В личном чате автоматическая отправка итогового xlsx может работать нестабильно.\n"
    "Для гарантированной доставки результата лучше использовать бота в рабочей группе."
)

DADATA_BATCH_FILE_NOT_DETECTED_TEXT = (
    "Не удалось обнаружить файл в сообщении.\n"
    "Пожалуйста, отправьте xlsx-файл."
)

DADATA_BATCH_WRONG_FILE_TYPE_TEXT = (
    "Поддерживаются только файлы формата .xlsx.\n"
    "Пожалуйста, проверьте файл и отправьте его повторно."
)

DADATA_BATCH_FILE_RECEIVED_TEXT = (
    "Файл получен.\n"
    "Скачиваю и анализирую содержимое..."
)

DADATA_BATCH_FILE_DOWNLOAD_ERROR_TEXT = (
    "Не удалось скачать файл из TDM.\n"
    "Попробуйте отправить файл еще раз или обратитесь к администратору."
)

DADATA_BATCH_ANALYZE_ERROR_TEXT = (
    "Не удалось проанализировать файл.\n"
    "Проверьте его структуру и повторите попытку."
)

DADATA_BATCH_LIMIT_OK_TEXT = "Лимита достаточно для запуска обработки."
DADATA_BATCH_LIMIT_WARNING_TEXT = "Лимита может не хватить для полной обработки."

DADATA_BATCH_CONFIRM_TEXT = "Запустить обработку файла?"
DADATA_BATCH_CONFIRM_HINT_TEXT = "Подтвердите запуск кнопкой ниже."

DADATA_BATCH_CANCELLED_TEXT = "Задача отменена."

DADATA_BATCH_MISSING_FILE_TEXT = (
    "Исходный файл не найден.\n"
    "Пожалуйста, загрузите файл повторно."
)

DADATA_BATCH_TASK_STARTED_TEXT = "Задача поставлена в очередь."
DADATA_BATCH_TASK_RUNNING_TEXT = "Задача выполняется."
DADATA_BATCH_TASK_DONE_TEXT = "Обработка завершена."
DADATA_BATCH_TASK_FAILED_TEXT = "Задача завершилась с ошибкой."

DADATA_BATCH_TASK_NOT_FOUND_TEXT = "Задача не найдена."
DADATA_BATCH_TASK_NOT_FOUND_DB_TEXT = "Задача не найдена в базе данных."

DADATA_BATCH_STATUS_TITLE = "📊 Статус задачи"
DADATA_BATCH_ANALYSIS_TITLE = "📑 Анализ файла"
DADATA_BATCH_STARTED_TITLE = "🚀 Обработка запущена"
DADATA_BATCH_DONE_TITLE = "✅ Обработка завершена"

DADATA_BATCH_RESULT_SENDING_TEXT = "Файл готов. Отправляю результат..."

DADATA_BATCH_P2P_RESULT_WARNING_TEXT = (
    "Обработка завершена, но TDM сейчас не всегда позволяет автоматически "
    "отправлять xlsx в личный чат с ботом.\n\n"
    "Файл результата сохранен на сервере:\n"
    "{file_name}\n\n"
    "Для автоматической доставки результата лучше использовать бота в рабочей группе."
)

DADATA_BATCH_RESULT_SEND_FAIL_TEXT = (
    "Не удалось отправить файл результата в этот чат.\n"
    "Попробуйте использовать бота в рабочей группе."
)

DADATA_BATCH_RESULT_FILE_NOT_FOUND_TEXT = "Файл результата не найден."

DADATA_BATCH_CONFIRM_BUTTON_HINT_TEXT = (
    "Нажмите кнопку ниже, чтобы подтвердить запуск или отменить операцию."
)

# === ADMIN CONSOLE ===

ADMIN_CONSOLE_TITLE = "⚙️ Панель администратора"

ADMIN_CONSOLE_INTRO_TEXT = (
    "Управление пользователями и доступами.\n\n"
    "Выберите нужное действие."
)

ADMIN_CONSOLE_FIND_USER_TEXT = (
    "Введите TDM ID пользователя.\n\n"
    "Чтобы выйти из сценария, используйте /cancel."
)

ADMIN_CONSOLE_USER_NOT_FOUND_TEXT = "Пользователь не найден."
ADMIN_CONSOLE_INVALID_USER_ID_TEXT = "Введите корректный числовой TDM ID."

ADMIN_CONSOLE_NO_USERS_TEXT = "Пользователи не найдены."

ADMIN_CONSOLE_NO_TARGET_USER_TEXT = "Сначала выберите пользователя."
ADMIN_CONSOLE_NO_TARGET_FOR_ACTION_TEXT = "Не выбран пользователь."
ADMIN_CONSOLE_NOT_ENOUGH_DATA_TEXT = "Недостаточно данных для выполнения действия."

ADMIN_CONSOLE_SERVICE_NOT_FOUND_TEXT = "Сервис не найден."
ADMIN_CONSOLE_NO_ACTIVE_ACCESS_TEXT = "У пользователя нет активных доступов."

ADMIN_CONSOLE_ACCESS_GRANTED_TEXT = "Доступ выдан."
ADMIN_CONSOLE_ACCESS_REVOKED_TEXT = "Доступ отозван."
ADMIN_CONSOLE_ACCESS_NOT_FOUND_TEXT = "Активный доступ не найден."

ADMIN_CONSOLE_GRANT_DAYS_TEXT = "Выберите срок доступа:"
ADMIN_CONSOLE_ENTER_GRANT_DAYS_TEXT = (
    "Введите количество дней.\n"
    "Для бессрочного доступа укажите 0."
)

ADMIN_CONSOLE_INVALID_DAYS_TEXT = (
    "Введите корректное число дней.\n"
    "Для бессрочного доступа используйте 0."
)

# === FIELD INSPECTION ===

FIELD_INSPECTION_TITLE = "🧭 Полевые проверки"

FIELD_INSPECTION_INTRO_TEXT = (
    "Сервис для управления полевыми проверками, заданиями инспекторам "
    "и фиксацией результатов."
)

FIELD_INSPECTION_NO_PROFILE_TEXT = (
    "Ваш профиль инспектора или куратора пока не настроен.\n"
    "Для доступа к сервису требуется связка учетной записи бота с профилем инспектора."
)

FIELD_INSPECTION_PROFILE_NOT_FOUND_TEXT = (
    "Профиль пользователя бота не найден.\n"
    "Попробуйте выполнить /start и повторить попытку."
)

FIELD_INSPECTION_CONTACT_ADMIN_TEXT = (
    "Профиль полевых проверок не настроен.\n"
    "Обратитесь к администратору."
)

FIELD_INSPECTION_USE_BUTTONS_TEXT = (
    "Для работы с сервисом используйте кнопки в меню."
)

FIELD_INSPECTION_CURATOR_TEXT = (
    "Режим куратора.\n\n"
    "Здесь можно создавать проверки, просматривать кампании и отслеживать статистику."
)

FIELD_INSPECTION_INSPECTOR_TEXT = (
    "Режим инспектора.\n\n"
    "Здесь доступны назначенные проверки, задачи и текущий прогресс."
)

FIELD_INSPECTION_CURATOR_CREATE_STUB_TEXT = (
    "Создание проверки будет реализовано на следующем этапе."
)

FIELD_INSPECTION_CURATOR_CAMPAIGNS_STUB_TEXT = (
    "Просмотр кампаний куратора будет реализован на следующем этапе."
)

FIELD_INSPECTION_CURATOR_STATS_STUB_TEXT = (
    "Статистика проверок будет реализована на следующем этапе."
)

FIELD_INSPECTION_INSPECTOR_CAMPAIGNS_STUB_TEXT = (
    "Список назначенных проверок будет реализован на следующем этапе."
)

FIELD_INSPECTION_INSPECTOR_TASKS_STUB_TEXT = (
    "Список задач инспектора будет реализован на следующем этапе."
)

FIELD_INSPECTION_INSPECTOR_PROGRESS_STUB_TEXT = (
    "Экран прогресса инспектора будет реализован на следующем этапе."
)

FIELD_INSPECTION_MY_CAMPAIGNS_TITLE = "📋 Мои проверки"
FIELD_INSPECTION_MY_TASKS_TITLE = "🏘 Мои задачи"
FIELD_INSPECTION_MY_PROGRESS_TITLE = "📊 Мой прогресс"
FIELD_INSPECTION_CAMPAIGN_CARD_TITLE = "🗂 Карточка проверки"
FIELD_INSPECTION_TASK_CARD_TITLE = "🏠 Карточка объекта"

FIELD_INSPECTION_EMPTY_CAMPAIGNS_TEXT = "Назначенных проверок пока нет."
FIELD_INSPECTION_EMPTY_TASKS_TEXT = "Назначенных задач пока нет."

FIELD_INSPECTION_SELECT_CAMPAIGN_HINT = "Выберите проверку с помощью кнопок ниже."
FIELD_INSPECTION_SELECT_TASK_HINT = "Выберите задачу с помощью кнопок ниже."

FIELD_INSPECTION_TASK_ACTIONS_STUB = (
    "Действия по заполнению чеклиста, формы и загрузке фото будут добавлены на следующих этапах."
)

