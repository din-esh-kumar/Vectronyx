# backend/alembic/env.py
from logging.config import fileConfig
from sqlalchemy import create_engine, text
from alembic import context
import os, sys
from dotenv import load_dotenv

# Load env
load_dotenv()

# Fix import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Base + models
from app.db.migrations.database import Base
from app.db.models import user, memory, query_log

target_metadata = Base.metadata

# Alembic config
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DB URL
DATABASE_URL = os.getenv("DATABASE_URL")

print("🔥 ALEMBIC USING DB:", DATABASE_URL)

# Fix % issue
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))


def run_migrations_online():
    connectable = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={
            "sslmode": "require",
            "connect_timeout": 10
        }
    )

    with connectable.connect() as connection:
        # 🔥 DEBUG (VERY IMPORTANT)
        result = connection.execute(
            text("SELECT current_database(), current_schema();")
        )
        print("🔥 CONNECTED TO:", result.fetchone())

        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()