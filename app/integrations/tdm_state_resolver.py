import logging
from typing import Optional

from messenger_bot_api.util import Request

from app.config import get_settings

logger = logging.getLogger(__name__)


class TdmStateResolver:
    def __init__(self):
        settings = get_settings()
        self.request = Request(
            token=settings.bot_token,
            api_base_url=settings.tdm_api_base_url,
            file_upload_base_url=settings.tdm_file_upload_base_url,
            sse_base_url=settings.tdm_sse_base_url,
        )

    def resolve_workspace_id_by_group_id(self, group_id: int) -> Optional[int]:
        try:
            states = self.request.get_states()
            for state in states:
                if state.get("groupId") == group_id:
                    return state.get("workspaceId")
        except Exception as e:
            logger.exception("Failed to resolve workspace_id by group_id", exc_info=e)

        return None