#!/usr/bin/env python3
"""Make this folder work on any machine.

    python setup_codekit.py            # venv + mcp<2 + rewrite codekit paths in opencode.json
    python setup_codekit.py --models   # also pull/build the local Ollama models
"""
import json, shutil, subprocess, sys, tempfile, venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "python_server.py"
CONFIG = ROOT / "opencode.json"
VENV = ROOT / "venv"
VENV_PY = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

# name used in opencode.json -> base model to build it from
MODELS = {"llama32-16k": "llama3.2:3b", "qwen3-4b-16k": "qwen3:4b"}


def venv_works():
    try:
        return subprocess.run([str(VENV_PY), "--version"], capture_output=True).returncode == 0
    except OSError:
        return False


def ensure_venv():
    # a venv copied from another PC points at the old machine's Python, so rebuild it
    if VENV.exists() and not venv_works():
        print("venv is broken (probably copied from another PC), rebuilding ...")
        shutil.rmtree(VENV)
    if not VENV_PY.exists():
        print("creating venv ...")
        venv.create(VENV, with_pip=True)
    ok = subprocess.run([str(VENV_PY), "-c", "import mcp.server.fastmcp"],
                        capture_output=True).returncode == 0
    if not ok:
        print("installing mcp<2 ...")
        subprocess.check_call([str(VENV_PY), "-m", "pip", "install", "mcp<2"])


def update_config():
    if not CONFIG.exists():
        sys.exit(f"{CONFIG} not found. Copy opencode.json into this folder first.")
    if not SERVER.exists():
        sys.exit(f"{SERVER} not found.")
    data = json.loads(CONFIG.read_text(encoding="utf-8"))  # must be plain JSON, no comments
    data.setdefault("mcp", {})["codekit"] = {
        "type": "local",
        "command": [str(VENV_PY), str(SERVER)],
        "enabled": True,
        "environment": {"CODEKIT_ROOT": str(ROOT)},
    }
    CONFIG.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    print(f"updated codekit paths in {CONFIG}")


def verify_server():
    r = subprocess.run([str(VENV_PY), "-c", "import python_server"],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("server import failed:\n" + r.stderr)
    print("server imports OK")


def ensure_models():
    if not shutil.which("ollama"):
        print("Ollama not found on PATH. Install it from ollama.com, then re-run with --models.")
        return
    have = subprocess.run(["ollama", "list"], capture_output=True, text=True).stdout
    for name, base in MODELS.items():
        if name in have:
            print(f"model {name}: already there")
            continue
        print(f"pulling {base} ...")
        subprocess.check_call(["ollama", "pull", base])
        with tempfile.TemporaryDirectory() as d:
            mf = Path(d) / "Modelfile"
            mf.write_text(f"FROM {base}\nPARAMETER num_ctx 16384\n", encoding="ascii")
            subprocess.check_call(["ollama", "create", name, "-f", str(mf)])
        print(f"model {name}: built")


if __name__ == "__main__":
    ensure_venv()
    update_config()
    verify_server()
    if "--models" in sys.argv:
        ensure_models()
    print("\nDone. Next: run `opencode mcp list` in this folder. codekit should show as connected.")