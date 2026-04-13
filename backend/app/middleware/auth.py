from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.supabase_client import supabase

router = APIRouter()


class SignupUser(BaseModel):
    name: str
    email: str
    password: str


class LoginUser(BaseModel):
    email: str
    password: str


# ✅ SIGNUP
@router.post("/signup")
def signup(user: SignupUser):
    # check if user exists
    existing = supabase.table("users").select("*").eq("email", user.email).execute()

    if existing.data:
        raise HTTPException(status_code=400, detail="User already exists")

    # insert user
    supabase.table("users").insert({
        "name": user.name,
        "email": user.email,
        "password": user.password
    }).execute()

    return {"message": "User created successfully"}


# ✅ LOGIN
@router.post("/login")
def login(user: LoginUser):
    res = supabase.table("users").select("*").eq("email", user.email).execute()

    if not res.data:
        raise HTTPException(status_code=401, detail="User not found")

    db_user = res.data[0]

    if db_user["password"] != user.password:
        raise HTTPException(status_code=401, detail="Invalid password")

    return {
        "message": "Login successful",
        "user": {
            "email": db_user["email"],
            "name": db_user["name"]
        }
    }