---
name: build123d-cad
description: >
  Parametric 3D CAD via build123d. Generate STEP, STL, SVG from Python scripts.
  Use when the user asks to design, model, create, or export 3D parts, enclosures,
  mounts, brackets, or mechanical components.
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins: ["uv"]
    emoji: "🔧"
---

# build123d CAD

Parametric 3D CAD via [build123d](https://build123d.readthedocs.io). This skill runs an MCP server that exposes 4 tools for generating and measuring 3D solids from Python scripts.

## Setup

The MCP server runs from `{baseDir}/src/server.py` in a Python 3.12 venv. On first use, set it up:

```bash
cd {baseDir}
uv venv --python 3.12
uv pip install -e .
```

## MCP Server

This skill bundles an MCP server. Add to your `~/.openclaw/openclaw.json`:

```json
{
  "mcpServers": {
    "build123d": {
      "command": "{baseDir}/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "{baseDir}"
    }
  }
}
```

Then restart: `openclaw gateway restart`

## Tools

Once the MCP server is connected, you have these tools:

### cad_generate

Execute a build123d script and export STEP, STL, or SVG.

```
cad_generate(script="from build123d import *\nwith BuildPart() as result:\n    Box(100,60,40)", export_format="step")
```

Returns: `{ success, artifact_path, format, file_size_bytes, bounding_box_mm }`

Exported files go to `~/.openclaw/workspace/cad-output/`.

### cad_measure

Execute a script and return measurements — bounding box, volume, surface area, center of mass, face/edge counts.

```
cad_measure(script="...")
```

Returns: `{ success, bounding_box_mm, volume_mm3, surface_area_mm2, center_of_mass_mm, face_count, edge_count }`

### cad_section

Generate a 2D cross-section SVG at a given plane and offset. Useful for clearance checks and mechanical drawings.

```
cad_section(script="...", plane="XY", offset=5.0)
```

Returns: `{ success, artifact_path, plane, offset_mm, section_edge_count }`

### cad_list_api

Return a build123d API cheatsheet — primitives, operations, selectors, export functions. No script execution. Call this first if you need to learn what's available.

## Script Format

All scripts must assign the final solid to `result` via a `BuildPart` context:

```python
from build123d import *

with BuildPart() as result:
    Box(100, 60, 40)
    fillet(result.edges().filter_by(Axis.Z), radius=5)
    with Locations((0, 0, 40)):
        CounterBoreHole(radius=5, counter_bore_radius=8, counter_bore_depth=3, depth=40)
```

All dimensions are in millimeters.

## Workflow

1. If unsure about build123d API, call `cad_list_api` first for the cheatsheet.
2. Write a parameterized script (no magic numbers).
3. Call `cad_measure` to verify dimensions before exporting.
4. Call `cad_generate` with the desired format (step for CAD interchange, stl for 3D printing).
5. For clearance checks, call `cad_section` at relevant planes.
6. Report artifact paths — they're in `~/.openclaw/workspace/cad-output/`, accessible via file tools.

## Design Rules

- Parameterize all dimensions for reusability.
- Add fillets to stress concentrations (min 1mm for plastic, 0.5mm for metal).
- Include mounting features (bosses, standoffs, screw posts) where applicable.
- Specify material and process assumptions in comments.
- Always output both the script and the exported file.
