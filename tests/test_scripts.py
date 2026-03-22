"""Tests for build123d CAD scripts.

Run: .venv/bin/python -m pytest tests/ -v
"""

import subprocess
import json
import os
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
PYTHON = Path(__file__).parent.parent / ".venv" / "bin" / "python"


def run_script(name: str, args: list[str]) -> dict:
    r = subprocess.run(
        [str(PYTHON), str(SCRIPTS / name)] + args,
        capture_output=True, text=True, timeout=60,
        cwd=str(SCRIPTS),
    )
    return json.loads(r.stdout)


def test_generate_step():
    out = run_script("cad_generate.py", [
        "--script", "from build123d import *\nwith BuildPart() as result:\n    Box(10, 20, 30)",
        "--format", "step",
    ])
    assert out["success"]
    assert Path(out["artifact_path"]).exists()
    assert out["bounding_box_mm"]["z"] == pytest.approx(30.0, abs=0.5)


def test_generate_stl():
    out = run_script("cad_generate.py", [
        "--script", "from build123d import *\nwith BuildPart() as result:\n    Cylinder(5, 10)",
        "--format", "stl",
    ])
    assert out["success"]
    assert out["format"] == "stl"


def test_measure_box():
    out = run_script("cad_measure.py", [
        "--script", "from build123d import *\nwith BuildPart() as result:\n    Box(10, 20, 30)",
    ])
    assert out["success"]
    assert out["volume_mm3"] == pytest.approx(6000.0, abs=1.0)
    assert out["face_count"] == 6


def test_section():
    out = run_script("cad_section.py", [
        "--script", "from build123d import *\nwith BuildPart() as result:\n    Box(10, 10, 10)",
        "--plane", "XY", "--offset", "5.0",
    ])
    assert out["success"]
    assert Path(out["artifact_path"]).suffix == ".svg"


def test_api():
    out = run_script("cad_api.py", [])
    assert "primitives_3d" in out
    assert "pattern" in out


def test_bad_script():
    out = run_script("cad_generate.py", [
        "--script", "raise ValueError('boom')",
        "--format", "step",
    ])
    assert not out["success"]
    assert "boom" in out["error"]
