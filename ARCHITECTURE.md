# OpenSCAD MCP — 아키텍처 및 데이터 흐름

## 시스템 개요

```
┌─────────────────────────────────────────────────────────┐
│                        사용자                            │
│      브라우저 (localhost:8000)  /  터미널 CLI             │
└──────────┬──────────────────────────────┬───────────────┘
           │ HTTP                          │ stdin/stdout
           ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│   FastAPI Server    │         │   MCP Server        │
│   port 8000         │         │   stdio transport    │
│                     │         │                     │
│  web_api.py         │         │ server.py           │
│  ├── /api/*  (REST) │         │ 3개 tool 노출       │
│  └── /*     (React) │         └──────────┬──────────┘
└──────────┬──────────┘                    │
           │                               │
           ▼                               ▼
┌──────────────────────────────────────────────┐
│          Renderer                            │
│          renderer.py                         │
│                                              │
│  .scad → PNG / STL / Validate                │
└──────────────────┬───────────────────────────┘
                   │ subprocess
                   ▼
┌────────────────────────┐
│  OpenSCAD CLI          │
│  bin/openscad          │
│  (AppImage + 번들 GL)  │
└────────────────────────┘
```

**프로덕션 모드**: FastAPI가 API(`/api/*`)와 React 빌드 정적 파일(`/*`)을 단일 포트(8000)에서 서빙.

**개발 모드**: Vite dev server(3000, HMR) + FastAPI(8000). Vite가 `/api/*`를 8000으로 프록시.

---

## 디렉토리 구조

```
openscad-mcp/
├── run.sh                          # 프로젝트 관리 스크립트
├── ARCHITECTURE.md                 # 시스템 아키텍처 문서 (이 파일)
├── CLAUDE.md                       # AI 어시스턴트 지침
├── pyproject.toml                  # Python 패키지 설정
├── data/                           # .scad 디자인 파일 및 렌더링 결과물
│   ├── *.scad                      # OpenSCAD 디자인 소스
│   ├── *_preview.png               # 렌더링된 PNG 미리보기
│   └── *.stl                       # 3D 프린팅용 STL
├── bin/                            # OpenSCAD 실행 환경
│   ├── openscad                    # 래퍼 스크립트 (LD_LIBRARY_PATH 설정)
│   ├── OpenSCAD-x86_64.AppImage    # OpenSCAD 바이너리
│   └── lib/                        # 번들된 OpenGL 라이브러리
├── src/openscad_mcp/
│   ├── __init__.py
│   ├── renderer.py                 # OpenSCAD CLI 래퍼 (162행)
│   ├── web_api.py                  # FastAPI 서버 (152행)
│   └── server.py                   # MCP 서버 (108행)
├── web/                            # Vite + React 프론트엔드
│   ├── vite.config.js              # Vite 설정 (프록시 포함)
│   ├── package.json                # Node.js 의존성
│   ├── dist/                       # 프로덕션 빌드 출력
│   └── src/
│       ├── main.jsx                # React 진입점
│       ├── App.jsx                 # 메인 UI 컴포넌트 (212행)
│       ├── App.css                 # 앱 스타일 (98행)
│       ├── StlViewer.jsx           # Three.js 3D 뷰어 (185행)
│       ├── index.css               # 글로벌 스타일
│       ├── api/
│       │   └── openscad.js         # HTTP 클라이언트 (48행)
│       └── hooks/
│           └── useFileWatcher.js   # 파일 변경 감지 훅 (54행)
├── .run/                           # 런타임 (PID, 로그) — gitignored
└── .claude/launch.json             # MCP 서버 실행 설정
```

---

## 컴포넌트별 역할

### 1. Web UI (React + Vite)

#### App.jsx — 메인 UI

**상태 관리:**

| State | 타입 | 역할 |
|-------|------|------|
| `scadFile` | `string` | 선택된 .scad 파일 경로 |
| `fileList` | `{name, path}[]` | 드롭다운 파일 목록 |
| `previewUrl` | `string \| null` | PNG blob URL |
| `stlUrl` | `string \| null` | STL blob URL |
| `viewMode` | `'png' \| '3d'` | 현재 뷰 모드 |
| `status` | `{type, message} \| null` | 상태 메시지 (success/error) |
| `loading` | `string \| null` | 로딩 상태 (`'preview'`, `'3d'`, `'validate'`, `'export'`) |

**핸들러:**

| 함수 | 트리거 | 동작 |
|------|--------|------|
| `handlePreview()` | Preview PNG 버튼 | `renderPng()` → blob URL → `<img>` 표시 |
| `handle3DView()` | 3D View 버튼 | `fetchStl('preview')` → blob URL → `<StlViewer>` 표시 |
| `handleValidate()` | Validate 버튼 | `validateScad()` → 결과 status 표시 |
| `handleDownloadStl()` | Download STL 버튼 | `fetchStl('export')` → `<a>` 다운로드 트리거 |
| `refreshFiles()` | 마운트 시 + 드롭다운 포커스 시 | `GET /api/files` → 목록 갱신 |

**자동 갱신**: `useFileWatcher`로 현재 선택된 파일의 mtime 변경 감지 → `autoRefreshRef` 콜백 호출 → 현재 뷰 모드에 맞춰 자동 리렌더.

**UI 구성**: 파일 드롭다운(`<select>`) → 4개 액션 버튼 → 상태 메시지 → 프리뷰 영역(PNG `<img>` 또는 `<StlViewer>`).

#### StlViewer.jsx — Three.js 3D 뷰어

Props: `{ stlUrl: string }`

**Three.js 씬 구성:**

| 항목 | 설정 |
|------|------|
| 카메라 | `PerspectiveCamera(fov:45, near:0.1, far:10000)` |
| 배경 | `0xf5f5dc` (beige) |
| 조명 | `AmbientLight(0x404040, 2)` + `DirectionalLight(0xffffff, 2)` + `DirectionalLight(0xffffff, 1)` |
| 머티리얼 | `MeshPhongMaterial(color:0xb8a000, specular:0x333333, shininess:40)` (gold) |
| 캔버스 높이 | 500px 고정 |
| 인터랙션 | `OrbitControls` (damping 활성화) |

**STL 로딩 과정**: `fetch(stlUrl)` → `ArrayBuffer` → `STLLoader.parse()` → `computeVertexNormals()` → mesh 생성 → `computeBoundingBox()` → 모델 중심 이동(`position.sub(center)`) → 카메라 자동 피팅(`position(0, -maxDim*1.5, maxDim)`).

**오버레이:**
- **스케일 바 (좌하단)**: 카메라 거리 기반 mm/px 계산 → ~120px 타겟 → nice round number 선택 (`[1,2,5,10,20,50,100,200,500,1000]`). 매 프레임 갱신.
- **바운딩 박스 (우하단)**: `X × Y × Z mm` 치수 표시 (소수점 1자리).

#### api/openscad.js — HTTP 클라이언트

| 함수 | HTTP | 반환 | 비고 |
|------|------|------|------|
| `validateScad(scadFile)` | `POST /api/validate` | `{success, message}` | |
| `renderPng(scadFile, w?, h?)` | `POST /api/render/png` | blob URL | `URL.createObjectURL()` |
| `renderStl(scadFile)` | `POST /api/render/stl` | (다운로드 트리거) | App.jsx에서 미사용, 내부 `fetchStl` 사용 |

#### hooks/useFileWatcher.js — 파일 변경 감지

```
useFileWatcher({ enabled, interval=2000, onChange, onNewFiles })
```

| 파라미터 | 타입 | 역할 |
|----------|------|------|
| `enabled` | `boolean` | 로딩 중일 때 비활성화 |
| `interval` | `number` | 폴링 간격 (ms, 기본 2000) |
| `onChange` | `(changedFiles: string[]) => void` | 기존 파일 mtime 변경 시 |
| `onNewFiles` | `(addedFiles: string[]) => void` | 새 파일 추가 시 |

**동작**: `GET /api/files/status` 폴링 → `{파일명: mtime}` 맵 비교 → 변경/추가 감지. 백엔드 미접속 시 무시.

---

### 2. Web API (FastAPI)

**파일**: `src/openscad_mcp/web_api.py` (152행)

**앱 설정:**
- `FastAPI(title="OpenSCAD Web API", version="0.2.0")`
- CORS: `http://localhost:3000`, `http://127.0.0.1:3000` 허용
- 데이터 디렉토리: `PROJECT_ROOT / "data"`
- 정적 파일: `DIST_DIR = PROJECT_ROOT / "web" / "dist"` — 디렉토리 존재 시 `StaticFiles(html=True)`로 마운트

**Pydantic 요청 모델:**

| 모델 | 필드 |
|------|------|
| `ValidateRequest` | `scad_file: str` |
| `RenderPngRequest` | `scad_file: str`, `width: int = 1024`, `height: int = 768` |
| `RenderStlRequest` | `scad_file: str`, `quality: str = "preview"` |

**품질 프리셋 (OpenSCAD 변수 오버라이드):**

| 상수 | 값 | 용도 |
|------|-----|------|
| `QUALITY_3D` | `{num_steps:30, $fn:36}` | 3D View (빠른 STL, ~5초) |
| `QUALITY_PNG` | `{num_steps:100, $fn:60}` | PNG 미리보기 (~30초) |
| `QUALITY_EXPORT` | `{num_steps:100, $fn:90}` | 고품질 STL 다운로드 (~1-2분) |

**임시 파일 정리**: `FileResponse`에 `BackgroundTask`로 전송 완료 후 자동 삭제.

---

### 3. Renderer

**파일**: `src/openscad_mcp/renderer.py` (162행)

**데이터 모델:**

```python
@dataclass
class RenderResult:
    success: bool
    output_path: str | None = None
    file_size: int | None = None
    stdout: str = ""
    stderr: str = ""
```

**함수:**

| 함수 | 시그니처 | 역할 |
|------|----------|------|
| `render_to_png()` | `(scad_file, output_path?, width=1024, height=768, overrides?)` | PNG 렌더링. `--autocenter --viewall --imgsize` 플래그 사용. 출력 미지정 시 temp 파일 생성. |
| `render_to_stl()` | `(scad_file, output_path?, overrides?)` | STL 렌더링. 출력 미지정 시 `.scad`와 같은 경로에 `.stl` 생성. |
| `validate()` | `(scad_file)` | 구문 검사. temp STL 렌더(30초 타임아웃) 후 삭제. |
| `_run_openscad()` | `(args, timeout=RENDER_TIMEOUT)` | subprocess 실행. `FileNotFoundError`, `TimeoutExpired` 처리. |
| `_build_overrides()` | `(overrides)` | `dict → -D flag` 목록 변환. |

**환경 변수:**

| 변수 | 기본값 | 역할 |
|------|--------|------|
| `OPENSCAD_PATH` | `bin/openscad` (프로젝트 상대 경로) | OpenSCAD 실행 파일 경로 |
| `OPENSCAD_TIMEOUT` | `600` (초) | 렌더링 타임아웃 |

---

### 4. MCP Server

**파일**: `src/openscad_mcp/server.py` (108행)

`FastMCP("openscad-mcp")` — stdio transport

| Tool | 시그니처 | 반환 타입 | 동작 |
|------|----------|-----------|------|
| `render_preview` | `(scad_file, width=1024, height=768)` | `list[dict]` | PNG 렌더 → base64 인코딩 → `[{type:"image", data, mimeType}, {type:"text", text}]`. temp 파일 정리. |
| `render_stl` | `(scad_file, output_path="")` | `str` | STL 렌더 → 성공 메시지(경로, 크기) 또는 실패 메시지. |
| `validate_scad` | `(scad_file)` | `str` | 구문 검사 → "Syntax is valid." + WARNING 필터링, 또는 에러 메시지. |

---

### 5. OpenSCAD CLI

CSG(Constructive Solid Geometry) 렌더링 엔진. `.scad` 스크립트를 읽어 PNG/STL로 출력.

| 항목 | 값 |
|------|-----|
| 실행 파일 | `bin/openscad` (AppImage 래퍼 스크립트) |
| 바이너리 | `bin/OpenSCAD-x86_64.AppImage` |
| GL 라이브러리 | `bin/lib/usr/lib/x86_64-linux-gnu/` |
| 렌더 타임아웃 | 600초 (기본), `OPENSCAD_TIMEOUT` 환경변수로 변경 가능 |
| 검증 타임아웃 | 30초 (고정) |

**래퍼 스크립트 (`bin/openscad`)**: `LD_LIBRARY_PATH`에 번들 GL 라이브러리 경로 추가 후 AppImage 실행.

---

## 데이터 흐름 상세

### 흐름 1: PNG 미리보기

```
사용자: "Preview PNG" 클릭
  │
  ▼
App.jsx handlePreview()
  → loading='preview', status=null
  │
  ▼  renderPng(scadFile) — api/openscad.js
  │
  ▼  POST /api/render/png {scad_file, width:1024, height:768}
  │
web_api.py api_render_png()
  → asyncio.to_thread(render_to_png, ..., overrides=QUALITY_PNG)
  │
  ▼
renderer.py render_to_png()
  → bin/openscad --autocenter --viewall --imgsize=1024,768
       -D'num_steps=100' -D'$fn=60' -o /tmp/openscad_preview_XXX.png input.scad
  │
  ▼  RenderResult{success, output_path, file_size}
  │
web_api.py
  → FileResponse(PNG, background=삭제 태스크)
  │
  ▼  blob
  │
App.jsx
  → URL.createObjectURL(blob) → setPreviewUrl(url)
  → viewMode='png' → <img src={url}>
```

### 흐름 2: 3D 뷰어 (STL 미리보기)

```
사용자: "3D View" 클릭
  │
  ▼
App.jsx handle3DView()
  → loading='3d', status=null
  │
  ▼  fetchStl('preview') — App.jsx 내부 함수
  │
  ▼  POST /api/render/stl {scad_file, quality:"preview"}
  │
web_api.py api_render_stl()
  → overrides = QUALITY_3D (num_steps:30, $fn:36)
  → tempfile → asyncio.to_thread(render_to_stl, ..., overrides)
  │
  ▼
renderer.py render_to_stl()
  → bin/openscad -D'num_steps=30' -D'$fn=36' -o /tmp/openscad_web_XXX.stl input.scad
  │
  ▼  FileResponse(STL, background=삭제 태스크)
  │
  ▼  blob → URL.createObjectURL()
  │
StlViewer.jsx
  ├── fetch(stlUrl) → ArrayBuffer
  ├── STLLoader.parse(buf)
  ├── geometry.computeVertexNormals()
  ├── MeshPhongMaterial(gold: 0xb8a000)
  ├── computeBoundingBox() → center → camera fit
  ├── OrbitControls (마우스 회전/줌)
  ├── 스케일 바 (좌하단, 매 프레임 갱신)
  └── 바운딩 박스 치수 (우하단)
```

### 흐름 3: STL 다운로드 (고품질)

```
사용자: "Download STL" 클릭
  │
  ▼
App.jsx handleDownloadStl()
  → loading='export', status=null
  │
  ▼  fetchStl('export')
  │
  ▼  POST /api/render/stl {scad_file, quality:"export"}
  │
web_api.py api_render_stl()
  → overrides = QUALITY_EXPORT (num_steps:100, $fn:90)
  → 렌더링 (~1-2분)
  │
  ▼  blob
  │
App.jsx
  → URL.createObjectURL(blob)
  → <a href={url} download="파일명.stl">.click()
  → URL.revokeObjectURL(url)
```

### 흐름 4: 파일 변경 자동 감지

```
useFileWatcher (2초 간격 폴링)
  │
  ▼  GET /api/files/status
  │
web_api.py files_status()
  → data/*.scad의 {name: mtime} 반환
  │
  ▼  prevRef와 비교
  │
  ├── 기존 파일 mtime 변경 → onChange(changedFiles)
  │     → 현재 선택 파일이면 autoRefreshRef.current()
  │       → 현재 viewMode에 따라 handlePreview() 또는 handle3DView() 자동 호출
  │
  └── 새 파일 추가 → onNewFiles(addedFiles)
        → refreshFiles() → 드롭다운 갱신
```

### 흐름 5: MCP Tool 호출 (외부 AI 연동)

```
Claude Desktop / AI 클라이언트
  │
  ▼  MCP tool call: render_preview(scad_file="data/suv.scad")
  │
server.py (FastMCP, stdio transport)
  │
  ├── renderer.py render_to_png(scad_file)
  │     → bin/openscad --autocenter --viewall → /tmp/openscad_preview_XXX.png
  │
  ├── png_path.read_bytes() → base64.standard_b64encode()
  │
  ├── temp 파일 삭제
  │
  └── 반환: [{type:"image", data:base64, mimeType:"image/png"},
             {type:"text", text:"Preview of: ..."}]
  │
  ▼
Claude가 렌더 이미지를 보고 분석/대화 가능
```

---

## API 엔드포인트

| 메서드 | 경로 | 요청 | 응답 | 용도 |
|--------|------|------|------|------|
| GET | `/api/health` | — | `{status: "ok"}` | 상태 확인 |
| GET | `/api/files` | — | `{files: [{name, path}]}` | data/ 내 .scad 파일 목록 (이름순 정렬) |
| GET | `/api/files/status` | — | `{files: {name: mtime}}` | 파일별 수정 시각 (폴링용) |
| POST | `/api/validate` | `{scad_file}` | `{success, message}` | 구문 검사 |
| POST | `/api/render/png` | `{scad_file, width?:1024, height?:768}` | PNG blob | QUALITY_PNG 오버라이드 적용 |
| POST | `/api/render/stl` | `{scad_file, quality?:"preview"}` | STL blob | `"preview"` → QUALITY_3D, `"export"` → QUALITY_EXPORT |

**정적 파일 서빙**: `web/dist/` 존재 시 `StaticFiles(directory, html=True)`로 `/*`에 마운트. API 라우트(`/api/*`)가 우선.

---

## MCP Tool 목록

| Tool | 시그니처 | 반환 | 용도 |
|------|----------|------|------|
| `render_preview` | `(scad_file, width?=1024, height?=768)` | `[{type:"image", data:base64, mimeType}, {type:"text", ...}]` | PNG 미리보기. temp 파일 자동 삭제. |
| `render_stl` | `(scad_file, output_path?="")` | `str` (성공: 경로+크기, 실패: 에러) | STL 렌더링 |
| `validate_scad` | `(scad_file)` | `str` (성공: "Syntax is valid." + 경고, 실패: 에러) | 구문 검증. WARNING 라인만 필터링 표시. |

---

## CLI 진입점

| 명령 | 모듈 | 설명 |
|------|------|------|
| `openscad-web` | `web_api:main` | FastAPI 서버 (port 8000, `uvicorn.run()`) |
| `openscad-mcp` | `server:main` | MCP stdio 서버 (`mcp.run(transport="stdio")`) |

---

## run.sh 명령

| 명령 | 동작 |
|------|------|
| `setup` | venv 생성, `pip install -e .`, `npm install`, OpenSCAD AppImage 다운로드 |
| `start` | **프로덕션**: `npm run build` → FastAPI 단일 서버(8000) 시작. `web/dist/`에서 정적 파일 서빙. |
| `dev` | **개발**: FastAPI(8000) + Vite dev server(3000, HMR) 동시 시작. Vite가 `/api`를 8000으로 프록시. |
| `stop` | PID 파일 기반 종료 (`kill_tree`) → 포트 8000/3000 폴백 정리 |
| `restart` | `stop` → `start` |
| `status` | PID 파일의 프로세스 생존 확인 |
| `build` | `npm run build` → `web/dist/` 생성 |

**런타임 파일**: `.run/pids` (프로세스 PID), `.run/backend.log`, `.run/frontend.log`

---

## Vite 개발 서버 설정

**파일**: `web/vite.config.js`

| 항목 | 값 |
|------|-----|
| 호스트 | `127.0.0.1` |
| 포트 | `3000` |
| 프록시 | `/api` → `http://localhost:8000` (`changeOrigin: true`) |
| 플러그인 | `@vitejs/plugin-react` |

---

## 환경 변수

| 변수 | 기본값 | 역할 |
|------|--------|------|
| `OPENSCAD_PATH` | `bin/openscad` | OpenSCAD 실행 파일 경로 |
| `OPENSCAD_TIMEOUT` | `600` | 렌더링 타임아웃 (초) |

---

## 의존성

### Python (`pyproject.toml`)

| 패키지 | 버전 | 역할 |
|--------|------|------|
| `mcp[cli]` | — | MCP 프로토콜 서버 (FastMCP) |
| `fastapi` | ≥0.115.0 | REST API 프레임워크 |
| `uvicorn[standard]` | ≥0.30.0 | ASGI 서버 |

### Node.js (`web/package.json`)

| 패키지 | 버전 | 역할 |
|--------|------|------|
| `react` | ^19.2.0 | UI 프레임워크 |
| `react-dom` | ^19.2.0 | React DOM 렌더러 |
| `three` | ^0.183.1 | 3D 렌더링 (STLLoader, OrbitControls) |
| `vite` | ^7.3.1 | 빌드/개발 서버 |
| `@vitejs/plugin-react` | ^5.1.1 | React HMR/JSX 지원 |

---

## 파일 수명 주기

| 경로 패턴 | 생성자 | 수명 |
|-----------|--------|------|
| `data/*.scad` | 사용자 | 영구 |
| `data/*_preview.png` | renderer.py | 선택적 보관 |
| `data/*.stl` | renderer.py | 선택적 보관 |
| `/tmp/openscad_preview_*.png` | renderer.py (render_to_png) | HTTP 전송 후 BackgroundTask로 삭제 |
| `/tmp/openscad_web_*.stl` | web_api.py (api_render_stl) | HTTP 전송 후 BackgroundTask로 삭제 |
| `/tmp/openscad_validate_*.stl` | renderer.py (validate) | finally 블록에서 즉시 삭제 |
| `.run/pids` | run.sh | 서버 종료 시 삭제 |
| `.run/*.log` | run.sh | 수동 삭제 |
