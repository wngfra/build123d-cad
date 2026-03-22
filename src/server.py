"""build123d MCP Server — parametric 3D CAD for LLM agents.

Tools:
  cad_generate  — Execute build123d script → export STEP/STL/SVG
  cad_measure   — Execute build123d script → bounding box, volume, mass, face/edge count
  cad_section   — Generate 2D cross-section SVG at a given plane + offset
  cad_list_api  — Return build123d API cheatsheet (no LLM call, pure reference)

All tools accept a `script` param: valid build123d Python code that assigns
the final solid to a variable named `result` (BuildPart context).

Runs in-process (no subprocess). build123d is imported once at startup.
Outputs go to a configurable workspace dir (default: ./cad-workspace).
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "build123d-cad",
    instructions=(
        "Parametric 3D CAD server. Generate STEP/STL/SVG files from build123d Python scripts. "
        "Scripts must use `with BuildPart() as result:` so the output solid is in `result.part`. "
        "All dimensions are in millimeters."
    ),
)

WORKSPACE = Path(os.environ.get("CAD_WORKSPACE", os.path.expanduser("~/.openclaw/workspace/cad-output")))
WORKSPACE.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exec_script(script: str) -> dict:
    """Execute a build123d script and return the `result` context object.

    Returns {"ok": True, "result": <BuildPart>, "stdout": "..."} on success,
    or {"ok": False, "error": "...", "stdout": "..."} on failure.
    """
    capture = io.StringIO()
    ns: dict = {}
    try:
        # Redirect stdout so print() in user scripts is captured
        old_stdout = sys.stdout
        sys.stdout = capture
        exec(script, ns)
    except Exception:
        return {"ok": False, "error": traceback.format_exc(), "stdout": capture.getvalue()}
    finally:
        sys.stdout = old_stdout

    result = ns.get("result")
    if result is None:
        return {
            "ok": False,
            "error": (
                "Script ran but `result` is not defined. "
                "Use `with BuildPart() as result:` to assign the output solid."
            ),
            "stdout": capture.getvalue(),
        }
    return {"ok": True, "result": result, "stdout": capture.getvalue()}


def _get_part(ctx):
    """Extract the Part/Solid from a BuildPart context or bare Shape."""
    if hasattr(ctx, "part"):
        return ctx.part
    if hasattr(ctx, "sketch"):
        return ctx.sketch
    return ctx


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def cad_generate(
    script: str,
    export_format: Literal["step", "stl", "svg"] = "step",
    filename: str | None = None,
) -> dict:
    """Execute a build123d Python script and export the resulting solid.

    The script MUST assign the final solid to `result` via:
        from build123d import *
        with BuildPart() as result:
            Box(100, 60, 40)
            ...

    Args:
        script: Complete build123d Python code.
        export_format: "step" (default, CAD interchange), "stl" (mesh for 3D printing), or "svg" (2D projection).
        filename: Output filename without extension. Auto-generated if omitted.

    Returns:
        Dictionary with artifact_path, format, file_size_bytes, and bounding_box.
    """
    r = _exec_script(script)
    if not r["ok"]:
        return {"success": False, "error": r["error"], "stdout": r["stdout"]}

    part = _get_part(r["result"])
    fname = filename or f"model_{id(part) % 100000:05d}"
    out_path = WORKSPACE / f"{fname}.{export_format}"

    try:
        from build123d import export_step, export_stl, export_svg

        if export_format == "step":
            export_step(part, str(out_path))
        elif export_format == "stl":
            export_stl(part, str(out_path))
        elif export_format == "svg":
            export_svg(part, str(out_path))
        else:
            return {"success": False, "error": f"Unknown format: {export_format}"}
    except Exception:
        return {"success": False, "error": traceback.format_exc(), "stdout": r["stdout"]}

    bb = part.bounding_box()
    return {
        "success": True,
        "artifact_path": str(out_path.resolve()),
        "format": export_format,
        "file_size_bytes": out_path.stat().st_size,
        "bounding_box_mm": {"x": round(bb.size.X, 2), "y": round(bb.size.Y, 2), "z": round(bb.size.Z, 2)},
        "stdout": r["stdout"],
    }


@mcp.tool()
def cad_measure(script: str) -> dict:
    """Execute a build123d script and return measurements of the resulting solid.

    Returns bounding box, volume, surface area, center of mass, face/edge counts.
    Uses the same script format as cad_generate.

    Args:
        script: Complete build123d Python code with `result` assigned.

    Returns:
        Dictionary with bounding_box_mm, volume_mm3, surface_area_mm2, center_of_mass_mm, face_count, edge_count.
    """
    r = _exec_script(script)
    if not r["ok"]:
        return {"success": False, "error": r["error"], "stdout": r["stdout"]}

    part = _get_part(r["result"])

    try:
        bb = part.bounding_box()
        com = part.center()
        return {
            "success": True,
            "bounding_box_mm": {"x": round(bb.size.X, 2), "y": round(bb.size.Y, 2), "z": round(bb.size.Z, 2)},
            "volume_mm3": round(part.volume, 2),
            "surface_area_mm2": round(part.area, 2),
            "center_of_mass_mm": {"x": round(com.X, 2), "y": round(com.Y, 2), "z": round(com.Z, 2)},
            "face_count": len(part.faces()),
            "edge_count": len(part.edges()),
            "stdout": r["stdout"],
        }
    except Exception:
        return {"success": False, "error": traceback.format_exc(), "stdout": r["stdout"]}


@mcp.tool()
def cad_section(
    script: str,
    plane: Literal["XY", "XZ", "YZ"] = "XY",
    offset: float = 0.0,
    filename: str | None = None,
) -> dict:
    """Generate a 2D cross-section SVG of a build123d solid at a given plane and offset.

    Useful for clearance checks, mechanical drawings, and visualizing internal geometry.

    Args:
        script: Complete build123d Python code with `result` assigned.
        plane: Section plane — "XY" (top/bottom), "XZ" (front/back), "YZ" (left/right).
        offset: Offset from origin along the plane normal, in mm.
        filename: Output filename without extension.

    Returns:
        Dictionary with artifact_path and section_edge_count.
    """
    r = _exec_script(script)
    if not r["ok"]:
        return {"success": False, "error": r["error"], "stdout": r["stdout"]}

    part = _get_part(r["result"])
    fname = filename or f"section_{plane}_{offset}"
    out_path = WORKSPACE / f"{fname}.svg"

    try:
        from build123d import Plane, export_svg

        planes = {"XY": Plane.XY, "XZ": Plane.XZ, "YZ": Plane.YZ}
        section_plane = planes[plane].offset(offset)
        section = part.section(plane=section_plane)

        export_svg(section, str(out_path))

        return {
            "success": True,
            "artifact_path": str(out_path.resolve()),
            "plane": plane,
            "offset_mm": offset,
            "section_edge_count": len(section.edges()) if hasattr(section, "edges") else 0,
            "stdout": r["stdout"],
        }
    except Exception:
        return {"success": False, "error": traceback.format_exc(), "stdout": r["stdout"]}


@mcp.tool()
def cad_list_api() -> dict:
    """Return a build123d API cheatsheet — primitives, operations, selectors, and export functions.

    No script execution. Use this to learn what's available before writing a script.
    """
    return {
        "primitives_3d": [
            "Box(length, width, height)",
            "Cylinder(radius, height)",
            "Sphere(radius)",
            "Cone(bottom_radius, top_radius, height)",
            "Torus(major_radius, minor_radius)",
            "Wedge(dx, dy, dz, xmin, zmin, xmax, zmax)",
        ],
        "primitives_2d": [
            "Circle(radius)",
            "Rectangle(width, height)",
            "Ellipse(x_radius, y_radius)",
            "Polygon(pts=[(x,y), ...])",
            "RegularPolygon(radius, side_count)",
            "SlotOverall(width, height)",
            "Text(txt, font_size)",
        ],
        "operations": [
            "extrude(amount=N)  — 2D sketch → 3D solid",
            "revolve(axis=Axis.Z, revolution_arc=360)",
            "loft(sections=[...])  — blend between profiles",
            "sweep(path=wire)  — extrude along a path",
            "fillet(edges, radius=N)",
            "chamfer(edges, length=N)",
            "offset(amount=N)  — shell / offset",
            "mirror(about=Plane.XZ)",
            "split(bisect_by=Plane.XY)",
            "section(plane=Plane.XY)  — 2D cross-section",
        ],
        "holes": [
            "Hole(radius, depth)",
            "CounterBoreHole(radius, counter_bore_radius, counter_bore_depth, depth)",
            "CounterSinkHole(radius, counter_sink_radius, depth)",
        ],
        "positioning": [
            "Pos(x, y, z)  — translate",
            "Rot(x, y, z)  — rotate (degrees)",
            "Locations((x,y,z), ...)  — place at multiple points",
            "GridLocations(x_spacing, y_spacing, x_count, y_count)",
            "PolarLocations(radius, count)",
            "Plane.XY / .XZ / .YZ  — reference planes",
            "Axis.X / .Y / .Z  — reference axes",
        ],
        "selectors": [
            "part.faces()  — all faces",
            "part.edges()  — all edges",
            "part.vertices()  — all vertices",
            ".filter_by(Axis.Z)  — filter by direction",
            ".sort_by(Axis.Z)  — sort by position",
            ".group_by(Axis.Z)  — group by position",
            "[-1]  — last (topmost/rightmost)",
            "[0]   — first (bottommost/leftmost)",
        ],
        "boolean": [
            "+  (add/union)",
            "-  (subtract/cut)",
            "&  (intersect)",
        ],
        "export": [
            "export_step(part, 'file.step')",
            "export_stl(part, 'file.stl')",
            "export_svg(part_or_sketch, 'file.svg')",
            "export_brep(part, 'file.brep')",
        ],
        "import": [
            "import_step('file.step')",
            "import_stl('file.stl')",
            "import_svg('file.svg')",
            "import_brep('file.brep')",
        ],
        "assembly": [
            "assy = Assembly()",
            "assy.add(part, name='base', loc=Pos(0,0,0) * Rot(0,0,0))",
        ],
        "pattern": (
            "from build123d import *\n"
            "with BuildPart() as result:\n"
            "    Box(100, 60, 40)\n"
            "    fillet(result.edges().filter_by(Axis.Z), radius=5)\n"
            "    with Locations((0, 0, 40)):\n"
            "        CounterBoreHole(radius=5, counter_bore_radius=8, counter_bore_depth=3, depth=40)"
        ),
        "notes": [
            "All dimensions in millimeters",
            "Always use `with BuildPart() as result:` — the server expects `result`",
            "Parameterize dimensions (no magic numbers) for reusability",
            "Add fillets to stress concentrations (min 1mm plastic, 0.5mm metal)",
            "export_step for CAD interchange, export_stl for 3D printing",
        ],
    }


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("cad://workspace/files")
def list_workspace_files() -> str:
    """List all files in the CAD workspace directory."""
    files = sorted(WORKSPACE.iterdir())
    if not files:
        return "Workspace is empty."
    lines = []
    for f in files:
        size = f.stat().st_size
        lines.append(f"{f.name}  ({size:,} bytes)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run()


if __name__ == "__main__":
    main()
