#!/usr/bin/env python3
"""
Deploy Vectronyx FastAPI backend to Hugging Face Spaces (Gradio + FastAPI mount or Docker SDK).

Usage:
    python scripts/deploy_hf_space.py --space-id <hf-user>/vectronyx-backend [--sync-env]
"""
import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import dotenv_values
from huggingface_hub import HfApi, get_token


SECRET_KEYS = (
    "DATABASE_URL",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_PUBLISHABLE_KEY",
    "SECRET_KEY",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
)

VARIABLE_KEYS = (
    "ENVIRONMENT",
    "DEBUG",
    "SUPABASE_STORAGE_BUCKET",
    "LLM_PROVIDER",
    "GEMINI_MODEL",
    "GROQ_MODEL",
    "EMBEDDING_PROVIDER",
    "EMBEDDING_MODEL",
    "FASTEMBED_MODEL",
    "VECTOR_STORE_PROVIDER",
    "VECTOR_DIMENSION",
    "ALLOWED_ORIGINS",
)


def space_subdomain(space_id: str) -> str:
    """Convert Hugging Face 'owner/space_name' into '*.hf.space' subdomain."""
    owner, name = space_id.split("/", 1)
    safe_owner = re.sub(r"[^a-z0-9-]", "-", owner.lower())
    safe_name = re.sub(r"[^a-z0-9-]", "-", name.lower())
    return f"https://{safe_owner}-{safe_name}.hf.space"


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy Vectronyx backend to Hugging Face Spaces")
    parser.add_argument(
        "--space-id",
        help="Target HF Space ID (e.g. 'din-esh-kumar/vectronyx-backend'). Defaults to '<current-user>/vectronyx-backend'.",
    )
    parser.add_argument(
        "--sdk",
        choices=("gradio", "docker"),
        default="gradio",
        help="Hugging Face Space SDK ('gradio' runs backend/space_app.py; 'docker' uses backend/Dockerfile).",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Create the Space as private (default: public so Vercel can reach it without HF token).",
    )
    parser.add_argument(
        "--sync-env",
        action="store_true",
        help="Sync backend secrets and variables from root .env to the Space.",
    )
    args = parser.parse_args()

    token = os.getenv("HF_TOKEN") or get_token()
    if not token:
        print("Error: Not authenticated with Hugging Face. Run 'hf auth login' first or set HF_TOKEN.", file=sys.stderr)
        return 1

    api = HfApi(token=token)
    who = api.whoami()
    username = who.get("name")
    space_id = args.space_id or f"{username}/vectronyx-backend"

    repo_root = Path(__file__).resolve().parent.parent
    backend_dir = repo_root / "backend"
    if not (backend_dir / "README.md").is_file():
        print("Error: backend/README.md is required for Hugging Face Spaces.", file=sys.stderr)
        return 1
    if args.sdk == "gradio" and not (backend_dir / "space_app.py").is_file():
        print("Error: backend/space_app.py is required for HF Gradio Spaces.", file=sys.stderr)
        return 1
    if args.sdk == "docker" and not (backend_dir / "Dockerfile").is_file():
        print("Error: backend/Dockerfile is required for HF Docker Spaces.", file=sys.stderr)
        return 1

    print(f"Ensuring Hugging Face {args.sdk} Space exists: {space_id}")
    api.create_repo(
        repo_id=space_id,
        repo_type="space",
        space_sdk=args.sdk,
        private=args.private,
        exist_ok=True,
    )

    if args.sync_env:
        env_path = repo_root / ".env"
        if not env_path.is_file():
            print(f"Warning: {env_path} not found; skipping secret sync.", file=sys.stderr)
        else:
            env_map = dotenv_values(env_path)
            print("Syncing secrets and variables from .env to Space...")
            for key in SECRET_KEYS:
                val = (env_map.get(key) or "").strip()
                if val:
                    if key == "DATABASE_URL" and ".supabase.co:" in val and "pooler.supabase.com" not in val:
                        print(
                            "  [Notice] DATABASE_URL uses direct db.*.supabase.co host. "
                            "HF Spaces uses IPv4 outbound networking; if DB queries fail, switch to Supabase's IPv4 Session Pooler URL."
                        )
                    api.add_space_secret(repo_id=space_id, key=key, value=val)
                    print(f"  Synced secret: {key}")

            for key in VARIABLE_KEYS:
                val = (env_map.get(key) or "").strip()
                if key == "ENVIRONMENT":
                    val = "production"
                elif key == "DEBUG":
                    val = "False"
                elif key == "ALLOWED_ORIGINS" and (not val or "localhost" in val):
                    val = "*"
                if val:
                    api.add_space_variable(repo_id=space_id, key=key, value=val)
                    print(f"  Synced variable: {key}={val}")

    ignore_patterns = [
        "**/__pycache__/**",
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        ".venv/**",
        "venv/**",
        ".pytest_cache/**",
        "**/.pytest_cache/**",
        "tests/**",
        ".env*",
    ]
    if args.sdk == "gradio":
        ignore_patterns.extend(["Dockerfile", ".dockerignore"])

    print(f"Uploading {backend_dir} to Space {space_id}...")
    api.upload_folder(
        folder_path=str(backend_dir),
        repo_id=space_id,
        repo_type="space",
        commit_message="Deploy Vectronyx backend to Hugging Face Space",
        ignore_patterns=ignore_patterns,
        delete_patterns=["*"],
    )

    api_url = space_subdomain(space_id)
    print("\nDeployment uploaded successfully!")
    print(f"  HF Space Page : https://huggingface.co/spaces/{space_id}")
    print(f"  Backend URL   : {api_url}")
    print(f"  Health Check  : {api_url}/health")
    print("\nNext step for Vercel Frontend:")
    print(f"  Set VITE_API_URL={api_url} in Vercel Project Settings -> Environment Variables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

