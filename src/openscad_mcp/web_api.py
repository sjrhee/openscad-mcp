"""FastAPI web server for OpenSCAD rendering."""

import asyncio
import tempfile
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask

from openscad_mcp.renderer import render_to_png, render_to_stl, validate

app = FastAPI(title="OpenSCAD Web API", version="0.2.0")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DIST_DIR = PROJECT_ROOT / "web" / "dist"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Quality presets: OpenSCAD variable overrides
QUALITY_3D: dict[str, object] = {"num_steps": 30, "$fn": 36}       # 3D View (STL preview)
QUALITY_PNG: dict[str, object] = {"num_steps": 100, "$fn": 60}      # PNG preview
QUALITY_EXPORT: dict[str, object] = {"num_steps": 100, "$fn": 90}   # STL download


class ValidateRequest(BaseModel):
    scad_file: str


class RenderPngRequest(BaseModel):
    scad_file: str
    width: int = 1024
    height: int = 768


class RenderStlRequest(BaseModel):
    scad_file: str
    quality: str = "preview"  # "preview" (fast) or "export" (high quality)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/files")
async def list_files():
    """List .scad files in the data/ directory."""
    if not DATA_DIR.is_dir():
        return {"files": []}
    files = sorted(
        [
            {"name": f.name, "path": str(f)}
            for f in DATA_DIR.glob("*.scad")
        ],
        key=lambda x: x["name"],
    )
    return {"files": files}


@app.get("/api/files/status")
async def files_status():
    """Return modification times for change detection polling."""
    if not DATA_DIR.is_dir():
        return {"files": {}}
    files = {}
    for f in DATA_DIR.glob("*.scad"):
        try:
            files[f.name] = f.stat().st_mtime
        except OSError:
            pass
    return {"files": files}


@app.post("/api/validate")
async def api_validate(req: ValidateRequest):
    result = await asyncio.to_thread(validate, req.scad_file)
    return {"success": result.success, "message": result.stderr}


@app.post("/api/render/png")
async def api_render_png(req: RenderPngRequest):
    result = await asyncio.to_thread(
        render_to_png, req.scad_file, None, req.width, req.height,
        overrides=QUALITY_PNG,
    )
    if not result.success or not result.output_path:
        raise HTTPException(status_code=400, detail=result.stderr)

    return FileResponse(
        result.output_path,
        media_type="image/png",
        background=BackgroundTask(
            lambda p=result.output_path: Path(p).unlink(missing_ok=True)
        ),
    )


@app.post("/api/render/stl")
async def api_render_stl(req: RenderStlRequest):
    overrides = QUALITY_EXPORT if req.quality == "export" else QUALITY_3D

    tmp = tempfile.NamedTemporaryFile(
        suffix=".stl", prefix="openscad_web_", delete=False
    )
    tmp_path = tmp.name
    tmp.close()

    result = await asyncio.to_thread(
        render_to_stl, req.scad_file, tmp_path, overrides=overrides
    )
    if not result.success or not result.output_path:
        Path(tmp_path).unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=result.stderr)

    filename = Path(req.scad_file).stem + ".stl"
    return FileResponse(
        result.output_path,
        media_type="application/octet-stream",
        filename=filename,
        background=BackgroundTask(
            lambda p=result.output_path: Path(p).unlink(missing_ok=True)
        ),
    )


# ---------------------------------------------------------------------------
# Static file serving (production: serves built React app)
# ---------------------------------------------------------------------------

if DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True))


def main():
    """Entry point for the web API server."""
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
