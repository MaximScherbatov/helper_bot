import logging
from typing import Optional

from messenger_bot_api.util import Request

from app.config import get_settings

logger = logging.getLogger(__name__)


class TdmUserResolver:
    def __init__(self):
        settings = get_settings()
        self.request = Request(
            token=settings.bot_token,
            api_base_url=settings.tdm_api_base_url,
            file_upload_base_url=settings.tdm_file_upload_base_url,
            sse_base_url=settings.tdm_sse_base_url,
        )

    def resolve_user_info(self, tdm_user_id: int) -> dict:
        """
        Пытается найти пользователя в get_states() и вернуть его ФИО.
        """
        try:
            states = self.request.get_states()

            for state in states:
                opponent = state.get("opponent")
                if isinstance(opponent, dict) and opponent.get("id") == tdm_user_id:
                    first_name = opponent.get("firstName")
                    last_name = opponent.get("lastName")
                    middle_name = opponent.get("middleName")

                    display_name_parts = [last_name, first_name, middle_name]
                    display_name = " ".join([part for part in display_name_parts if part]).strip()

                    return {
                        "first_name": first_name,
                        "last_name": last_name,
                        "middle_name": middle_name,
                        "display_name": display_name or None,
                    }

        except Exception as e:
            logger.exception("Failed to resolve user info from TDM states", exc_info=e)

        return {
            "first_name": None,
            "last_name": None,
            "middle_name": None,
            "display_name": None,
        }