# build123d-mcp

MCP server for parametric 3D CAD via [build123d](https://github.com/gumyr/build123d). Generates STEP, STL, SVG from Python scripts.

## Tools

| Tool | Description |
|------|-------------|
| `cad_generate` | Execute build123d script → export STEP/STL/SVG |
| `cad_measure` | Execute build123d script → bounding box, volume, surface area, center of mass |
| `cad_section` | Generate 2D cross-section SVG at a given plane + offset |
| `cad_list_api` | Return build123d API cheatsheet (no execution) |

## Install

```bash
# clone to OpenClaw's MCP server directory
git clone https://github.com/xintlabs/build123d-mcp.git ~/.openclaw/mcp-servers/build123d-mcp
cd ~/.openclaw/mcp-servers/build123d-mcp

# create venv pinned to Python 3.12 (build123d requires <=3.12 for OpenCascade wheels)
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .
```

build123d pulls in OpenCascade (~800MB). First install takes a few minutes. `uv` auto-downloads Python 3.12 if not present.

> **Note:** Your system Python version doesn't matter. The MCP server runs in its own venv. OpenClaw spawns it as a child process — they never share a runtime.

## OpenClaw integration

Add to `~/.openclaw/openclaw.json`:

```json5
{
  "mcpServers": {
    "build123d": {
      "command": "~/.openclaw/mcp-servers/build123d-mcp/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "~/.openclaw/mcp-servers/build123d-mcp"
    }
  }
}
```

Restart gateway: `openclaw gateway restart`

Your agent now has `cad_generate`, `cad_measure`, `cad_section`, and `cad_list_api` tools. Exported files land in `~/.openclaw/workspace/cad-output/` — accessible to the agent via normal file tools.

## Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "build123d": {
      "command": "~/.openclaw/mcp-servers/build123d-mcp/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "~/.openclaw/mcp-servers/build123d-mcp"
    }
  }
}
```

## Script format

All tools expect a `script` parameter with valid build123d Python. The final solid must be assigned to `result`:

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

## Run standalone

```bash
cd ~/.openclaw/mcp-servers/build123d-mcp

# stdio transport (default)
.venv/bin/python -m src.server

# streamable HTTP
CAD_WORKSPACE=/tmp/cad .venv/bin/python -m src.server --transport streamable-http --port 8100
```

## Test

```bash
cd ~/.openclaw/mcp-servers/build123d-mcp
.venv/bin/python -m pytest tests/ -v
```