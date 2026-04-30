import logging
import mimetypes
import time
from typing import Optional

import requests

from app.config import get_settings

logger = logging.getLogger(__name__)


class TdmFileSender:
    def __init__(self):
        self.settings = get_settings()
        self.token = self.settings.bot_token
        self.api_base_url = self.settings.tdm_api_base_url
        self.file_upload_base_url = self.settings.tdm_file_upload_base_url
        self.base_headers = {"Authorization": self.token}

    def _upload_file(self, file_name: str, content: bytes) -> Optional[dict]:
        url = f"{self.file_upload_base_url}/api/v1/upload/secret/encryptable"
        headers = {
            **self.base_headers,
            "Content-Length": str(len(content)),
        }
        files = {"file": (file_name, content)}

        try:
            resp = requests.post(url, headers=headers, files=files, timeout=60)
            logger.info(
                "Upload response: status=%s body=%s",
                resp.status_code,
                resp.text[:500],
            )
            if resp.status_code == 200:
                data = resp.json()
                resource = data.get("resource")
                if resource:
                    return resource
                logger.error("Upload OK but no 'resource' in response: %s", data)
                return None
            else:
                logger.error(
                    "Upload failed: status=%s body=%s",
                    resp.status_code,
                    resp.text[:500],
                )
                return None
        except Exception as e:
            logger.exception("Upload exception", exc_info=e)
            return None

    def send_file(
        self,
        workspace_id: int,
        group_id: int,
        file_name: str,
        content: bytes,
        message_text: str = "",
    ) -> bool:
        from app.integrations.tdm_state_resolver import TdmStateResolver

        effective_workspace_id = workspace_id if workspace_id and workspace_id > 0 else None

        if effective_workspace_id is None:
            effective_workspace_id = TdmStateResolver().resolve_workspace_id_by_group_id(group_id)

        if effective_workspace_id is None:
            logger.error("Could not resolve workspace_id for group_id=%s", group_id)
            return False

        logger.info(
            "Sending file '%s' (%d bytes) to workspace=%s group=%s",
            file_name,
            len(content),
            effective_workspace_id,
            group_id,
        )

        resource = self._upload_file(file_name, content)
        if resource is None:
            logger.error("Upload failed, aborting send_file")
            return False

        mime_type = (
            mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        )

        send_url = (
            f"{self.api_base_url}/botapi/v1/messages/sendFile"
            f"/{effective_workspace_id}/{group_id}"
        )

        payload = {
            "clientRandomId": int(time.time() * 1000),
            "message": message_text,
            "file": {
                "fileName": file_name,
                "length": len(content),
                "mimeType": mime_type,
                "resourceRef": resource,
            },
        }

        try:
            resp = requests.post(
                send_url,
                headers={
                    **self.base_headers,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            logger.info(
                "SendFile response: status=%s body=%s",
                resp.status_code,
                resp.text[:500],
            )
            if resp.status_code == 200:
                return True
            else:
                logger.error(
                    "SendFile failed: status=%s body=%s",
                    resp.status_code,
                    resp.text[:500],
                )
                return False
        except Exception as e:
            logger.exception("SendFile exception", exc_info=e)
            return False