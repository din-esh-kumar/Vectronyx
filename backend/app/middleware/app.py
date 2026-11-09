import sys
from pathlib import Path

# Ensure backend root directory is in sys.path
backend_root = str(Path(__file__).resolve().parent.parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.middleware.auth import router as auth_router
from app.modules.data_analyst.routes import router as analyst_router
from app.modules.research_agent.routes import router as research_router
from app.modules.memory.routes import router as memory_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Vectronyx AI Workbench API")

# ✅ CORS FIX
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all (for dev & prod cross-origin)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(analyst_router, prefix="/api/analyst")
app.include_router(research_router, prefix="/api/research")
app.include_router(memory_router, prefix="/api/memory")

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "Vectronyx AI Workbench API",
        "version": "1.0.0"
    }

# Check for production frontend build (e.g. monolithic or single-container deploy)
_dist_candidate = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
if not _dist_candidate.is_dir():
    _dist_candidate = Path("frontend/dist").resolve()

if _dist_candidate.is_dir() and (_dist_candidate / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=str(_dist_candidate / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith(("api", "auth", "health", "docs", "openapi.json", "redoc")):
            return {"detail": "Not Found"}
        target_file = _dist_candidate / full_path
        if target_file.is_file():
            return FileResponse(str(target_file))
        return FileResponse(str(_dist_candidate / "index.html"))
else:
    @app.get("/")
    def root():
        return {"message": "Vectronyx AI Workbench Backend Running ⚡"}