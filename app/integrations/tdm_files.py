import logging
import os
import tempfile
from typing import Optional

import requests

from app.config import get_settings

logger = logging.getLogger(__name__)

XLSX_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}


def extract_file_from_event(event) -> Optional[dict]:
    """
    Извлекает информацию о файле из входящего события.
    Возвращает dict с полями: fileName, length, mimeType, resourceRef
    или None если файл не найден.
    """
    try:
        payload = event.get_payload_data()
        messages = payload.get("messages", [])
        if not messages:
            return None

        media = messages[0].get("media", {})
        if not media:
            return None

        file_data = media.get("file", None)
        if file_data is None:
            return None

        resource_ref = file_data.get("resourceRef", None)
        if resource_ref is None:
            return None

        return {
            "fileName": file_data.get("fileName", "file"),
            "length": file_data.get("length", 0),
            "mimeType": file_data.get("mimeType", ""),
            "resourceRef": resource_ref,
        }

    except Exception as e:
        logger.exception("Failed to extract file from event payload", exc_info=e)
        return None


def is_xlsx_file(file_info: dict) -> bool:
    """Проверяет, является ли файл xlsx."""
    return file_info.get("mimeType", "") in XLSX_MIME_TYPES


def download_decryptable_file(resource_ref: dict, token: str, api_base_url: str) -> Optional[bytes]:
    """
    Скачивает расшифрованное содержимое файла из TDM S3.
    """
    url = f"{api_base_url}/api/v1/download/secret/decryptable"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }
    body = {"resourceRef": resource_ref}

    try:
        response = requests.post(url, json=body, headers=headers, timeout=60)
        if response.status_code == 200:
            return response.content
        else:
            logger.error(
                "Failed to download file: status=%s body=%s",
                response.status_code,
                response.text[:500],
            )
            return None
    except Exception as e:
        logger.exception("Exception while downloading file", exc_info=e)
        return None


def save_file_to_storage(content: bytes, file_name: str, sub_dir: str = "input") -> str:
    """
    Сохраняет байты файла в папку storage.
    Возвращает полный путь к файлу.
    """
    settings = get_settings()
    base_dir = os.path.join(settings.files_base_dir, sub_dir)
    os.makedirs(base_dir, exist_ok=True)

    safe_name = os.path.basename(file_name)
    file_path = os.path.join(base_dir, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info("File saved to %s (%d bytes)", file_path, len(content))
    return file_path


def download_event_file_to_storage(event, sub_dir: str = "input") -> Optional[tuple[str, dict]]:
    """
    Полный pipeline: извлечь -> скачать -> сохранить.
    Возвращает (путь_к_файлу, file_info) или None при ошибке.
    """
    file_info = extract_file_from_event(event)
    if file_info is None:
        return None

    settings = get_settings()
    content = download_decryptable_file(
        resource_ref=file_info["resourceRef"],
        token=settings.bot_token,
        api_base_url=settings.tdm_file_upload_base_url,
    )
    if content is None:
        return None

    file_path = save_file_to_storage(
        content=content,
        file_name=file_info["fileName"],
        sub_dir=sub_dir,
    )

    return file_path, file_info