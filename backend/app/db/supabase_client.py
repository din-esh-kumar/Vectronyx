import os
from supabase import create_client
from app.core.config import settings

SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = (
    settings.SUPABASE_SERVICE_ROLE_KEY
    or settings.SUPABASE_KEY
    or settings.SUPABASE_PUBLISHABLE_KEY
)

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

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        # Handle new Supabase key formats or offline environments gracefully
        supabase = None
