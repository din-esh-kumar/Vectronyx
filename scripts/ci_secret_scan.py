#!/usr/bin/env python3
"""
Vectronyx CI/CD Secret & Client Exposure Scanner.

Scans tracked repository files (`git ls-files`) and optional build output
directories (`--paths frontend/dist`) for leaked API keys, database
passwords, private keys, or forbidden `VITE_*` secret environment variables.

Usage:
    python scripts/ci_secret_scan.py
    python scripts/ci_secret_scan.py --paths frontend/dist
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".svgz",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".tgz",
    ".whl",
    ".pyc",
    ".pyo",
    ".onnx",
    ".bin",
    ".db",
    ".sqlite",
}

TEST_PLACEHOLDER_MARKERS = (
    "INVALID",
    "TEST",
    "DUMMY",
    "EXAMPLE",
    "PLACEHOLDER",
    "YOUR_",
    "OVERRIDE",
)

DB_PASSWORD_PLACEHOLDERS = {
    "password",
    "your_password",
    "changeme",
    "postgres",
    "placeholder",
    "secret",
    "[your-password]",
    "<password>",
}

DB_HOST_ALLOWLIST = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "host",
    "db",
    "postgres",
    "vectronyx-db",
}

PATTERNS = {
    "groq_api_key": re.compile(r"\bgsk_[A-Za-z0-9_]{20,}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "gemini_oauth_token": re.compile(r"\bAQ\.Ab8[0-9A-Za-z_-]{20,}\b"),
    "supabase_secret_key": re.compile(r"\bsb_secret_[0-9A-Za-z_-]{15,}\b"),
    "huggingface_token": re.compile(r"\bhf_[A-Za-z]{2}[A-Za-z0-9]{18,}\b"),
    "github_token": re.compile(r"\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private_key_block": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
}

POSTGRES_URI_RE = re.compile(
    r"postgres(?:ql)?(?:\+\w+)?://[^:\s/\"']+:([^@\s/\"']+)@([A-Za-z0-9._-]+)"
)

FORBIDDEN_CLIENT_VARS_RE = re.compile(
    r"\b(VITE_GEMINI_API_KEY|VITE_GROQ_API_KEY|VITE_SUPABASE_SERVICE_ROLE_KEY|VITE_SECRET_KEY)\b"
)
FORBIDDEN_FRONTEND_ONLY_VARS_RE = re.compile(
    r"\b(SUPABASE_SERVICE_ROLE_KEY|SUPABASE_SECRET_KEY)\b"
)


@dataclass
class SecretFinding:
    rule: str
    path: str
    line: int
    preview: str


def redact_match(raw: str) -> str:
    if len(raw) <= 10:
        return "***"
    return f"{raw[:6]}...{raw[-2:]}"


def _is_placeholder_token(token: str) -> bool:
    upper = token.upper()
    return any(marker in upper for marker in TEST_PLACEHOLDER_MARKERS)


def scan_text(
    text: str,
    label: str,
    *,
    check_client_vars: bool = False,
    check_frontend_only_vars: bool = False,
) -> List[SecretFinding]:
    findings: List[SecretFinding] = []
    lines = text.splitlines()
    if not lines and text:
        lines = [text]

    for idx, line in enumerate(lines, start=1):
        for rule, pattern in PATTERNS.items():
            for match in pattern.finditer(line):
                val = match.group(0)
                if rule in ("groq_api_key", "google_api_key") and _is_placeholder_token(val):
                    continue
                if rule == "groq_api_key" and "_" in val[4:] and len(val) < 40:
                    # Short synthetic test identifiers using snake_case words (e.g., mock docs)
                    continue
                findings.append(
                    SecretFinding(
                        rule=rule,
                        path=label,
                        line=idx,
                        preview=redact_match(val),
                    )
                )

        for match in POSTGRES_URI_RE.finditer(line):
            password, host = match.group(1), match.group(2).lower()
            if password.lower() in DB_PASSWORD_PLACEHOLDERS or _is_placeholder_token(password):
                continue
            if host in DB_HOST_ALLOWLIST or "[" in password or "<" in password or "..." in password:
                continue
            findings.append(
                SecretFinding(
                    rule="postgres_credential_uri",
                    path=label,
                    line=idx,
                    preview=f"postgres://***:***@{host}",
                )
            )

        if check_client_vars:
            stripped = line.strip()
            is_comment = stripped.startswith(("#", "//", "*"))
            if not is_comment:
                for match in FORBIDDEN_CLIENT_VARS_RE.finditer(line):
                    findings.append(
                        SecretFinding(
                            rule="forbidden_client_secret_env",
                            path=label,
                            line=idx,
                            preview=match.group(1),
                        )
                    )
                if check_frontend_only_vars:
                    for match in FORBIDDEN_FRONTEND_ONLY_VARS_RE.finditer(line):
                        findings.append(
                            SecretFinding(
                                rule="forbidden_frontend_server_secret",
                                path=label,
                                line=idx,
                                preview=match.group(1),
                            )
                        )

    return findings


def _git_tracked_files(repo_root: Path) -> List[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=str(repo_root),
        capture_output=True,
        check=True,
    )
    rel_paths = [p for p in result.stdout.decode("utf-8", errors="ignore").split("\0") if p]
    return [repo_root / p for p in rel_paths]


def _iter_directory_files(target: Path) -> Iterable[Path]:
    if target.is_file():
        yield target
        return
    if not target.is_dir():
        return
    for item in target.rglob("*"):
        if item.is_file():
            yield item


def scan_paths(
    files: Sequence[Path],
    repo_root: Path,
    *,
    force_client_var_check: bool = False,
) -> List[SecretFinding]:
    findings: List[SecretFinding] = []
    for file_path in files:
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            continue
        try:
            rel = file_path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            rel = file_path.as_posix()

        check_frontend_only = force_client_var_check or rel.startswith(("frontend/src/", "frontend/dist/"))
        check_client = check_frontend_only or rel.endswith(".env.example")
        # Do not flag regex definitions inside this scanner itself
        if rel == "scripts/ci_secret_scan.py":
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        findings.extend(
            scan_text(
                content,
                rel,
                check_client_vars=check_client,
                check_frontend_only_vars=check_frontend_only,
            )
        )
    return findings


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Scan Vectronyx files and build artifacts for leaked secrets.")
    parser.add_argument(
        "--paths",
        nargs="*",
        default=[],
        help="Additional untracked paths/directories to scan (e.g. frontend/dist).",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    findings: List[SecretFinding] = []
    scanned_count = 0

    if not args.paths:
        tracked = _git_tracked_files(repo_root)
        env_tracked = [p for p in tracked if p.name == ".env"]
        for p in env_tracked:
            findings.append(
                SecretFinding(
                    rule="tracked_dotenv_file",
                    path=p.relative_to(repo_root).as_posix(),
                    line=1,
                    preview=".env must never be tracked in git",
                )
            )
        findings.extend(scan_paths(tracked, repo_root))
        scanned_count += len(tracked)
    else:
        extra_files: List[Path] = []
        for raw_path in args.paths:
            candidate = (repo_root / raw_path) if not Path(raw_path).is_absolute() else Path(raw_path)
            if not candidate.exists():
                print(f"Error: scan target does not exist: {candidate}", file=sys.stderr)
                return 2
            extra_files.extend(_iter_directory_files(candidate))
        findings.extend(scan_paths(extra_files, repo_root, force_client_var_check=True))
        scanned_count += len(extra_files)

    if findings:
        print(f"FAILED: Detected {len(findings)} potential secret/exposure violation(s):", file=sys.stderr)
        for item in findings:
            print(f"  - [{item.rule}] {item.path}:{item.line} ({item.preview})", file=sys.stderr)
        return 1

    scope = ", ".join(args.paths) if args.paths else "git tracked files"
    print(f"PASS: Secret scan clean ({scanned_count} file(s) inspected in {scope}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
