from datetime import datetime, date
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BotUser(Base):
    __tablename__ = "bot_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tdm_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(255), nullable=True)    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    system_roles: Mapped[list["UserSystemRole"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    service_accesses: Mapped[list["UserServiceAccess"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="UserServiceAccess.user_id",
    )


class SystemRole(Base):
    __tablename__ = "system_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    users: Mapped[list["UserSystemRole"]] = relationship(back_populates="role", cascade="all, delete-orphan")


class UserSystemRole(Base):
    __tablename__ = "user_system_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_system_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("system_roles.id", ondelete="CASCADE"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["BotUser"] = relationship(back_populates="system_roles")
    role: Mapped["SystemRole"] = relationship(back_populates="users")


class BotService(Base):
    __tablename__ = "bot_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    accesses: Mapped[list["UserServiceAccess"]] = relationship(back_populates="service", cascade="all, delete-orphan")


class UserServiceAccess(Base):
    __tablename__ = "user_service_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("bot_services.id", ondelete="CASCADE"), nullable=False)

    access_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    granted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("bot_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped["BotUser"] = relationship(
        back_populates="service_accesses",
        foreign_keys=[user_id],
    )
    service: Mapped["BotService"] = relationship(back_populates="accesses")


class UserContext(Base):
    __tablename__ = "user_contexts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tdm_user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    workspace_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    active_service_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    context_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tdm_user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    service_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DaDataApiKey(Base):
    __tablename__ = "dadata_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("bot_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_shared: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)
    used_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class DaDataRequestCache(Base):
    __tablename__ = "dadata_request_cache"
    __table_args__ = (
        UniqueConstraint("query_type", "normalized_query", name="uq_dadata_cache_query"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_type: Mapped[str] = mapped_column(String(20), nullable=False)  # inn | name
    query_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_query: Mapped[str] = mapped_column(Text, nullable=False)
    response_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_key_id: Mapped[int | None] = mapped_column(
        ForeignKey("dadata_api_keys.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DaDataUsageLog(Base):
    __tablename__ = "dadata_usage_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[int | None] = mapped_column(
        ForeignKey("dadata_api_keys.id", ondelete="SET NULL"),
        nullable=True,
    )
    query_type: Mapped[str] = mapped_column(String(20), nullable=False)
    query_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # success | cache | error | no_results
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_uuid: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    tdm_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    service_code: Mapped[str] = mapped_column(String(100), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")

    input_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    progress_current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)