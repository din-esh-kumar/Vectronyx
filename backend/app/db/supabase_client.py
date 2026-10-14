import os
from dotenv import load_dotenv
from supabase import create_client

# Ensure the backend .env is loaded even when uvicorn imports modules directly.
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY")

missing = [
    name
    for name, value in {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY / SUPABASE_SERVICE_ROLE_KEY": SUPABASE_KEY,
    }.items()
    if not value
]

if missing:
    raise RuntimeError(
        f"Missing required Supabase environment variables: {', '.join(missing)}"
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
