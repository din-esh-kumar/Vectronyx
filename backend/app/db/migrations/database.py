# backend/app/db/migrations/database.py
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger("vectronyx.database")

db_url = (settings.DB_URL or "").strip()
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

if db_url:
    engine = create_engine(db_url, pool_pre_ping=True)
else:
    logger.warning("DATABASE_URL is not set; using in-memory SQLite fallback until configured.")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()