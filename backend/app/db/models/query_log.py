# backend/app/db/models/query_log.py
from sqlalchemy import Column, Integer, Text
from app.db.migrations.database import Base

class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text)
    response = Column(Text)
    __table_args__ = {"schema": "public"}