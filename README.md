# build123d-mcp

OpenClaw skill + MCP server for parametric 3D CAD via [build123d](https://github.com/gumyr/build123d). Generates STEP, STL, SVG from Python scripts.

## Tools

| Tool | Description |
|------|-------------|
| `cad_generate` | Execute build123d script → export STEP/STL/SVG |
| `cad_measure` | Execute build123d script → bounding box, volume, surface area, center of mass |
| `cad_section` | Generate 2D cross-section SVG at a given plane + offset |
| `cad_list_api` | Return build123d API cheatsheet (no execution) |

## Install as OpenClaw skill

```bash
# clone into OpenClaw workspace skills
git clone https://github.com/xintlabs/build123d-mcp.git ~/.openclaw/workspace/skills/build123d-cad

# create venv pinned to Python 3.12 (build123d requires <=3.12 for OpenCascade wheels)
cd ~/.openclaw/workspace/skills/build123d-cad
uv venv --python 3.12
uv pip install -e .
```

Then add the MCP server to `~/.openclaw/openclaw.json`:

```json
{
  "mcpServers": {
    "build123d": {
      "command": "~/.openclaw/workspace/skills/build123d-cad/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "~/.openclaw/workspace/skills/build123d-cad"
    }
  }
}
```

Restart gateway:

```bash
openclaw gateway restart
```

OpenClaw loads the `SKILL.md` (teaches the agent when and how to use the tools) and connects to the MCP server (provides the actual tool implementations). Exported files land in `~/.openclaw/workspace/cad-output/`.

> **Note:** build123d requires Python ≤3.12 for OpenCascade wheels. Your system Python version doesn't matter — the MCP server runs in its own venv. `uv` auto-downloads 3.12 if needed.

## Also works with Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "build123d": {
      "command": "~/.openclaw/workspace/skills/build123d-cad/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "~/.openclaw/workspace/skills/build123d-cad"
    }
  }
}
```

## Script format

All tools expect a `script` parameter. The final solid must be assigned to `result`:

```python
from build123d import *

with BuildPart() as result:
    Box(100, 60, 40)
    fillet(result.edges().filter_by(Axis.Z), radius=5)
    with Locations((0, 0, 40)):
        CounterBoreHole(radius=5, counter_bore_radius=8, counter_bore_depth=3, depth=40)
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `CAD_WORKSPACE` | `~/.openclaw/workspace/cad-output` | Directory for exported files |

## Test

```bash
cd ~/.openclaw/workspace/skills/build123d-cad
.venv/bin/python -m pytest tests/ -v
```
