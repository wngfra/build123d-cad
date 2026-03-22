"""Shared helpers for build123d CAD scripts.

Security: user-supplied scripts NEVER execute in the parent process.
All execution happens in a sandboxed subprocess with:
  - Clean environment (no API keys, tokens, secrets)
  - Isolated tmpdir as cwd
  - Timeout (default 120s for complex geometry)
  - Result communicated via a JSON file, not stdout parsing

The parent constructs a full Python script (user code + operation), writes it
to a temp file, runs it in a subprocess, reads the result JSON file.
No geometry objects cross the process boundary.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


WORKSPACE = Path(os.environ.get("CAD_WORKSPACE", os.path.expanduser("~/.openclaw/workspace/cad-output")))
WORKSPACE.mkdir(parents=True, exist_ok=True)


def run_sandboxed(full_script: str, timeout: int = 120) -> dict:
    """Run a complete Python script in a sandboxed subprocess.

    The script must write JSON to the path in env var _RESULT_PATH.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "run.py"
        result_path = Path(tmpdir) / "result.json"
        script_path.write_text(full_script)

        clean_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": tmpdir,
            "TMPDIR": tmpdir,
            "PYTHONDONTWRITEBYTECODE": "1",
            "_RESULT_PATH": str(result_path),
            "_WORKSPACE": str(WORKSPACE),
        }
        venv = os.environ.get("VIRTUAL_ENV")
        if venv:
            clean_env["VIRTUAL_ENV"] = venv
            clean_env["PATH"] = f"{venv}/bin:{clean_env['PATH']}"

        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True, text=True,
                timeout=timeout, cwd=tmpdir, env=clean_env,
            )
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Script timed out after {timeout}s."}

        if result_path.exists():
            try:
                return json.loads(result_path.read_text())
            except (json.JSONDecodeError, OSError) as e:
                return {"success": False, "error": f"Bad result file: {e}", "stderr": proc.stderr[-2000:]}

        return {
            "success": False,
            "error": proc.stderr[-2000:] if proc.stderr else "No result produced.",
            "stdout": proc.stdout[-2000:],
        }


def output_json(data: dict):
    print(json.dumps(data))
    sys.exit(0 if data.get("success", False) else 1)
