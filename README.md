# openscad-mcp

OpenSCAD 3D 모델을 생성·렌더링하고 웹 브라우저에서 인터랙티브하게 미리보기할 수 있는 도구.

![Preview](data/50_to_100_transition_pipe_preview.png)

---

## 주요 기능

- `.scad` 파일을 받아 **PNG 미리보기** 또는 **STL** 로 렌더링
- **Three.js 기반 3D 웹 뷰어** — 드래그 회전, 스크롤 줌, 동적 스케일 바, 바운딩 박스 치수
- 품질 프리셋 — 빠른 웹 미리보기 / 고품질 PNG / 최종 STL 출력 분리
- FastAPI REST API로 외부 연동 가능
- MCP(Model Context Protocol) 서버 내장
- `run.sh` 관리 스크립트로 설치/실행/종료 통합 관리

---

## 구조

```
openscad-mcp/
├── run.sh                 # 프로젝트 관리 스크립트 (setup/start/dev/stop/build)
├── data/                  # .scad 소스 및 렌더링 결과 (PNG, STL)
├── bin/                   # OpenSCAD AppImage + 번들 라이브러리
│   ├── openscad           # 래퍼 스크립트
│   └── OpenSCAD-x86_64.AppImage
├── src/openscad_mcp/
│   ├── renderer.py        # OpenSCAD CLI 래퍼
│   ├── web_api.py         # FastAPI 서버 (REST API + 정적 파일 서빙)
│   └── server.py          # MCP 서버
└── web/                   # React 프론트엔드
    ├── vite.config.js     # Vite 설정 (dev 프록시 포함)
    ├── dist/              # 프로덕션 빌드 출력
    └── src/
        ├── App.jsx        # 메인 UI (파일 드롭다운, 버튼)
        ├── StlViewer.jsx  # Three.js 3D 뷰어 (스케일 바, 바운딩 박스)
        ├── api/openscad.js        # HTTP 클라이언트 (API 호출 래퍼)
        └── hooks/useFileWatcher.js  # 파일 변경 감지 (2초 폴링)
```

---

## 요구사항

| 항목 | 버전 |
|------|------|
| Python | 3.10+ |
| Node.js | 18+ (nvm 사용 시 `nvm use 20`) |
| [OpenSCAD](https://openscad.org/downloads.html) | 자동 설치 (AppImage) |

> OpenSCAD는 `./run.sh setup` 실행 시 `bin/` 디렉토리에 자동 다운로드됩니다.
> 다른 경로를 사용하려면 환경 변수 `OPENSCAD_PATH`로 지정하세요.

---

## 설치 및 실행

```bash
# 1. 저장소 클론
git clone https://github.com/your-username/openscad-mcp.git
cd openscad-mcp

# 2. 환경 설정 (venv + 패키지 + OpenSCAD)
./run.sh setup

# 3. 서버 시작 (프론트엔드 빌드 + 단일 서버 8000)
./run.sh start
```

브라우저에서 `http://localhost:8000` 접속

### 관리 명령어

```bash
./run.sh setup     # venv 생성, 패키지 설치, OpenSCAD 다운로드
./run.sh start     # 프론트엔드 빌드 + 서버 시작 (port 8000)
./run.sh stop      # 모든 서버 종료
./run.sh dev       # 개발 모드: 백엔드(8000) + Vite HMR(3000)
./run.sh restart   # 재시작
./run.sh status    # 서버 상태 확인
./run.sh build     # 프론트엔드 프로덕션 빌드
```

---

## 사용법

1. 드롭다운에서 `.scad` 파일 선택 (새 파일은 드롭다운 클릭 시 자동 갱신)
2. **3D View** — Three.js 인터랙티브 뷰어 (동적 스케일 바 + 바운딩 박스 치수)
3. **Preview PNG** — 고품질 정적 PNG 렌더링
4. **Validate** — 문법 검사
5. **Download STL** — 최종 STL 출력

---

## 렌더링 품질 프리셋

| 용도 | num_steps | $fn | 소요 시간 |
|------|-----------|-----|-----------|
| 3D View (웹) | 30 | 36 | ~5초 |
| Preview PNG | 100 | 60 | ~30초 |
| Download STL | 100 | 90 | ~1~2분 |

---

## REST API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/health` | 서버 상태 확인 |
| GET | `/api/files` | `data/` 내 .scad 파일 목록 |
| GET | `/api/files/status` | 파일별 수정 시각 (변경 감지 폴링) |
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
| `50_to_100_transition_pipe.scad` | 원형 Ø50mm → 원형 Ø100mm, 양끝 10mm 평탄, 길이 150mm |
| `90deg_bent_pipe_30mm.scad` | Ø30mm 파이프, 90도 곡관, 벽 3mm, 곡률 60mm |
| `simple_suv.scad` | 심플 SUV 자동차 모델 (100mm 스케일) |
| `simple_car_basic.scad` | 심플 세단 모델 |
| `simple_truck_basic.scad` | 심플 트럭 모델 |
| `simple_laptop.scad` | 노트북 모델 |
| `simple_game_controller.scad` | 게임 컨트롤러 모델 |
| `simple_zippo_lighter.scad` | 지포 라이터 모델 |

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

`~/.config/Claude/claude_desktop_config.json` (Linux) 또는 `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "openscad": {
      "command": "/path/to/openscad-mcp/.venv/bin/python",
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
command = "/path/to/openscad-mcp/.venv/bin/python"
args = ["-m", "openscad_mcp.server"]
cwd = "/path/to/openscad-mcp"
```

---

### Cursor / VS Code / Windsurf

`.cursor/mcp.json` 또는 `.vscode/mcp.json`

```json
{
  "mcpServers": {
    "openscad": {
      "command": "/path/to/openscad-mcp/.venv/bin/python",
      "args": ["-m", "openscad_mcp.server"]
    }
  }
}
```

> Windows는 `.venv/bin/python`을 `.venv/Scripts/python`으로 변경

---

## 라이선스

MIT
