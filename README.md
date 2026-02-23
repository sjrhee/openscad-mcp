# openscad-mcp

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io)

A **Model Context Protocol (MCP)** server that gives AI assistants the power to
generate, render, validate, and export 3D models using
[OpenSCAD](https://openscad.org/).

## Features

| Tool | Description |
|------|-------------|
| `check_openscad` | Verify OpenSCAD installation and version |
| `render_scad` | Render OpenSCAD code → PNG image (base64) |
| `multi_view_render` | Render front / back / left / right / top / bottom / isometric views |
| `export_stl` | Export OpenSCAD code → STL (for 3D printing) |
| `export_3mf` | Export OpenSCAD code → 3MF (preserves parametric data) |
| `validate_scad` | Syntax-check OpenSCAD code without rendering |
| `render_scad_file` | Render an existing `.scad` file → PNG |
| `export_scad_file` | Export an existing `.scad` file → STL / 3MF / DXF / SVG / AMF |

## Requirements

- **Python 3.10+**
- **OpenSCAD** installed on your system
  - macOS: `brew install openscad`
  - Windows: download from [openscad.org](https://openscad.org/downloads.html)
  - Ubuntu/Debian: `sudo apt install openscad`

## Installation

### From source

```bash
git clone https://github.com/sjrhee/openscad-mcp.git
cd openscad-mcp
pip install -e ".[dev]"
```

### With `uv` (recommended)

```bash
uv tool install openscad-mcp
```

## Usage

### Run as stdio MCP server (default)

```bash
openscad-mcp
# or
python -m openscad_mcp.server
```

### Run as SSE server

```bash
openscad-mcp --transport sse --host 0.0.0.0 --port 8000
```

### Custom OpenSCAD binary path

```bash
OPENSCAD_BINARY=/path/to/openscad openscad-mcp
```

## Claude Desktop Integration

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "openscad-mcp": {
      "command": "uvx",
      "args": ["--from", "openscad-mcp", "openscad-mcp"],
      "env": {
        "OPENSCAD_BINARY": "/usr/bin/openscad"
      }
    }
  }
}
```

Config file locations:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

## Example: Ask Claude to create a 3D model

Once the server is connected, you can prompt Claude:

> "Create a parametric box with lid in OpenSCAD — width=60mm, depth=40mm, height=30mm — and show me a render."

Claude will call `render_scad` and return a visual preview directly in the chat.

## Tool Reference

### `render_scad`

```python
render_scad(
    scad_code: str,
    width: int = 800,
    height: int = 600,
    camera_translate_x: float = 0,
    camera_translate_y: float = 0,
    camera_translate_z: float = 0,
    camera_rotate_x: float = 55,
    camera_rotate_y: float = 0,
    camera_rotate_z: float = 25,
    camera_distance: float = 140,
    viewall: bool = True,
    colorscheme: str = "Cornfield",
) -> dict
```

### `multi_view_render`

```python
multi_view_render(
    scad_code: str,
    views: list[str] = ["isometric", "front", "top"],
    width: int = 640,
    height: int = 480,
    colorscheme: str = "Cornfield",
) -> dict
# views choices: front, back, left, right, top, bottom, isometric
```

### `validate_scad`

```python
validate_scad(scad_code: str) -> dict
# Returns: { valid: bool, warnings: list[str], errors: list[str] }
```

### `export_stl` / `export_3mf`

```python
export_stl(scad_code: str, output_path: str | None = None) -> dict
export_3mf(scad_code: str, output_path: str | None = None) -> dict
# If output_path is None, returns base64-encoded file content
```

### `export_scad_file`

```python
export_scad_file(
    scad_file_path: str,
    output_path: str | None = None,
    format: str = "stl",   # stl | 3mf | dxf | svg | off | amf | csg
) -> dict
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## License

MIT © [sjrhee](https://github.com/sjrhee)
