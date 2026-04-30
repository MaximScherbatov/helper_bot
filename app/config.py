from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    okved_dict_xlsx_path: str = ""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    tdm_api_base_url: str = ""
    tdm_file_upload_base_url: str = ""
    tdm_sse_base_url: str = ""

    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    files_base_dir: str = "./app/files"

    admin_tdm_user_ids: List[int] = []

    log_level: str = "INFO"

    @field_validator("admin_tdm_user_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value):
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        return [int(item.strip()) for item in str(value).split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()