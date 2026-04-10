# backend/app/db/models/memory.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.db.migrations.database import Base

class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    embedding = Column(Text)  # store as JSON string
    __table_args__ = {"schema": "public"}