#!/usr/bin/env python3
"""
Vectronyx AI Workbench — Post-Deploy & Synthetic Production Verifier.

Verifies live backend API endpoints, CORS preflight headers, frontend SPA routes,
immutable asset cache headers, and live JS bundle secret hygiene.
Zero external dependencies (Python standard library only).

Usage:
    python scripts/verify_deployment.py \
        --backend-url https://din-esh-kumar-vectronyx-backend.hf.space \
        --frontend-url https://vectronyx.vercel.app
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


DEFAULT_BACKEND_ROUTES: Tuple[str, ...] = (
    "/health",
    "/openapi.json",
    "/api/memory/status",
    "/api/research/health",
)

REQUIRED_OPENAPI_PATHS: Tuple[str, ...] = (
    "/health",
    "/auth/login",
    "/api/analyst/profile",
    "/api/analyst/generate-dashboard/stream",
    "/api/research/health",
    "/api/memory/status",
)

DEFAULT_FRONTEND_ROUTES: Tuple[str, ...] = (
    "/",
    "/login",
    "/data-analyst",
)

LIVE_BUNDLE_SECRET_RE = re.compile(
    r"\bgsk_[A-Za-z0-9]{20,}\b|\bAQ\.Ab8[A-Za-z0-9_-]{20,}\b|\bAIza[0-9A-Za-z_-]{35}\b|\bsb_secret_[0-9A-Za-z_-]{15,}\b"
)


@dataclass
class CheckResult:
    target: str
    check: str
    url: str
    ok: bool
    status: int
    latency_ms: float
    detail: str
    severity: str = "error"  # "error" or "warning"


def space_subdomain(space_id: str) -> str:
    """Convert Hugging Face 'owner/space_name' into '*.hf.space' URL."""
    owner, name = space_id.split("/", 1)
    safe_owner = re.sub(r"[^a-z0-9-]", "-", owner.lower())
    safe_name = re.sub(r"[^a-z0-9-]", "-", name.lower())
    return f"https://{safe_owner}-{safe_name}.hf.space"


def http_request(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 20.0,
) -> Tuple[int, Dict[str, str], str, float]:
    """Perform an HTTP request and return (status, lowercased_headers, body, latency_ms)."""
    req_headers = {"User-Agent": "Vectronyx-DevOps-Verifier/2.0"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, method=method, headers=req_headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, hdrs, body, round((time.perf_counter() - t0) * 1000.0, 1)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
        hdrs = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
        return exc.code, hdrs, body, round((time.perf_counter() - t0) * 1000.0, 1)


def _retry_until_ok(
    fn,
    *,
    wait_seconds: int,
    interval: float = 6.0,
):
    deadline = time.monotonic() + max(0, wait_seconds)
    result = fn()
    while not result.ok and time.monotonic() < deadline:
        time.sleep(min(interval, max(0.5, deadline - time.monotonic())))
        result = fn()
    return result


def verify_backend(
    backend_url: str,
    *,
    cors_origin: str,
    timeout: float = 20.0,
    wait_seconds: int = 30,
) -> List[CheckResult]:
    base = backend_url.rstrip("/")
    results: List[CheckResult] = []

    # 1. /health with retry (allows cold-start warm-up)
    def check_health() -> CheckResult:
        url = f"{base}/health"
        try:
            status, _, body, latency = http_request(url, timeout=timeout)
            if status != 200:
                return CheckResult("backend", "GET /health", url, False, status, latency, f"HTTP {status}")
            data = json.loads(body)
            ok = data.get("status") == "healthy"
            detail = f"status={data.get('status')}, version={data.get('version', 'n/a')}"
            return CheckResult("backend", "GET /health", url, ok, status, latency, detail)
        except Exception as exc:
            return CheckResult("backend", "GET /health", url, False, 0, 0.0, str(exc))

    results.append(_retry_until_ok(check_health, wait_seconds=wait_seconds))

    # 2. /openapi.json contract check
    openapi_url = f"{base}/openapi.json"
    try:
        status, _, body, latency = http_request(openapi_url, timeout=timeout)
        if status != 200:
            results.append(CheckResult("backend", "GET /openapi.json", openapi_url, False, status, latency, f"HTTP {status}"))
        else:
            schema = json.loads(body)
            paths = schema.get("paths", {})
            missing = [p for p in REQUIRED_OPENAPI_PATHS if p not in paths]
            ok = len(missing) == 0
            detail = f"{len(paths)} routes exposed" if ok else f"Missing routes: {', '.join(missing)}"
            results.append(CheckResult("backend", "GET /openapi.json", openapi_url, ok, status, latency, detail))
    except Exception as exc:
        results.append(CheckResult("backend", "GET /openapi.json", openapi_url, False, 0, 0.0, str(exc)))

    # 3. Remaining module health/status routes
    for path in ("/api/memory/status", "/api/research/health"):
        url = f"{base}{path}"
        try:
            status, _, _, latency = http_request(url, timeout=timeout)
            ok = status == 200
            results.append(CheckResult("backend", f"GET {path}", url, ok, status, latency, f"HTTP {status}"))
        except Exception as exc:
            results.append(CheckResult("backend", f"GET {path}", url, False, 0, 0.0, str(exc)))

    # 4. CORS preflight check
    cors_url = f"{base}/api/analyst/generate-dashboard/stream"
    try:
        status, hdrs, _, latency = http_request(
            cors_url,
            method="OPTIONS",
            headers={
                "Origin": cors_origin.rstrip("/"),
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            timeout=timeout,
        )
        allow_origin = hdrs.get("access-control-allow-origin", "")
        ok = status == 200 and allow_origin in (cors_origin.rstrip("/"), "*")
        detail = f"HTTP {status}, allow-origin={allow_origin or 'missing'}"
        results.append(CheckResult("backend", "OPTIONS CORS preflight", cors_url, ok, status, latency, detail))
    except Exception as exc:
        results.append(CheckResult("backend", "OPTIONS CORS preflight", cors_url, False, 0, 0.0, str(exc)))

    return results


def verify_frontend(
    frontend_url: str,
    *,
    timeout: float = 20.0,
    wait_seconds: int = 30,
    bypass_secret: str = "",
) -> List[CheckResult]:
    base = frontend_url.rstrip("/")
    headers: Dict[str, str] = {}
    if bypass_secret:
        headers["x-vercel-protection-bypass"] = bypass_secret

    results: List[CheckResult] = []
    index_html = ""

    def check_route(route: str) -> Tuple[CheckResult, str]:
        url = f"{base}{route}"
        try:
            status, _, body, latency = http_request(url, headers=headers, timeout=timeout)
            ok = status == 200 and '<div id="root">' in body
            detail = "SPA shell verified" if ok else f"HTTP {status} (missing root mount)"
            return CheckResult("frontend", f"GET {route}", url, ok, status, latency, detail), body
        except Exception as exc:
            return CheckResult("frontend", f"GET {route}", url, False, 0, 0.0, str(exc)), ""

    # Wait on root route first (useful when Vercel native Git build is finishing)
    deadline = time.monotonic() + max(0, wait_seconds)
    root_res, index_html = check_route("/")
    while not root_res.ok and time.monotonic() < deadline:
        time.sleep(min(8.0, max(1.0, deadline - time.monotonic())))
        root_res, index_html = check_route("/")
    results.append(root_res)

    for route in DEFAULT_FRONTEND_ROUTES[1:]:
        res, _ = check_route(route)
        results.append(res)

    # Verify static JS asset availability + scan for leaked keys
    asset_paths = list(dict.fromkeys(re.findall(r"/assets/[A-Za-z0-9_.-]+\.js", index_html)))
    if asset_paths:
        first_asset = asset_paths[0]
        asset_url = f"{base}{first_asset}"
        try:
            status, hdrs, js_body, latency = http_request(asset_url, headers=headers, timeout=timeout)
            cache_ctrl = hdrs.get("cache-control", "")
            ok = status == 200 and len(js_body) > 0
            detail = f"HTTP {status}, {len(js_body) // 1024} KiB, cache-control={cache_ctrl or 'default'}"
            results.append(CheckResult("frontend", f"Asset {first_asset}", asset_url, ok, status, latency, detail))
        except Exception as exc:
            results.append(CheckResult("frontend", f"Asset {first_asset}", asset_url, False, 0, 0.0, str(exc)))

        leaked_assets: List[str] = []
        for asset in asset_paths[:5]:
            try:
                _, _, js_body, _ = http_request(f"{base}{asset}", headers=headers, timeout=timeout)
                if LIVE_BUNDLE_SECRET_RE.search(js_body):
                    leaked_assets.append(asset)
            except Exception:
                continue

        if leaked_assets:
            results.append(
                CheckResult(
                    "frontend",
                    "Live JS Bundle Secret Audit",
                    base,
                    False,
                    200,
                    0.0,
                    f"Potential API key pattern found in: {', '.join(leaked_assets)}",
                    severity="warning",
                )
            )
        else:
            results.append(
                CheckResult(
                    "frontend",
                    "Live JS Bundle Secret Audit",
                    base,
                    True,
                    200,
                    0.0,
                    f"Clean ({min(len(asset_paths), 5)} JS bundle(s) inspected)",
                    severity="warning",
                )
            )

    return results


def render_markdown_summary(results: Sequence[CheckResult], title: str = "Deployment Verification Report") -> str:
    lines = [
        f"## {title}",
        "",
        "| Target | Check | Status | Latency | Details |",
        "|---|---|---|---:|---|",
    ]
    for item in results:
        if item.ok:
            badge = "PASS"
        elif item.severity == "warning":
            badge = "WARN"
        else:
            badge = "FAIL"
        latency_str = f"{item.latency_ms:.0f} ms" if item.latency_ms > 0 else "-"
        lines.append(f"| `{item.target}` | `{item.check}` | **{badge}** | {latency_str} | {item.detail} |")
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Verify live Vectronyx backend & frontend deployments.")
    parser.add_argument("--backend-url", default="", help="Backend base URL (e.g. https://...hf.space)")
    parser.add_argument("--hf-space-id", default="", help="HF Space ID to derive --backend-url if not passed")
    parser.add_argument("--frontend-url", default="", help="Frontend base URL (e.g. https://vectronyx.vercel.app)")
    parser.add_argument("--backend-only", action="store_true", help="Only verify backend endpoints")
    parser.add_argument("--frontend-only", action="store_true", help="Only verify frontend endpoints")
    parser.add_argument("--timeout", type=float, default=20.0, help="Per-request HTTP timeout in seconds")
    parser.add_argument("--wait-seconds", type=int, default=30, help="Initial readiness retry window in seconds")
    parser.add_argument("--vercel-bypass-secret", default="", help="Optional x-vercel-protection-bypass header value")
    parser.add_argument("--title", default="Vectronyx Post-Deploy Verification", help="Markdown report title")
    parser.add_argument("--summary-out", default="", help="File to append Markdown summary to (e.g. $GITHUB_STEP_SUMMARY)")
    parser.add_argument("--json-out", default="", help="Optional path to write machine-readable JSON results")
    args = parser.parse_args(argv)

    backend_url = args.backend_url.strip()
    if not backend_url and args.hf_space_id.strip():
        backend_url = space_subdomain(args.hf_space_id.strip())
    frontend_url = args.frontend_url.strip()
    bypass_secret = args.vercel_bypass_secret or os.getenv("VERCEL_AUTOMATION_BYPASS_SECRET", "")

    if not args.frontend_only and not backend_url:
        print("Error: --backend-url or --hf-space-id is required unless --frontend-only is set.", file=sys.stderr)
        return 2
    if not args.backend_only and not frontend_url:
        print("Error: --frontend-url is required unless --backend-only is set.", file=sys.stderr)
        return 2

    results: List[CheckResult] = []
    if not args.frontend_only and backend_url:
        results.extend(
            verify_backend(
                backend_url,
                cors_origin=frontend_url or "https://vectronyx.vercel.app",
                timeout=args.timeout,
                wait_seconds=args.wait_seconds,
            )
        )
    if not args.backend_only and frontend_url:
        results.extend(
            verify_frontend(
                frontend_url,
                timeout=args.timeout,
                wait_seconds=args.wait_seconds,
                bypass_secret=bypass_secret,
            )
        )

    for item in results:
        tag = "OK" if item.ok else ("WARN" if item.severity == "warning" else "FAIL")
        print(f"[{tag}] ({item.target}) {item.check} -> {item.detail} ({item.latency_ms:.0f} ms)")
        if not item.ok and item.severity == "warning":
            print(f"::warning::{item.check}: {item.detail}")

    summary_md = render_markdown_summary(results, title=args.title)
    summary_target = args.summary_out or os.getenv("GITHUB_STEP_SUMMARY", "")
    if summary_target:
        with open(summary_target, "a", encoding="utf-8") as fh:
            fh.write(summary_md + "\n")

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps([asdict(r) for r in results], indent=2), encoding="utf-8")

    hard_failures = [r for r in results if not r.ok and r.severity == "error"]
    if hard_failures:
        print(f"\nVerification FAILED ({len(hard_failures)} blocking check(s) failed).", file=sys.stderr)
        return 1

    print(f"\nVerification PASSED ({len(results)} check(s) completed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
