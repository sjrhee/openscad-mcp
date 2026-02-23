# openscad-mcp

OpenSCAD 3D 모델을 생성·렌더링하고 웹 브라우저에서 인터랙티브하게 미리보기할 수 있는 도구.

![Preview](data/50_to_100_transition_pipe_preview.png)

---

## 주요 기능

- `.scad` 파일을 받아 **PNG 미리보기** 또는 **STL** 로 렌더링
- **Three.js 기반 3D 웹 뷰어** — 드래그 회전, 스크롤 줌
- 품질 프리셋 — 빠른 웹 미리보기 / 고품질 STL 출력 분리
- FastAPI REST API로 외부 연동 가능
- MCP(Model Context Protocol) 서버 내장

---

## 구조

```
openscad-mcp/
├── data/              # .scad 소스 및 렌더링 결과 (PNG, STL)
├── src/openscad_mcp/
│   ├── renderer.py    # OpenSCAD CLI 래퍼
│   ├── web_api.py     # FastAPI 서버 (port 8000)
│   └── server.py      # MCP 서버
└── web/               # Vite + React 프론트엔드 (port 3000)
    └── src/
        ├── App.jsx
        └── StlViewer.jsx
```

---

## 요구사항

| 항목 | 버전 |
|------|------|
| [OpenSCAD](https://openscad.org/downloads.html) | 2021.01+ |
| Python | 3.10+ |
| Node.js | 18+ |

> Windows 기본 설치 경로: `C:\Program Files\OpenSCAD\openscad.exe`
> 다른 경로인 경우 환경 변수 `OPENSCAD_PATH` 로 지정

---

## 설치

```bash
# 1. 저장소 클론
git clone https://github.com/YOUR_USERNAME/openscad-mcp.git
cd openscad-mcp

# 2. Python 가상환경 생성 및 백엔드 설치
python -m venv .venv
.venv/Scripts/pip install -e .      # Windows
# source .venv/bin/activate && pip install -e .  # macOS/Linux

# 3. 프론트엔드 의존성 설치
cd web && npm install && cd ..
```

---

## 실행

```bash
# 백엔드 (port 8000)
.venv/Scripts/python -m openscad_mcp.web_api

# 프론트엔드 (port 3000) — 별도 터미널
cd web && npm run dev
```

브라우저에서 `http://localhost:3000` 접속

---

## 사용법

1. 입력란에 `.scad` 파일 절대 경로 입력
2. **3D View** — Three.js 인터랙티브 뷰어로 확인
3. **Preview PNG** — 정적 PNG 렌더링
4. **Validate** — 문법 검사
5. **Download STL** — 고품질 STL 출력

---

## 렌더링 품질 프리셋

| 용도 | num_steps | $fn | 소요 시간 |
|------|-----------|-----|-----------|
| 3D View (웹) | 30 | 36 | ~5초 |
| Preview PNG | 50 | 60 | ~20초 |
| Download STL | 100 | 90 | ~1~2분 |

---

## REST API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/health` | 서버 상태 확인 |
| POST | `/api/validate` | .scad 문법 검사 |
| POST | `/api/render/png` | PNG 렌더링 |
| POST | `/api/render/stl` | STL 렌더링 (`quality`: `preview` / `export`) |

**예시**
```bash
curl -X POST http://localhost:8000/api/render/stl \
  -H "Content-Type: application/json" \
  -d '{"scad_file": "/path/to/model.scad", "quality": "export"}' \
  --output model.stl
```

---

## 디자인 예시

| 파일 | 설명 |
|------|------|
| `circle_to_ellipse_transition_pipe.scad` | 원형 Ø50mm → 평타원 80×10mm, 길이 150mm |
| `50_to_100_transition_pipe.scad` | 원형 Ø55mm → 원형 Ø100mm, 양끝 10mm 평탄, 길이 150mm |

---

## MCP 서버 연동

`stdio` 기반 MCP 서버로, MCP를 지원하는 모든 AI 클라이언트에서 사용 가능합니다.

### 지원 도구

| 도구 | 설명 |
|------|------|
| `render_preview` | `.scad` → PNG 렌더링 후 대화창에 이미지로 표시 |
| `render_stl` | `.scad` → STL 파일 생성 |
| `validate_scad` | `.scad` 문법 검사 |

---

### Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "openscad": {
      "command": "D:/Work/openscad-mcp/.venv/Scripts/python",
      "args": ["-m", "openscad_mcp.server"]
    }
  }
}
```

**명령 예시**
```
50mm에서 100mm로 전환되는 길이 150mm 파이프를 만들고 미리보기 보여줘
data/my_pipe.scad 파일을 STL로 내보내줘
data/model.scad 문법 검사해줘
```

---

### OpenAI Codex CLI

`~/.codex/config.toml`

```toml
[mcp_servers.openscad]
command = "D:/Work/openscad-mcp/.venv/Scripts/python"
args = ["-m", "openscad_mcp.server"]
cwd = "D:/Work/openscad-mcp"
```

**명령 예시**
```
Create a pipe transitioning from 50mm to 100mm diameter, 150mm long, and preview it
Export data/my_pipe.scad to STL
```

---

### Cursor / VS Code / Windsurf

`.cursor/mcp.json` 또는 `.vscode/mcp.json`

```json
{
  "mcpServers": {
    "openscad": {
      "command": "D:/Work/openscad-mcp/.venv/Scripts/python",
      "args": ["-m", "openscad_mcp.server"]
    }
  }
}
```

> macOS/Linux는 `command`를 `D:/Work/openscad-mcp/.venv/bin/python` 으로 변경

---

## 라이선스

MIT
