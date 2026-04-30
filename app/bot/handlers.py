from messenger_bot_api.handler import (
    ClickButtonEventHandler,
    CommandHandler,
    MessageHandler,
)


def register_handlers(app, router):
    app.add_handler(CommandHandler("start", router.handle_start))
    app.add_handler(CommandHandler("help", router.handle_help))
    app.add_handler(CommandHandler("menu", router.handle_menu))
    app.add_handler(CommandHandler("status", router.handle_status))
    app.add_handler(CommandHandler("cancel", router.handle_cancel))
    app.add_handler(CommandHandler("resume", router.handle_resume))
    app.add_handler(CommandHandler("whoami", router.handle_whoami))
    app.add_handler(CommandHandler("tasks", router.handle_tasks))
    #app.add_handler(CommandHandler("testfile", router.handle_send_test_file))
    app.add_handler(CommandHandler("testxlsx", router.handle_send_test_xlsx))
    app.add_handler(ClickButtonEventHandler(router.handle_button))
    app.add_handler(MessageHandler(router.handle_message))