# backend/tests/test_ci_smoke.py
"""
Deterministic offline CI/CD smoke & contract tests.
Safe to execute with zero API keys, zero network access, and zero database credentials.
"""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

from starlette.testclient import TestClient

from app.main import app


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_health_and_root_endpoints():
    client = TestClient(app)

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "healthy"
    assert "Vectronyx" in health_data["service"]

    root_resp = client.get("/")
    assert root_resp.status_code == 200
    ctype = root_resp.headers.get("content-type", "")
    if "application/json" in ctype:
        assert "Vectronyx" in root_resp.json().get("message", "")
    else:
        assert "<div id=\"root\">" in root_resp.text


def test_openapi_schema_exposes_core_routes():
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json().get("paths", {})
    assert "/health" in paths
    assert "/auth/login" in paths
    assert "/api/analyst/profile" in paths
    assert "/api/analyst/generate-dashboard/stream" in paths
    assert "/api/research/health" in paths
    assert "/api/research/stream" in paths
    assert "/api/memory/status" in paths


def test_cors_preflight_allows_production_origin():
    client = TestClient(app)
    resp = client.options(
        "/api/analyst/generate-dashboard/stream",
        headers={
            "Origin": "https://vectronyx.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    allow_origin = resp.headers.get("access-control-allow-origin")
    assert allow_origin in ("https://vectronyx.vercel.app", "*")


def test_auth_login_degrades_gracefully_without_supabase():
    client = TestClient(app)
    with patch("app.middleware.auth.supabase", None):
        resp = client.post(
            "/auth/login",
            json={"email": "ci@vectronyx.dev", "password": "not-used-offline"},
        )
    assert resp.status_code == 503
    assert "Supabase" in resp.json().get("detail", "")


def test_memory_status_endpoint_offline_safe():
    client = TestClient(app)
    with patch("app.modules.memory.embedder.settings.GEMINI_API_KEY", ""), \
         patch("app.modules.memory.routes.FastEmbedLocalEmbedder._ensure_loaded", return_value=None), \
         patch("app.modules.memory.routes.FastEmbedLocalEmbedder.embed_query", return_value=[0.1] * 384):
        resp = client.get("/api/memory/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_provider" in data
    assert data["online_gemini"]["status"] == "unconfigured"
    assert data["offline_fastembed"]["status"].startswith("healthy")


def test_deploy_hf_space_helper_subdomain():
    if not (REPO_ROOT / "scripts" / "deploy_hf_space.py").is_file():
        return
    mod = _load_script("deploy_hf_space", "scripts/deploy_hf_space.py")
    assert mod.space_subdomain("din-esh-kumar/vectronyx-backend") == (
        "https://din-esh-kumar-vectronyx-backend.hf.space"
    )


def test_ci_secret_scanner_detects_real_shapes_and_ignores_mocks():
    mod = _load_script("ci_secret_scan", "scripts/ci_secret_scan.py")

    # Dynamically constructed synthetic patterns so test source itself never holds literal keys
    fake_groq = "gsk_" + ("Ab12Cd34Ef56" * 3)
    fake_gemini = "AIza" + ("Sy98Zy76Xw54Vu32Ts" * 2)[:35]
    fake_oauth = "AQ.Ab8" + ("Q1w2E3r4T5y6" * 3)
    fake_sb_secret = "sb_secret_" + ("ZyXw9876" * 3)
    fake_db = "postgresql://postgres:" + "RealProdPass9988" + "@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

    leaked_blob = "\n".join([
        f'GROQ_API_KEY="{fake_groq}"',
        f'GEMINI_API_KEY="{fake_gemini}"',
        f'OAUTH="{fake_oauth}"',
        f'SB="{fake_sb_secret}"',
        f'DATABASE_URL="{fake_db}"',
        'const k = import.meta.env.VITE_GEMINI_API_KEY;',
    ])
    findings = mod.scan_text(leaked_blob, "frontend/src/leaked.ts", check_client_vars=True, check_frontend_only_vars=True)
    rules = {f.rule for f in findings}
    assert "groq_api_key" in rules
    assert "google_api_key" in rules
    assert "gemini_oauth_token" in rules
    assert "supabase_secret_key" in rules
    assert "postgres_credential_uri" in rules
    assert "forbidden_client_secret_env" in rules

    safe_blob = "\n".join([
        'bad = GeminiCloudEmbedder(api_key="AIzaSy_INVALID_KEY_FOR_TESTING")',
        'client = get_groq_instructor(api_key="gsk_override_test_12345")',
        'sqlalchemy.url = postgresql://user:password@localhost:5432/vectronyx',
        '# Never add VITE_GEMINI_API_KEY here',
    ])
    assert mod.scan_text(safe_blob, ".env.example", check_client_vars=True, check_frontend_only_vars=False) == []
