# backend/app/db/models/user.py
from sqlalchemy import Column, Integer, String
from app.db.migrations.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    __table_args__ = {"schema": "public"}