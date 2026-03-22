"""Tests for build123d MCP server tools.

Run: .venv/bin/python -m pytest tests/ -v
Requires build123d installed (OpenCascade kernel).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from server import _exec_script, _get_part, WORKSPACE


def test_exec_simple_box():
    r = _exec_script("from build123d import *\nwith BuildPart() as result:\n    Box(10, 20, 30)")
    assert r["ok"], r.get("error")
    part = _get_part(r["result"])
    assert abs(part.volume - 6000.0) < 1.0


def test_exec_no_result():
    r = _exec_script("x = 42")
    assert not r["ok"]
    assert "result" in r["error"].lower()


def test_exec_syntax_error():
    r = _exec_script("def foo(:\n  pass")
    assert not r["ok"]


def test_generate_step():
    from server import cad_generate
    script = "from build123d import *\nwith BuildPart() as result:\n    Cylinder(10, 50)"
    out = cad_generate(script, export_format="step")
    assert out["success"], out.get("error")
    assert out["format"] == "step"
    assert Path(out["artifact_path"]).exists()
    assert out["bounding_box_mm"]["z"] == pytest.approx(50.0, abs=0.5)


def test_generate_stl():
    from server import cad_generate
    script = "from build123d import *\nwith BuildPart() as result:\n    Box(5, 5, 5)"
    out = cad_generate(script, export_format="stl")
    assert out["success"], out.get("error")
    assert Path(out["artifact_path"]).suffix == ".stl"


def test_generate_bad_script():
    from server import cad_generate
    out = cad_generate("raise ValueError('boom')", export_format="step")
    assert not out["success"]
    assert "boom" in out["error"]


def test_measure_box():
    from server import cad_measure
    script = "from build123d import *\nwith BuildPart() as result:\n    Box(10, 20, 30)"
    out = cad_measure(script)
    assert out["success"], out.get("error")
    assert out["volume_mm3"] == pytest.approx(6000.0, abs=1.0)
    assert out["face_count"] == 6
    assert out["edge_count"] == 12


def test_section_xy():
    from server import cad_section
    script = "from build123d import *\nwith BuildPart() as result:\n    Box(10, 10, 10)"
    out = cad_section(script, plane="XY", offset=5.0)
    assert out["success"], out.get("error")
    assert Path(out["artifact_path"]).suffix == ".svg"


def test_list_api():
    from server import cad_list_api
    out = cad_list_api()
    assert "primitives_3d" in out
    assert "operations" in out
    assert "pattern" in out
