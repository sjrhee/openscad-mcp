"""FastAPI web server for OpenSCAD rendering."""

import asyncio
import os
import re as _re
import tempfile
import time as _time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import anthropic
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from openscad_mcp.renderer import render_to_png, render_to_stl, validate
from openscad_mcp.design_agent import (
    render_preview,
    image_to_base64,
    call_claude,
    parse_evaluation,
    apply_code,
    generate_initial_code,
    SYSTEM_PROMPT,
    DEFAULT_MODEL,
    PROJECT_ROOT,
)

app = FastAPI(title="OpenSCAD Web API", version="0.1.0")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

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
# Design Agent — session management & endpoints
# ---------------------------------------------------------------------------

_SESSION_TTL = 1800  # 30 minutes
_anthropic_client: anthropic.Anthropic | None = None


def _get_anthropic_client() -> anthropic.Anthropic:
    """Lazy singleton for the Anthropic client."""
    global _anthropic_client
    if _anthropic_client is not None:
        return _anthropic_client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "ANTHROPIC_API_KEY":
                    api_key = v.strip()
                    break
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


@dataclass
class AgentSession:
    session_id: str
    scad_path: str
    current_code: str
    mode: str
    description: str
    messages: list = field(default_factory=list)
    history: list = field(default_factory=list)
    model: str = DEFAULT_MODEL
    target_score: int = 8
    max_iterations: int = 5
    pending_code: str | None = None
    created_at: float = 0


_sessions: dict[str, AgentSession] = {}


def _cleanup_old_sessions():
    now = _time.time()
    expired = [sid for sid, s in _sessions.items() if now - s.created_at > _SESSION_TTL]
    for sid in expired:
        del _sessions[sid]


def _slugify(text: str) -> str:
    return _re.sub(r"[^a-z0-9]+", text.lower(), "_").strip("_")[:40]


class AgentStartRequest(BaseModel):
    scad_file: str = ""
    mode: str = "review"
    description: str = ""
    output_name: str | None = None
    model: str = DEFAULT_MODEL
    target_score: int = 8
    max_iterations: int = 5


class AgentEvaluateRequest(BaseModel):
    session_id: str
    feedback: str | None = None


class AgentApplyRequest(BaseModel):
    session_id: str


class AgentStopRequest(BaseModel):
    session_id: str


@app.post("/api/agent/start")
async def agent_start(req: AgentStartRequest):
    _cleanup_old_sessions()
    client = _get_anthropic_client()

    if req.mode == "generate":
        if not req.description.strip():
            raise HTTPException(400, "description required for generate mode")
        slug = _re.sub(r"[^a-z0-9]+", "_", req.description.lower()).strip("_")[:40]
        if not slug:
            slug = f"design_{uuid.uuid4().hex[:8]}"
        scad_name = req.output_name or slug + ".scad"
        scad_path = str(DATA_DIR / scad_name)
        code = await asyncio.to_thread(generate_initial_code, client, req.description, req.model)
        success = await asyncio.to_thread(apply_code, scad_path, code)
        if not success:
            raise HTTPException(400, "Generated code failed validation")
        description = req.description
    else:
        scad_path = req.scad_file
        if not Path(scad_path).exists():
            raise HTTPException(404, f"File not found: {scad_path}")
        code = Path(scad_path).read_text(encoding="utf-8")
        description = f"Review of {Path(scad_path).name}"

    sid = str(uuid.uuid4())
    _sessions[sid] = AgentSession(
        session_id=sid,
        scad_path=scad_path,
        current_code=code,
        mode=req.mode,
        description=description,
        model=req.model,
        target_score=req.target_score,
        max_iterations=req.max_iterations,
        created_at=_time.time(),
    )
    return {"session_id": sid, "scad_file": scad_path, "mode": req.mode}


@app.post("/api/agent/evaluate")
async def agent_evaluate(req: AgentEvaluateRequest):
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    iteration = len(session.history) + 1
    if iteration > session.max_iterations:
        raise HTTPException(400, "Max iterations reached")

    client = _get_anthropic_client()

    # Step 1: Render preview PNG
    png_path = await asyncio.to_thread(render_preview, session.scad_path)
    if png_path is None:
        raise HTTPException(500, "Render failed")

    b64 = image_to_base64(png_path)
    png_path.unlink(missing_ok=True)

    # Step 2: Build user message
    if iteration == 1:
        if session.mode == "generate":
            text = (
                f'I generated this OpenSCAD design based on: "{session.description}". '
                "Evaluate how well the rendered image matches. "
                "Suggest improvements to geometry, proportions, detail, and code quality."
            )
        else:
            text = (
                "Review this OpenSCAD design. Evaluate the rendered image and code. "
                "Suggest improvements for realism, proportions, and best practices."
            )
    else:
        text = f"Iteration {iteration}: updated render and code after previous suggestions."

    if req.feedback:
        text += f"\n\nUser feedback: {req.feedback}"

    user_content = [
        {"type": "text", "text": text},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
        {"type": "text", "text": f"Current .scad code:\n```openscad\n{session.current_code}\n```"},
    ]
    session.messages.append({"role": "user", "content": user_content})

    # Step 3: Call Claude
    response = await asyncio.to_thread(
        call_claude, client, SYSTEM_PROMPT, session.messages, session.model
    )
    response_text = response.content[0].text
    eval_result = parse_evaluation(response_text)

    session.messages.append({"role": "assistant", "content": response_text})
    session.pending_code = eval_result.suggested_code

    record = {
        "iteration": iteration,
        "score": eval_result.score,
        "summary": eval_result.summary,
        "issues": eval_result.issues,
    }
    session.history.append(record)

    # Check convergence
    converged = False
    converge_reason = None
    if eval_result.score >= session.target_score and not eval_result.suggested_code:
        converged = True
        converge_reason = "target_reached"
    elif eval_result.stop_reason == "no_improvement":
        converged = True
        converge_reason = "no_improvement"
    elif len(session.history) >= 3:
        scores = [h["score"] for h in session.history[-3:]]
        if scores[2] <= scores[1] <= scores[0]:
            converged = True
            converge_reason = "stagnant"

    return {
        "session_id": session.session_id,
        "iteration": iteration,
        "score": eval_result.score,
        "summary": eval_result.summary,
        "criteria_scores": eval_result.criteria_scores,
        "issues": eval_result.issues,
        "has_suggested_code": eval_result.suggested_code is not None,
        "preview_base64": b64,
        "converged": converged,
        "converge_reason": converge_reason,
        "history": session.history,
    }


@app.post("/api/agent/apply")
async def agent_apply(req: AgentApplyRequest):
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    code = session.pending_code
    if not code:
        raise HTTPException(400, "No suggested code to apply")

    success = await asyncio.to_thread(apply_code, session.scad_path, code)
    if not success:
        raise HTTPException(400, "Code validation failed; changes not applied")

    session.current_code = code
    session.pending_code = None
    return {"success": True, "message": "Code applied and validated"}


@app.post("/api/agent/stop")
async def agent_stop(req: AgentStopRequest):
    session = _sessions.pop(req.session_id, None)
    if not session:
        raise HTTPException(404, "Session not found")
    return {"success": True, "history": session.history}


def main():
    """Entry point for the web API server."""
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
