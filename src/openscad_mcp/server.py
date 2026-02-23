"""
OpenSCAD MCP Server
===================
A Model Context Protocol (MCP) server that enables AI assistants to
generate, render, and export 3D models using OpenSCAD.

Tools provided:
  - check_openscad       : Check OpenSCAD installation & version
  - render_scad          : Render OpenSCAD code to a PNG image
  - multi_view_render    : Render multiple standard views (front/back/left/right/top/isometric)
  - export_stl           : Export OpenSCAD code to an STL file
  - export_3mf           : Export OpenSCAD code to a 3MF file
  - validate_scad        : Validate OpenSCAD syntax (dry-run)
  - render_scad_file     : Render an existing .scad file to PNG
  - export_scad_file     : Export an existing .scad file to STL/3MF/DXF/SVG
"""

from __future__ import annotations

import base64
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openscad-mcp")

# ---------------------------------------------------------------------------
# FastMCP app
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "openscad-mcp",
    instructions="MCP server for OpenSCAD 3D modeling, rendering, and export",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_openscad_binary() -> str:
    """Return the OpenSCAD binary path from env or PATH lookup."""
    binary = os.environ.get("OPENSCAD_BINARY", "")
    if binary and Path(binary).is_file():
        return binary
    found = shutil.which("openscad") or shutil.which("OpenSCAD")
    if found:
        return found
    raise FileNotFoundError(
        "OpenSCAD binary not found. Install OpenSCAD and ensure it is in PATH, "
        "or set the OPENSCAD_BINARY environment variable."
    )


def _run_openscad(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    """Run OpenSCAD with the given arguments."""
    binary = _get_openscad_binary()
    cmd = [binary] + args
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result


def _encode_image(path: str) -> str:
    """Read a PNG file and return a base64-encoded data URI."""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{data}"


def _camera_args(
    camera_translate: tuple[float, float, float] | None = None,
    camera_rotate: tuple[float, float, float] | None = None,
    camera_distance: float | None = None,
    viewall: bool = False,
) -> list[str]:
    """Build --camera argument list for OpenSCAD CLI."""
    args: list[str] = []
    if viewall:
        args += ["--viewall"]
    if camera_translate and camera_rotate and camera_distance is not None:
        tx, ty, tz = camera_translate
        rx, ry, rz = camera_rotate
        args += [
            "--camera",
            f"{tx},{ty},{tz},{rx},{ry},{rz},{camera_distance}",
        ]
    elif camera_translate or camera_rotate or camera_distance is not None:
        # Partial camera spec — fill defaults
        tx, ty, tz = camera_translate or (0, 0, 0)
        rx, ry, rz = camera_rotate or (55, 0, 25)
        dist = camera_distance if camera_distance is not None else 140
        args += ["--camera", f"{tx},{ty},{tz},{rx},{ry},{rz},{dist}"]
    return args


# Standard named views as (translate, rotate, distance)
_NAMED_VIEWS: dict[str, tuple[tuple[float, float, float], tuple[float, float, float], float]] = {
    "front":      ((0, 0, 0), (0, 0, 0),   140),
    "back":       ((0, 0, 0), (0, 0, 180), 140),
    "left":       ((0, 0, 0), (0, 0, 90),  140),
    "right":      ((0, 0, 0), (0, 0, -90), 140),
    "top":        ((0, 0, 0), (90, 0, 0),  140),
    "bottom":     ((0, 0, 0), (-90, 0, 0), 140),
    "isometric":  ((0, 0, 0), (55, 0, 25), 140),
}


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def check_openscad() -> dict[str, Any]:
    """
    Check whether OpenSCAD is installed and return its version.

    Returns a dict with:
      - installed (bool)
      - binary_path (str)
      - version (str)
      - error (str, only on failure)
    """
    try:
        binary = _get_openscad_binary()
        result = _run_openscad(["--version"], timeout=10)
        version_str = (result.stdout + result.stderr).strip()
        return {
            "installed": True,
            "binary_path": binary,
            "version": version_str,
        }
    except FileNotFoundError as exc:
        return {"installed": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"installed": False, "error": str(exc)}


@mcp.tool()
def render_scad(
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
) -> dict[str, Any]:
    """
    Render OpenSCAD code to a PNG image.

    Args:
        scad_code: The OpenSCAD source code to render.
        width: Image width in pixels (default 800).
        height: Image height in pixels (default 600).
        camera_translate_x/y/z: Camera translation vector.
        camera_rotate_x/y/z: Camera rotation angles (degrees).
        camera_distance: Distance from camera to origin.
        viewall: Automatically fit the model in view (default True).
        colorscheme: OpenSCAD color scheme name (default "Cornfield").

    Returns a dict with:
      - success (bool)
      - image_base64 (str): data URI of the rendered PNG
      - width, height (int)
      - error (str, only on failure)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        scad_path = Path(tmpdir) / "model.scad"
        png_path = Path(tmpdir) / "render.png"

        scad_path.write_text(scad_code, encoding="utf-8")

        cam_args = _camera_args(
            camera_translate=(camera_translate_x, camera_translate_y, camera_translate_z),
            camera_rotate=(camera_rotate_x, camera_rotate_y, camera_rotate_z),
            camera_distance=camera_distance,
            viewall=viewall,
        )

        args = [
            "--render",
            "--imgsize", f"{width},{height}",
            "--colorscheme", colorscheme,
            *cam_args,
            "-o", str(png_path),
            str(scad_path),
        ]

        try:
            result = _run_openscad(args)
        except FileNotFoundError as exc:
            return {"success": False, "error": str(exc)}

        if result.returncode != 0 or not png_path.exists():
            return {
                "success": False,
                "error": result.stderr or "OpenSCAD returned a non-zero exit code",
            }

        return {
            "success": True,
            "image_base64": _encode_image(str(png_path)),
            "width": width,
            "height": height,
        }


@mcp.tool()
def multi_view_render(
    scad_code: str,
    views: list[str] | None = None,
    width: int = 640,
    height: int = 480,
    colorscheme: str = "Cornfield",
) -> dict[str, Any]:
    """
    Render multiple standard views of an OpenSCAD model.

    Args:
        scad_code: The OpenSCAD source code to render.
        views: List of view names to render. Choices: front, back, left, right,
               top, bottom, isometric. Defaults to ["isometric", "front", "top"].
        width: Image width in pixels (default 640).
        height: Image height in pixels (default 480).
        colorscheme: OpenSCAD color scheme name (default "Cornfield").

    Returns a dict with:
      - success (bool)
      - views (dict[str, str]): mapping of view name -> base64 PNG data URI
      - errors (dict[str, str]): any per-view errors
    """
    if views is None:
        views = ["isometric", "front", "top"]

    invalid = [v for v in views if v not in _NAMED_VIEWS]
    if invalid:
        return {
            "success": False,
            "error": f"Unknown views: {invalid}. Valid: {list(_NAMED_VIEWS.keys())}",
        }

    results: dict[str, str] = {}
    errors: dict[str, str] = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        scad_path = Path(tmpdir) / "model.scad"
        scad_path.write_text(scad_code, encoding="utf-8")

        for view_name in views:
            translate, rotate, distance = _NAMED_VIEWS[view_name]
            png_path = Path(tmpdir) / f"{view_name}.png"
            cam_args = _camera_args(
                camera_translate=translate,
                camera_rotate=rotate,
                camera_distance=distance,
            )
            args = [
                "--render",
                "--imgsize", f"{width},{height}",
                "--colorscheme", colorscheme,
                *cam_args,
                "-o", str(png_path),
                str(scad_path),
            ]
            try:
                result = _run_openscad(args)
                if result.returncode != 0 or not png_path.exists():
                    errors[view_name] = result.stderr or "Render failed"
                else:
                    results[view_name] = _encode_image(str(png_path))
            except FileNotFoundError as exc:
                return {"success": False, "error": str(exc)}
            except Exception as exc:  # noqa: BLE001
                errors[view_name] = str(exc)

    return {
        "success": len(results) > 0,
        "views": results,
        "errors": errors,
    }


@mcp.tool()
def export_stl(
    scad_code: str,
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Export OpenSCAD code to an STL file.

    Args:
        scad_code: The OpenSCAD source code to export.
        output_path: Destination path for the STL file. If not provided,
                     a temporary path is used and the content is returned as base64.

    Returns a dict with:
      - success (bool)
      - output_path (str): final path of the STL file
      - stl_base64 (str, optional): base64-encoded STL if no output_path given
      - error (str, only on failure)
    """
    use_temp = output_path is None
    with tempfile.TemporaryDirectory() as tmpdir:
        scad_path = Path(tmpdir) / "model.scad"
        stl_path = Path(output_path) if output_path else Path(tmpdir) / "model.stl"

        scad_path.write_text(scad_code, encoding="utf-8")
        stl_path.parent.mkdir(parents=True, exist_ok=True)

        args = ["-o", str(stl_path), str(scad_path)]
        try:
            result = _run_openscad(args, timeout=300)
        except FileNotFoundError as exc:
            return {"success": False, "error": str(exc)}

        if result.returncode != 0 or not stl_path.exists():
            return {
                "success": False,
                "error": result.stderr or "Export failed",
            }

        response: dict[str, Any] = {
            "success": True,
            "output_path": str(stl_path),
        }
        if use_temp:
            with open(stl_path, "rb") as f:
                response["stl_base64"] = base64.b64encode(f.read()).decode("utf-8")
        return response


@mcp.tool()
def export_3mf(
    scad_code: str,
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Export OpenSCAD code to a 3MF file (preserves parametric info).

    Args:
        scad_code: The OpenSCAD source code to export.
        output_path: Destination path for the 3MF file. If not provided,
                     content is returned as base64.

    Returns a dict with:
      - success (bool)
      - output_path (str)
      - file_base64 (str, optional)
      - error (str, only on failure)
    """
    use_temp = output_path is None
    with tempfile.TemporaryDirectory() as tmpdir:
        scad_path = Path(tmpdir) / "model.scad"
        threemf_path = Path(output_path) if output_path else Path(tmpdir) / "model.3mf"

        scad_path.write_text(scad_code, encoding="utf-8")
        threemf_path.parent.mkdir(parents=True, exist_ok=True)

        args = ["-o", str(threemf_path), str(scad_path)]
        try:
            result = _run_openscad(args, timeout=300)
        except FileNotFoundError as exc:
            return {"success": False, "error": str(exc)}

        if result.returncode != 0 or not threemf_path.exists():
            return {
                "success": False,
                "error": result.stderr or "Export failed",
            }

        response: dict[str, Any] = {
            "success": True,
            "output_path": str(threemf_path),
        }
        if use_temp:
            with open(threemf_path, "rb") as f:
                response["file_base64"] = base64.b64encode(f.read()).decode("utf-8")
        return response


@mcp.tool()
def validate_scad(scad_code: str) -> dict[str, Any]:
    """
    Validate OpenSCAD code syntax without rendering.

    Performs a dry-run parse of the provided source code and reports
    any syntax errors.

    Args:
        scad_code: The OpenSCAD source code to validate.

    Returns a dict with:
      - valid (bool)
      - warnings (list[str])
      - errors (list[str])
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        scad_path = Path(tmpdir) / "model.scad"
        # Use a non-existent output to force syntax-only check
        null_out = Path(tmpdir) / "null.echo"

        scad_path.write_text(scad_code, encoding="utf-8")
        args = ["-o", str(null_out), "--export-format", "echo", str(scad_path)]

        try:
            result = _run_openscad(args, timeout=30)
        except FileNotFoundError as exc:
            return {"valid": False, "warnings": [], "errors": [str(exc)]}

        # OpenSCAD on Windows writes errors to the echo output file instead of stderr
        all_output = result.stderr
        if null_out.exists():
            try:
                all_output += null_out.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass

        output_lines = all_output.splitlines()
        warnings = [l for l in output_lines if "WARNING" in l.upper()]
        errors = [l for l in output_lines if "ERROR" in l.upper()]
        is_valid = result.returncode == 0 and not errors

        return {
            "valid": is_valid,
            "warnings": warnings,
            "errors": errors,
        }


@mcp.tool()
def render_scad_file(
    scad_file_path: str,
    output_png_path: str | None = None,
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
) -> dict[str, Any]:
    """
    Render an existing .scad file to a PNG image.

    Args:
        scad_file_path: Path to an existing .scad file.
        output_png_path: Where to save the PNG. Defaults to same dir as .scad.
        width: Image width in pixels.
        height: Image height in pixels.
        camera_translate_x/y/z: Camera translation.
        camera_rotate_x/y/z: Camera rotation angles.
        camera_distance: Camera distance.
        viewall: Auto-fit model in view.
        colorscheme: OpenSCAD color scheme.

    Returns a dict with:
      - success (bool)
      - output_path (str)
      - image_base64 (str): base64 PNG data URI
      - error (str, only on failure)
    """
    scad_path = Path(scad_file_path)
    if not scad_path.exists():
        return {"success": False, "error": f"File not found: {scad_file_path}"}

    if output_png_path:
        png_path = Path(output_png_path)
    else:
        png_path = scad_path.with_suffix(".png")

    png_path.parent.mkdir(parents=True, exist_ok=True)

    cam_args = _camera_args(
        camera_translate=(camera_translate_x, camera_translate_y, camera_translate_z),
        camera_rotate=(camera_rotate_x, camera_rotate_y, camera_rotate_z),
        camera_distance=camera_distance,
        viewall=viewall,
    )
    args = [
        "--render",
        "--imgsize", f"{width},{height}",
        "--colorscheme", colorscheme,
        *cam_args,
        "-o", str(png_path),
        str(scad_path),
    ]

    try:
        result = _run_openscad(args)
    except FileNotFoundError as exc:
        return {"success": False, "error": str(exc)}

    if result.returncode != 0 or not png_path.exists():
        return {"success": False, "error": result.stderr or "Render failed"}

    return {
        "success": True,
        "output_path": str(png_path),
        "image_base64": _encode_image(str(png_path)),
    }


@mcp.tool()
def export_scad_file(
    scad_file_path: str,
    output_path: str | None = None,
    format: str = "stl",
) -> dict[str, Any]:
    """
    Export an existing .scad file to STL, 3MF, DXF, or SVG.

    Args:
        scad_file_path: Path to an existing .scad file.
        output_path: Destination file path. Defaults to same dir as .scad.
        format: Export format. One of: stl, 3mf, dxf, svg, off, amf, csg.

    Returns a dict with:
      - success (bool)
      - output_path (str)
      - error (str, only on failure)
    """
    valid_formats = {"stl", "3mf", "dxf", "svg", "off", "amf", "csg"}
    if format.lower() not in valid_formats:
        return {
            "success": False,
            "error": f"Invalid format '{format}'. Valid: {sorted(valid_formats)}",
        }

    scad_path = Path(scad_file_path)
    if not scad_path.exists():
        return {"success": False, "error": f"File not found: {scad_file_path}"}

    out_path = Path(output_path) if output_path else scad_path.with_suffix(f".{format.lower()}")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    args = ["-o", str(out_path), str(scad_path)]
    try:
        result = _run_openscad(args, timeout=300)
    except FileNotFoundError as exc:
        return {"success": False, "error": str(exc)}

    if result.returncode != 0 or not out_path.exists():
        return {"success": False, "error": result.stderr or "Export failed"}

    return {"success": True, "output_path": str(out_path)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the OpenSCAD MCP server (stdio transport)."""
    import argparse

    parser = argparse.ArgumentParser(description="OpenSCAD MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="SSE host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="SSE port (default: 8000)"
    )
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
