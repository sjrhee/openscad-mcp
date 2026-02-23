"""OpenSCAD CLI wrapper for rendering .scad files to STL/PNG."""

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

OPENSCAD_EXE = os.environ.get(
    "OPENSCAD_PATH", r"C:\Program Files\OpenSCAD\openscad.exe"
)
RENDER_TIMEOUT = int(os.environ.get("OPENSCAD_TIMEOUT", "600"))


@dataclass
class RenderResult:
    success: bool
    output_path: str | None = None
    file_size: int | None = None
    stdout: str = ""
    stderr: str = ""


def _run_openscad(args: list[str], timeout: int = RENDER_TIMEOUT) -> RenderResult:
    """Run OpenSCAD CLI with the given arguments."""
    cmd = [OPENSCAD_EXE, *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        success = proc.returncode == 0
        return RenderResult(
            success=success,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    except FileNotFoundError:
        return RenderResult(
            success=False,
            stderr=f"OpenSCAD not found at: {OPENSCAD_EXE}",
        )
    except subprocess.TimeoutExpired:
        return RenderResult(
            success=False,
            stderr=f"Rendering timed out after {timeout} seconds",
        )


def _build_overrides(overrides: dict[str, object] | None) -> list[str]:
    """Convert a dict of variable overrides to OpenSCAD -D flags."""
    if not overrides:
        return []
    args = []
    for key, val in overrides.items():
        args.extend(["-D", f"{key}={val}"])
    return args


def render_to_stl(
    scad_file: str,
    output_path: str | None = None,
    overrides: dict[str, object] | None = None,
) -> RenderResult:
    """Render a .scad file to STL format.

    Args:
        scad_file: Path to the .scad input file.
        output_path: Path for the output .stl file.
                     Defaults to same directory with .stl extension.
        overrides: Optional dict of OpenSCAD variable overrides (e.g. {"$fn": 90}).
    """
    scad_path = Path(scad_file).resolve()
    if not scad_path.exists():
        return RenderResult(success=False, stderr=f"File not found: {scad_file}")

    if output_path is None:
        output_path = str(scad_path.with_suffix(".stl"))

    result = _run_openscad([*_build_overrides(overrides), "-o", output_path, str(scad_path)])

    out = Path(output_path)
    if out.exists():
        result.output_path = str(out)
        result.file_size = out.stat().st_size

    return result


def render_to_png(
    scad_file: str,
    output_path: str | None = None,
    width: int = 1024,
    height: int = 768,
    overrides: dict[str, object] | None = None,
) -> RenderResult:
    """Render a .scad file to PNG preview image.

    Args:
        scad_file: Path to the .scad input file.
        output_path: Path for the output .png file.
                     Defaults to a temp file.
        width: Image width in pixels.
        height: Image height in pixels.
        overrides: Optional dict of OpenSCAD variable overrides.
    """
    scad_path = Path(scad_file).resolve()
    if not scad_path.exists():
        return RenderResult(success=False, stderr=f"File not found: {scad_file}")

    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".png", prefix="openscad_preview_", delete=False
        )
        output_path = tmp.name
        tmp.close()

    result = _run_openscad([
        *_build_overrides(overrides),
        "--autocenter",
        "--viewall",
        f"--imgsize={width},{height}",
        "-o", output_path,
        str(scad_path),
    ])

    out = Path(output_path)
    if out.exists() and out.stat().st_size > 0:
        result.output_path = str(out)
        result.file_size = out.stat().st_size

    return result


def validate(scad_file: str) -> RenderResult:
    """Validate OpenSCAD file syntax.

    Attempts a dry render to /dev/null (NUL on Windows) to check for errors.
    """
    scad_path = Path(scad_file).resolve()
    if not scad_path.exists():
        return RenderResult(success=False, stderr=f"File not found: {scad_file}")

    # Render to a temp STL but with very fast settings just to check syntax
    tmp = tempfile.NamedTemporaryFile(
        suffix=".stl", prefix="openscad_validate_", delete=False
    )
    tmp_path = tmp.name
    tmp.close()

    try:
        result = _run_openscad(["-o", tmp_path, str(scad_path)], timeout=30)
        return result
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
