# backend/app/core/dependencies.py
from app.db.migrations.database import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()