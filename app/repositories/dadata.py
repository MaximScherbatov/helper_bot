from datetime import datetime, date
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import DaDataApiKey, DaDataRequestCache, DaDataUsageLog


class DaDataRepository:
    def __init__(self, session: Session):
        self.session = session

    # ---------- API KEYS ----------

    def get_active_keys(self) -> list[DaDataApiKey]:
        rows = self.session.scalars(
            select(DaDataApiKey)
            .where(DaDataApiKey.is_active.is_(True))
            .order_by(DaDataApiKey.id.asc())
        )
        return list(rows)

    def get_first_available_key(self) -> DaDataApiKey | None:
        today = date.today()
        keys = self.get_active_keys()

        for key in keys:
            if key.last_reset_date != today:
                key.used_today = 0
                key.last_reset_date = today
        self.session.commit()

        for key in keys:
            if key.used_today < key.daily_limit:
                return key

        return None

    def increment_key_usage(self, key_id: int) -> None:
        key = self.session.get(DaDataApiKey, key_id)
        if key is None:
            return

        today = date.today()
        if key.last_reset_date != today:
            key.used_today = 0
            key.last_reset_date = today

        key.used_today += 1
        self.session.commit()

    def create_api_key(
        self,
        api_key: str,
        comment: str | None = None,
        daily_limit: int = 10000,
    ) -> DaDataApiKey:
        row = DaDataApiKey(
            api_key=api_key,
            is_active=True,
            daily_limit=daily_limit,
            used_today=0,
            last_reset_date=date.today(),
            comment=comment,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    # ---------- CACHE ----------

    def get_cache_row(
        self,
        query_type: str,
        normalized_query: str,
    ) -> DaDataRequestCache | None:
        return self.session.scalar(
            select(DaDataRequestCache).where(
                DaDataRequestCache.query_type == query_type,
                DaDataRequestCache.normalized_query == normalized_query,
            )
        )

    def get_cache(
        self,
        query_type: str,
        normalized_query: str,
    ) -> DaDataRequestCache | None:
        row = self.get_cache_row(query_type, normalized_query)
        if row is None:
            return None

        if row.expires_at and row.expires_at < datetime.utcnow():
            return None

        return row

    def upsert_cache(
        self,
        query_type: str,
        query_value: str,
        normalized_query: str,
        response_json: dict,
        source_key_id: int | None = None,
        expires_at: datetime | None = None,
    ) -> DaDataRequestCache:
        row = self.get_cache_row(query_type, normalized_query)

        if row is not None:
            row.query_value = query_value
            row.response_json = response_json
            row.source_key_id = source_key_id
            row.expires_at = expires_at
            self.session.commit()
            self.session.refresh(row)
            return row

        row = DaDataRequestCache(
            query_type=query_type,
            query_value=query_value,
            normalized_query=normalized_query,
            response_json=response_json,
            source_key_id=source_key_id,
            expires_at=expires_at,
        )
        self.session.add(row)

        try:
            self.session.commit()
            self.session.refresh(row)
            return row
        except IntegrityError:
            self.session.rollback()

            existing = self.get_cache_row(query_type, normalized_query)
            if existing is None:
                raise

            existing.query_value = query_value
            existing.response_json = response_json
            existing.source_key_id = source_key_id
            existing.expires_at = expires_at

            self.session.commit()
            self.session.refresh(existing)
            return existing

    # ---------- USAGE LOG ----------

    def log_usage(
        self,
        query_type: str,
        query_value: str,
        normalized_query: str,
        status: str,
        api_key_id: int | None = None,
        error_text: str | None = None,
    ) -> None:
        row = DaDataUsageLog(
            api_key_id=api_key_id,
            query_type=query_type,
            query_value=query_value,
            normalized_query=normalized_query,
            status=status,
            error_text=error_text,
        )
        self.session.add(row)
        self.session.commit()