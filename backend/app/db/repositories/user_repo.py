# backend/app/db/repositories/user_repo.py
from sqlalchemy.orm import Session
from app.db.models.user import User

def create_user(db: Session, email: str, name: str):
    user = User(email=email, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user