import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import SystemRole
from app.db.session import engine, SessionLocal

logger = logging.getLogger(__name__)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created or already exist")


def seed_system_roles(session: Session) -> None:
    roles = [
        ("admin", "Администратор"),
        ("user", "Пользователь"),
    ]

    for code, name in roles:
        existing = session.scalar(select(SystemRole).where(SystemRole.code == code))
        if existing is None:
            session.add(SystemRole(code=code, name=name))

    session.commit()
    logger.info("System roles seeded")


def init_db() -> None:
    create_tables()
    with SessionLocal() as session:
        seed_system_roles(session)