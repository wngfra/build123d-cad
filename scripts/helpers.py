"""Shared helpers for build123d CAD scripts."""

import io
import json
import os
import sys
import traceback
from pathlib import Path


WORKSPACE = Path(os.environ.get("CAD_WORKSPACE", os.path.expanduser("~/.openclaw/workspace/cad-output")))
WORKSPACE.mkdir(parents=True, exist_ok=True)


def exec_script(script: str) -> dict:
    """Execute a build123d script. Returns {"ok", "result", "stdout"} or {"ok": False, "error", "stdout"}."""
    capture = io.StringIO()
    ns = {}
    try:
        old = sys.stdout
        sys.stdout = capture
        exec(script, ns)
    except Exception:
        return {"ok": False, "error": traceback.format_exc(), "stdout": capture.getvalue()}
    finally:
        sys.stdout = old

    result = ns.get("result")
    if result is None:
        return {"ok": False, "error": "Script ran but `result` is not defined. Use `with BuildPart() as result:`.", "stdout": capture.getvalue()}
    return {"ok": True, "result": result, "stdout": capture.getvalue()}


def get_part(ctx):
    """Extract Part from BuildPart context or bare Shape."""
    if hasattr(ctx, "part"):
        return ctx.part
    if hasattr(ctx, "sketch"):
        return ctx.sketch
    return ctx


def output_json(data: dict):
    """Print JSON to stdout and exit."""
    print(json.dumps(data))
    sys.exit(0 if data.get("success", False) else 1)


def output_error(error: str, stdout: str = ""):
    """Print error JSON to stdout and exit 1."""
    print(json.dumps({"success": False, "error": error, "stdout": stdout}))
    sys.exit(1)
