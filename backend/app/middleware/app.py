import sys
from pathlib import Path

# Ensure backend root directory is in sys.path
backend_root = str(Path(__file__).resolve().parent.parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from fastapi import FastAPI
from app.middleware.auth import router as auth_router
from app.modules.data_analyst.routes import router as analyst_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Vectronyx AI Workbench API")

# ✅ CORS FIX
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all (for dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(analyst_router, prefix="/api/analyst")

@app.get("/")
def root():
    return {"message": "Vectronyx AI Workbench Backend Running ⚡"}