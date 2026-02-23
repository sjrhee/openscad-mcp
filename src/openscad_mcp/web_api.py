"""FastAPI web server for OpenSCAD rendering."""

import asyncio
import tempfile
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from openscad_mcp.renderer import render_to_png, render_to_stl, validate

app = FastAPI(title="OpenSCAD Web API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Quality presets: OpenSCAD variable overrides
QUALITY_PREVIEW = {"num_steps": 30, "$fn": 36}
QUALITY_EXPORT = {"num_steps": 100, "$fn": 90}


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


@app.post("/api/validate")
async def api_validate(req: ValidateRequest):
    result = await asyncio.to_thread(validate, req.scad_file)
    return {"success": result.success, "message": result.stderr}


@app.post("/api/render/png")
async def api_render_png(req: RenderPngRequest):
    result = await asyncio.to_thread(
        render_to_png, req.scad_file, None, req.width, req.height,
        overrides=QUALITY_PREVIEW,
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
    overrides = QUALITY_EXPORT if req.quality == "export" else QUALITY_PREVIEW

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


def main():
    """Entry point for the web API server."""
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
