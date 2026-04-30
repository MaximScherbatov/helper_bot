import logging

from messenger_bot_api.api import Application

from app.bot.handlers import register_handlers
from app.bot.router import BotRouter
from app.config import get_settings
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.logging_config import setup_logging
#from app.services.echo_service import EchoService
from app.services.dadata_service.service import DaDataService
from app.services.dadata_admin_service.service import DaDataAdminService
from app.services.dadata_batch_service.service import DaDataBatchService
from app.services.registry import ServiceRegistry
from app.services.admin_console_service.service import AdminConsoleService
from app.services.field_inspection_service.service import FieldInspectionService

logger = logging.getLogger(__name__)


def build_service_registry() -> ServiceRegistry:
    registry = ServiceRegistry()
    #registry.register(EchoService())
    registry.register(DaDataService())
    registry.register(DaDataAdminService())
    registry.register(DaDataBatchService())
    registry.register(AdminConsoleService())
    registry.register(FieldInspectionService())
    return registry


def main():
    print("=== BOT MAIN START ===", flush=True)

    setup_logging()
    from app.utils.requests_timeout import patch_requests_default_timeout

    patch_requests_default_timeout(connect_timeout=5, read_timeout=20)
    logger.info("Patched requests default timeout")
    logger.info("Logging configured")

    settings = get_settings()
    logger.info("Settings loaded")
    logger.info("TDM_API_BASE_URL=%s", settings.tdm_api_base_url)
    logger.info("TDM_FILE_UPLOAD_BASE_URL=%s", settings.tdm_file_upload_base_url)
    logger.info("TDM_SSE_BASE_URL=%s", settings.tdm_sse_base_url)
    logger.info("FILES_BASE_DIR=%s", settings.files_base_dir)

    init_db()
    logger.info("Database initialized")

    service_registry = build_service_registry()
    logger.info("Service registry created with %d services", len(service_registry.all()))

    router = BotRouter(session_factory=SessionLocal, service_registry=service_registry)
    router.sync_services()
    logger.info("Services synced to database")

    app = Application(
        token=settings.bot_token,
        request_kwargs={
            "api_base_url": settings.tdm_api_base_url,
            "file_upload_base_url": settings.tdm_file_upload_base_url,
            "sse_base_url": settings.tdm_sse_base_url,
        },
    )
    logger.info("TDM Application object created")

    register_handlers(app, router)
    logger.info("Handlers registered")

    logger.info("Starting TDM bot application")
    app.start()

    logger.info("Application.start() returned")


if __name__ == "__main__":
    main()