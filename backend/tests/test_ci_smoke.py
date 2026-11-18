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


def test_verify_deployment_script_offline_contract():
    mod = _load_script("verify_deployment", "scripts/verify_deployment.py")
    assert mod.space_subdomain("din-esh-kumar/vectronyx-backend") == (
        "https://din-esh-kumar-vectronyx-backend.hf.space"
    )

    def fake_http(url: str, *, method: str = "GET", headers=None, timeout: float = 20.0):
        if method == "OPTIONS":
            return 200, {"access-control-allow-origin": "*"}, "", 12.4
        if url.endswith("/health"):
            return 200, {}, '{"status":"healthy","version":"1.0.0"}', 18.2
        if url.endswith("/openapi.json"):
            paths = {p: {} for p in mod.REQUIRED_OPENAPI_PATHS}
            return 200, {}, f'{{"paths": {__import__("json").dumps(paths)}}}', 25.0
        if url.endswith(("/api/memory/status", "/api/research/health")):
            return 200, {}, '{"ok":true}', 15.1
        if "/assets/" in url:
            return 200, {"cache-control": "public, max-age=31536000, immutable"}, "console.log('ok');", 9.5
        return 200, {}, '<!doctype html><html><body><div id="root"></div><script src="/assets/index-abc123.js"></script></body></html>', 22.0

    with patch.object(mod, "http_request", side_effect=fake_http):
        be_results = mod.verify_backend("https://api.example.test", cors_origin="https://app.example.test", wait_seconds=0)
        fe_results = mod.verify_frontend("https://app.example.test", wait_seconds=0)

    assert all(r.ok for r in be_results), [r for r in be_results if not r.ok]
    assert all(r.ok for r in fe_results), [r for r in fe_results if not r.ok]

    md = mod.render_markdown_summary(be_results + fe_results, title="Test Report")
    assert "## Test Report" in md
    assert "| `backend` | `GET /health` | **PASS** |" in md
    assert "| `frontend` | `GET /data-analyst` | **PASS** |" in md


def test_github_workflows_parse_and_enforce_hardening_policies():
    try:
        import yaml
    except ImportError:
        return

    workflows_dir = REPO_ROOT / ".github" / "workflows"
    workflow_files = sorted(workflows_dir.glob("*.yml"))
    assert len(workflow_files) >= 1, f"Expected unified CI workflow suite, found {[p.name for p in workflow_files]}"

    for wf_path in workflow_files:
        doc = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
        assert isinstance(doc, dict), f"{wf_path.name} did not parse to a mapping"
        assert "permissions" in doc, f"{wf_path.name} must declare explicit top-level permissions"
        jobs = doc.get("jobs", {})
        assert jobs, f"{wf_path.name} has no jobs"
        for job_id, job in jobs.items():
            assert "timeout-minutes" in job, f"{wf_path.name}:{job_id} must set timeout-minutes"
            assert "permissions" in job, f"{wf_path.name}:{job_id} must set least-privilege permissions"


def test_security_headers_and_strict_cors_allowlist():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in (resp.headers.get("permissions-policy") or "")

    # Untrusted origin must NOT be echoed back when explicit allowlist is active
    evil = client.options(
        "/api/analyst/generate-dashboard/stream",
        headers={
            "Origin": "https://evil-attacker.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert evil.headers.get("access-control-allow-origin") != "https://evil-attacker.example"


def test_auth_password_scrypt_hashing_and_constant_time_verify():
    from app.middleware.auth import hash_password, verify_password

    digest1 = hash_password("CorrectHorseBatteryStaple!")
    digest2 = hash_password("CorrectHorseBatteryStaple!")
    assert digest1.startswith("scrypt$")
    assert digest1 != digest2  # Unique random salt per call

    ok, needs_rehash = verify_password("CorrectHorseBatteryStaple!", digest1)
    assert ok is True and needs_rehash is False

    bad, bad_rehash = verify_password("WrongPassword123!", digest1)
    assert bad is False and bad_rehash is False

    legacy_ok, legacy_rehash = verify_password("legacy1234", "legacy1234")
    assert legacy_ok is True and legacy_rehash is True


def test_ssrf_dns_guard_blocks_internal_resolution():
    import socket
    from app.modules.research_agent.tools import _is_dns_safe

    fake_loopback = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]
    fake_metadata = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 0))]
    fake_public = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    with patch("app.modules.research_agent.tools.socket.getaddrinfo", return_value=fake_loopback):
        assert _is_dns_safe("rebind.attacker.test") is False
    with patch("app.modules.research_agent.tools.socket.getaddrinfo", return_value=fake_metadata):
        assert _is_dns_safe("meta.attacker.test") is False
    with patch("app.modules.research_agent.tools.socket.getaddrinfo", return_value=fake_public):
        assert _is_dns_safe("example.com") is True


def test_csv_upload_size_limit_returns_413():
    from app.modules.data_analyst import routes as analyst_routes

    client = TestClient(app)
    with patch.object(analyst_routes, "MAX_UPLOAD_BYTES", 32):
        resp = client.post(
            "/api/analyst/profile",
            files={"file": ("huge.csv", b"a,b\n" + b"1,2\n" * 30, "text/csv")},
        )
    assert resp.status_code == 413
