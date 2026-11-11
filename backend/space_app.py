import os
import socket
import sys
from pathlib import Path

os.environ.setdefault("FASTEMBED_CACHE_PATH", "/tmp/fastembed_cache")
os.makedirs("/tmp/fastembed_cache", exist_ok=True)

# Ensure Space root directory is in sys.path so `app.*` imports resolve cleanly
ROOT_DIR = str(Path(__file__).resolve().parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Must import `spaces` before CUDA/gradio modules on HF ZeroGPU Spaces
try:
    import spaces  # type: ignore

    _HAS_SPACES = True
except ImportError:
    spaces = None  # type: ignore
    _HAS_SPACES = False

import gradio as gr
import uvicorn

from app.middleware.app import app as backend_app


def _gpu_decorator():
    if _HAS_SPACES and spaces is not None:
        return spaces.GPU(duration=15)
    return lambda fn: fn


@_gpu_decorator()
def run_gpu_probe() -> str:
    return "Vectronyx ZeroGPU worker ready ⚡"


with gr.Blocks(title="Vectronyx AI Workbench Backend") as demo:
    gr.Markdown("# ⚡ Vectronyx AI Workbench Backend")
    gr.Markdown("FastAPI + Gemini + Groq + Supabase pgvector API is live.")
    gr.Markdown("- Health probe: `/health`\n- Memory diagnostics: `/api/memory/status`\n- Swagger API Docs: `/docs`")
    probe_btn = gr.Button("Check ZeroGPU Worker")
    probe_out = gr.Textbox(label="Worker Status", interactive=False)
    probe_btn.click(fn=run_gpu_probe, outputs=probe_out)


app = gr.mount_gradio_app(backend_app, demo, path="/ui", ssr_mode=False)


def _find_available_port(host: str, start_port: int = 7860, tries: int = 50) -> int:
    for candidate in range(start_port, start_port + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, candidate))
                return candidate
            except OSError:
                continue
    return start_port


if __name__ == "__main__":
    gradio_port_env = os.getenv("GRADIO_SERVER_PORT")
    port_env = os.getenv("PORT")
    host = os.getenv("GRADIO_SERVER_NAME") or "0.0.0.0"

    if _HAS_SPACES:
        try:
            import spaces.zero as _spaces_zero  # type: ignore

            if hasattr(_spaces_zero, "startup"):
                _spaces_zero.startup()
        except Exception as exc:
            print(f"[space_app] spaces.zero.startup() warning: {exc}", flush=True)

    if gradio_port_env:
        port = int(gradio_port_env)
    elif port_env:
        port = int(port_env)
    else:
        port = _find_available_port(host, 7860)

    uvicorn.run(app, host=host, port=port)

