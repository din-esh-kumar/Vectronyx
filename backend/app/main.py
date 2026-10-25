# backend/app/main.py
"""
Vectronyx AI Workbench - Primary FastAPI Entrypoint
"""
from app.middleware.app import app

__all__ = ["app"]
