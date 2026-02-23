"""Tests for openscad_mcp.server — skips gracefully when OpenSCAD is absent."""

from __future__ import annotations

import pytest

from openscad_mcp.server import (
    check_openscad,
    export_3mf,
    export_scad_file,
    export_stl,
    multi_view_render,
    render_scad,
    render_scad_file,
    validate_scad,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SIMPLE_CUBE = """
// A simple test cube
module test_cube(size=10) {
    cube([size, size, size], center=true);
}
test_cube(20);
"""

SYNTAX_ERROR = """
// Missing closing brace
module broken(  {
    cube(10);
"""


def _openscad_available() -> bool:
    result = check_openscad()
    return result.get("installed", False)


skip_if_no_openscad = pytest.mark.skipif(
    not _openscad_available(),
    reason="OpenSCAD is not installed on this system",
)


# ---------------------------------------------------------------------------
# check_openscad
# ---------------------------------------------------------------------------

def test_check_openscad_returns_dict() -> None:
    result = check_openscad()
    assert isinstance(result, dict)
    assert "installed" in result


def test_check_openscad_has_version_when_installed() -> None:
    result = check_openscad()
    if result["installed"]:
        assert "version" in result
        assert "binary_path" in result


# ---------------------------------------------------------------------------
# render_scad
# ---------------------------------------------------------------------------

@skip_if_no_openscad
def test_render_scad_success() -> None:
    result = render_scad(SIMPLE_CUBE, width=320, height=240)
    assert result["success"] is True
    assert "image_base64" in result
    assert result["image_base64"].startswith("data:image/png;base64,")


@skip_if_no_openscad
def test_render_scad_invalid_code() -> None:
    result = render_scad("invalid { scad code !!!", width=320, height=240)
    assert result["success"] is False
    assert "error" in result


# ---------------------------------------------------------------------------
# multi_view_render
# ---------------------------------------------------------------------------

@skip_if_no_openscad
def test_multi_view_render_default_views() -> None:
    result = multi_view_render(SIMPLE_CUBE, width=320, height=240)
    assert result["success"] is True
    assert "views" in result
    for view_name in ["isometric", "front", "top"]:
        assert view_name in result["views"]
        assert result["views"][view_name].startswith("data:image/png;base64,")


@skip_if_no_openscad
def test_multi_view_render_custom_views() -> None:
    result = multi_view_render(SIMPLE_CUBE, views=["front", "left"], width=320, height=240)
    assert result["success"] is True
    assert set(result["views"].keys()) == {"front", "left"}


def test_multi_view_render_invalid_view() -> None:
    result = multi_view_render(SIMPLE_CUBE, views=["nonexistent_view"])
    assert result["success"] is False
    assert "error" in result


# ---------------------------------------------------------------------------
# validate_scad
# ---------------------------------------------------------------------------

@skip_if_no_openscad
def test_validate_scad_valid_code() -> None:
    result = validate_scad(SIMPLE_CUBE)
    assert result["valid"] is True
    assert isinstance(result["warnings"], list)
    assert isinstance(result["errors"], list)


@skip_if_no_openscad
def test_validate_scad_invalid_code() -> None:
    result = validate_scad(SYNTAX_ERROR)
    assert result["valid"] is False
    assert len(result["errors"]) > 0


# ---------------------------------------------------------------------------
# export_stl
# ---------------------------------------------------------------------------

@skip_if_no_openscad
def test_export_stl_returns_base64_when_no_path() -> None:
    result = export_stl(SIMPLE_CUBE)
    assert result["success"] is True
    assert "stl_base64" in result
    # STL binary header starts with "solid" or binary bytes
    import base64
    stl_bytes = base64.b64decode(result["stl_base64"])
    assert len(stl_bytes) > 0


@skip_if_no_openscad
def test_export_stl_to_file(tmp_path) -> None:
    out = str(tmp_path / "test.stl")
    result = export_stl(SIMPLE_CUBE, output_path=out)
    assert result["success"] is True
    assert result["output_path"] == out
    from pathlib import Path
    assert Path(out).exists()


# ---------------------------------------------------------------------------
# export_3mf
# ---------------------------------------------------------------------------

@skip_if_no_openscad
def test_export_3mf_returns_base64_when_no_path() -> None:
    result = export_3mf(SIMPLE_CUBE)
    assert result["success"] is True
    assert "file_base64" in result


# ---------------------------------------------------------------------------
# render_scad_file / export_scad_file
# ---------------------------------------------------------------------------

@skip_if_no_openscad
def test_render_scad_file(tmp_path) -> None:
    scad_file = tmp_path / "test.scad"
    scad_file.write_text(SIMPLE_CUBE, encoding="utf-8")
    result = render_scad_file(str(scad_file), width=320, height=240)
    assert result["success"] is True
    assert result["image_base64"].startswith("data:image/png;base64,")


def test_render_scad_file_not_found() -> None:
    result = render_scad_file("/nonexistent/path/model.scad")
    assert result["success"] is False
    assert "not found" in result["error"].lower()


@skip_if_no_openscad
def test_export_scad_file_stl(tmp_path) -> None:
    scad_file = tmp_path / "test.scad"
    scad_file.write_text(SIMPLE_CUBE, encoding="utf-8")
    result = export_scad_file(str(scad_file), format="stl")
    assert result["success"] is True
    from pathlib import Path
    assert Path(result["output_path"]).exists()


def test_export_scad_file_invalid_format(tmp_path) -> None:
    scad_file = tmp_path / "test.scad"
    scad_file.write_text(SIMPLE_CUBE, encoding="utf-8")
    result = export_scad_file(str(scad_file), format="xyz")
    assert result["success"] is False
    assert "Invalid format" in result["error"]
