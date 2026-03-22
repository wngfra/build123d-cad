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

# install (requires Python 3.10+)
uv pip install -e .
# or
pip install -e .
```

build123d pulls in OpenCascade (~800MB). First install takes a few minutes.

## OpenClaw integration

Add to `~/.openclaw/openclaw.json`:

```json5
{
  mcpServers: {
    "build123d": {
      command: "python",
      args: ["-m", "src.server"],
      cwd: "~/.openclaw/mcp-servers/build123d-mcp"
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
      "command": "python",
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
# stdio transport (default)
python -m src.server

# streamable HTTP
CAD_WORKSPACE=/tmp/cad python -m src.server --transport streamable-http --port 8100
```

## Test

```bash
uv run pytest tests/ -v
```
