# backend/app/db/repositories/memory_repo.py
from sqlalchemy.orm import Session
from app.db.models.memory import Memory

def save_memory(db: Session, user_id: int, content: str, embedding: str):
    memory = Memory(
        user_id=user_id,
        content=content,
        embedding=embedding
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory