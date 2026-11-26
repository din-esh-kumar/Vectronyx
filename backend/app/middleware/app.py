import json
import os
import sys
from pathlib import Path

# Ensure backend root directory is in sys.path
backend_root = str(Path(__file__).resolve().parent.parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from app.core.config import settings
from app.middleware.auth import router as auth_router
from app.modules.data_analyst.routes import router as analyst_router
from app.modules.research_agent.routes import router as research_router
from app.modules.memory.routes import router as memory_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Vectronyx AI Workbench API")

# Explicit CORS allowlist (never combine wildcard '*' with allow_credentials=True)
_allowed_origins = settings.ALLOWED_ORIGINS or [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://vectronyx.vercel.app",
]
_wildcard_cors = "*" in _allowed_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _wildcard_cors else _allowed_origins,
    allow_origin_regex=None if _wildcard_cors else r"^https://vectronyx(?:-[a-z0-9-]+)?\.vercel\.app$",
    allow_credentials=not _wildcard_cors,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept"],
)


def _is_hf_space_runtime() -> bool:
    return bool(
        (
            os.getenv("VECTRONYX_HF_SPACE")
            or os.getenv("SPACE_ID")
            or os.getenv("SPACE_HOST")
            or ""
        ).strip()
    )


def _is_non_frameable_api_path(path: str) -> bool:
    return path == "/health" or path.startswith(("/api/", "/auth/")) or path in ("/api", "/auth")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    if _is_hf_space_runtime() and not _is_non_frameable_api_path(request.url.path):
        # Allow Hugging Face Space App iframe embedding while keeping API/auth routes strictly un-frameable
        response.headers.setdefault(
            "Content-Security-Policy",
            "frame-ancestors 'self' https://huggingface.co https://*.hf.space",
        )
    else:
        response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    if forwarded_proto == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

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
    _dist_root = _dist_candidate.resolve()
    _assets_dir = _dist_root / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    _raw_index_html = (_dist_root / "index.html").read_text(encoding="utf-8")

    def _render_index_html() -> str:
        runtime_payload = {
            "apiUrl": "",
            "supabaseUrl": settings.SUPABASE_URL,
            "supabasePublishableKey": settings.SUPABASE_PUBLISHABLE_KEY,
        }
        serialized = json.dumps(runtime_payload).replace("</", "<\\/")
        script_tag = f"<script>window.__VECTRONYX_CONFIG__={serialized};</script>"
        if "</head>" in _raw_index_html:
            return _raw_index_html.replace("</head>", f"{script_tag}</head>", 1)
        return f"{script_tag}{_raw_index_html}"

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path in ("api", "auth", "health", "docs", "openapi.json", "redoc") or full_path.startswith(
            ("api/", "auth/", "docs/")
        ):
            raise HTTPException(status_code=404, detail="Not Found")

        if full_path:
            target_file = (_dist_root / full_path).resolve()
            if target_file.is_relative_to(_dist_root) and target_file.is_file():
                return FileResponse(str(target_file))

        return HTMLResponse(content=_render_index_html())
else:
    @app.get("/")
    def root(request: Request):
        if _is_hf_space_runtime() and "text/html" in (request.headers.get("accept") or "").lower():
            return RedirectResponse(url="/ui", status_code=302)
        return {"message": "Vectronyx AI Workbench Backend Running ⚡"}