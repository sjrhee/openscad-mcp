"""MCP server for OpenSCAD 3D model rendering."""

import base64
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from openscad_mcp.renderer import render_to_png, render_to_stl, validate

mcp = FastMCP(
    "openscad-mcp",
    instructions=(
        "OpenSCAD 3D model rendering server. "
        "Use render_preview to see a PNG preview of .scad files. "
        "Use render_stl to export .scad files to STL for 3D printing. "
        "Use validate_scad to check .scad file syntax."
    ),
)


@mcp.tool()
def render_stl(scad_file: str, output_path: str = "") -> str:
    """Render an OpenSCAD .scad file to STL format for 3D printing.

    Args:
        scad_file: Absolute path to the .scad file.
        output_path: Optional output path for the .stl file.
                     Defaults to same location with .stl extension.
    """
    result = render_to_stl(scad_file, output_path if output_path else None)

    if result.success and result.output_path:
        size_kb = (result.file_size or 0) / 1024
        msg = f"STL exported successfully.\nPath: {result.output_path}\nSize: {size_kb:.1f} KB"
        if result.stderr:
            msg += f"\nWarnings:\n{result.stderr}"
        return msg

    return f"Rendering failed.\n{result.stderr}"


@mcp.tool()
def render_preview(scad_file: str, width: int = 1024, height: int = 768) -> list:
    """Render an OpenSCAD .scad file to a PNG preview image.

    Returns the rendered image directly so you can see the 3D model.

    Args:
        scad_file: Absolute path to the .scad file.
        width: Image width in pixels (default 1024).
        height: Image height in pixels (default 768).
    """
    result = render_to_png(scad_file, width=width, height=height)

    if result.success and result.output_path:
        png_path = Path(result.output_path)
        png_data = png_path.read_bytes()
        b64 = base64.standard_b64encode(png_data).decode("ascii")

        contents = [
            {"type": "image", "data": b64, "mimeType": "image/png"},
            {"type": "text", "text": f"Preview of: {scad_file}\nImage: {width}x{height}px"},
        ]

        # Clean up temp file
        try:
            png_path.unlink()
        except OSError:
            pass

        return contents

    return [{"type": "text", "text": f"Preview rendering failed.\n{result.stderr}"}]


@mcp.tool()
def validate_scad(scad_file: str) -> str:
    """Validate OpenSCAD .scad file syntax without producing output.

    Args:
        scad_file: Absolute path to the .scad file to validate.
    """
    result = validate(scad_file)

    if result.success:
        msg = "Syntax is valid."
        if result.stderr:
            warnings = [
                line for line in result.stderr.splitlines()
                if line.strip() and "WARNING" in line.upper()
            ]
            if warnings:
                msg += "\nWarnings:\n" + "\n".join(warnings)
        return msg

    return f"Syntax errors found:\n{result.stderr}"


def main():
    """Entry point for the MCP server."""
    print("Starting OpenSCAD MCP server...", file=sys.stderr)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
