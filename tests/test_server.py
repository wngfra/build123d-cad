"""Tests for build123d MCP server tools.

Run: uv run pytest tests/ -v
Requires build123d installed (heavy dep — OpenCascade kernel).
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from server import _exec_script, _get_part, WORKSPACE


# --- _exec_script ---

def test_exec_simple_box():
    r = _exec_script("from build123d import *\nwith BuildPart() as result:\n    Box(10, 20, 30)")
    assert r["ok"], r.get("error")
    part = _get_part(r["result"])
    assert abs(part.volume - 6000.0) < 1.0  # 10*20*30


def test_exec_no_result():
    r = _exec_script("x = 42")
    assert not r["ok"]
    assert "result" in r["error"].lower()


def test_exec_syntax_error():
    r = _exec_script("def foo(:\n  pass")
    assert not r["ok"]
    assert "SyntaxError" in r["error"] or "invalid" in r["error"].lower()


# --- cad_generate ---

def test_generate_step():
    from server import cad_generate

    script = "from build123d import *\nwith BuildPart() as result:\n    Cylinder(10, 50)"
    out = cad_generate(script, export_format="step")
    assert out["success"], out.get("error")
    assert out["format"] == "step"
    assert Path(out["artifact_path"]).exists()
    assert out["file_size_bytes"] > 0
    assert out["bounding_box_mm"]["z"] == pytest.approx(50.0, abs=0.5)


def test_generate_stl():
    from server import cad_generate

    script = "from build123d import *\nwith BuildPart() as result:\n    Box(5, 5, 5)"
    out = cad_generate(script, export_format="stl")
    assert out["success"], out.get("error")
    assert out["format"] == "stl"
    assert Path(out["artifact_path"]).suffix == ".stl"


def test_generate_bad_script():
    from server import cad_generate

    out = cad_generate("raise ValueError('boom')", export_format="step")
    assert not out["success"]
    assert "boom" in out["error"]


# --- cad_measure ---

def test_measure_box():
    from server import cad_measure

    script = "from build123d import *\nwith BuildPart() as result:\n    Box(10, 20, 30)"
    out = cad_measure(script)
    assert out["success"], out.get("error")
    assert out["volume_mm3"] == pytest.approx(6000.0, abs=1.0)
    assert out["bounding_box_mm"]["x"] == pytest.approx(10.0, abs=0.5)
    assert out["bounding_box_mm"]["y"] == pytest.approx(20.0, abs=0.5)
    assert out["bounding_box_mm"]["z"] == pytest.approx(30.0, abs=0.5)
    assert out["face_count"] == 6  # box has 6 faces
    assert out["edge_count"] == 12  # box has 12 edges


# --- cad_section ---

def test_section_xy():
    from server import cad_section

    script = "from build123d import *\nwith BuildPart() as result:\n    Box(10, 10, 10)"
    out = cad_section(script, plane="XY", offset=5.0)
    assert out["success"], out.get("error")
    assert Path(out["artifact_path"]).suffix == ".svg"


# --- cad_list_api ---

def test_list_api():
    from server import cad_list_api

    out = cad_list_api()
    assert "primitives_3d" in out
    assert "operations" in out
    assert len(out["primitives_3d"]) > 0
    assert "pattern" in out
