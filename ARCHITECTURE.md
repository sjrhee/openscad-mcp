# OpenSCAD MCP — 아키텍처 및 데이터 흐름

## 시스템 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                        사용자                                    │
│            브라우저 (localhost:3000)  /  터미널 CLI               │
└──────────┬──────────────────────────────────┬───────────────────┘
           │ HTTP                              │ stdin/stdout
           ▼                                   ▼
┌─────────────────────┐             ┌─────────────────────┐
│   Web UI (React)    │             │   MCP Server        │
│   port 3000         │             │   stdio transport    │
│                     │             │                     │
│ App.jsx             │             │ server.py           │
│ StlViewer.jsx       │             │ 3개 tool 노출       │
│ api/openscad.js     │             └──────────┬──────────┘
│ hooks/useFileWatcher│                        │
└──────────┬──────────┘                        │
           │ REST API (/api/*)                 │
           ▼                                   │
┌──────────────────────────────────────────────┤
│          Web API (FastAPI)                   │
│          port 8000                           │
│                                              │
│  web_api.py                                  │
│  ├── 렌더링 엔드포인트 (/render/png, /stl)  │
│  ├── 파일 관리 (/files, /files/status)       │
│  └── 에이전트 세션 (/agent/*)                │
└──────────┬──────────────┬────────────────────┘
           │              │
           ▼              ▼
┌────────────────┐  ┌──────────────────────┐
│  Renderer      │  │  Design Agent        │
│  renderer.py   │  │  design_agent.py     │
│                │  │                      │
│  .scad → PNG   │  │  평가 루프           │
│  .scad → STL   │  │  코드 생성/개선      │
│  .scad 검증    │  │  수렴 판정           │
└───────┬────────┘  └──────────┬───────────┘
        │                      │
        ▼                      ▼
┌────────────────┐  ┌──────────────────────┐
│  OpenSCAD CLI  │  │  Claude API (LLM)    │
│  bin/openscad  │  │  Anthropic SDK       │
│                │  │                      │
│  CSG 렌더링    │  │  비전 평가 (PNG)     │
│  엔진          │  │  코드 생성 (텍스트)  │
└────────────────┘  └──────────────────────┘
```

---

## 컴포넌트별 역할

### 1. Web UI (React + Vite)

| 파일 | 역할 |
|------|------|
| `web/src/App.jsx` | 메인 UI — 파일 선택, 렌더링 버튼, 에이전트 패널 |
| `web/src/StlViewer.jsx` | Three.js 3D 뷰어 — OrbitControls, 스케일 바, 바운딩 박스 |
| `web/src/api/openscad.js` | HTTP 클라이언트 — 백엔드 REST API 호출 래퍼 |
| `web/src/hooks/useFileWatcher.js` | 파일 변경 감지 — 2초 폴링, 자동 갱신 트리거 |
| `web/src/App.css` | 스타일 — 에이전트 패널, 점수 배지, 기준 바 등 |

**역할**: 사용자 인터페이스. 파일 선택, 렌더링 요청, 에이전트 대화형 제어(시작/적용/피드백/중지).

### 2. Web API (FastAPI)

| 파일 | 역할 |
|------|------|
| `src/openscad_mcp/web_api.py` | FastAPI 서버 — 렌더링 + 에이전트 세션 관리 |

**역할**: 프론트엔드와 백엔드 로직 사이의 REST 게이트웨이. 에이전트 세션을 인메모리로 유지하고, 렌더링 요청을 Renderer에 위임.

### 3. Renderer

| 파일 | 역할 |
|------|------|
| `src/openscad_mcp/renderer.py` | OpenSCAD CLI 래퍼 — subprocess로 실행 |

**역할**: `.scad` 파일을 OpenSCAD CLI에 전달하여 PNG/STL로 변환. 품질 프리셋별 변수 오버라이드(`$fn`, `num_steps`) 지원.

### 4. Design Agent

| 파일 | 역할 |
|------|------|
| `src/openscad_mcp/design_agent.py` | 평가 루프, 프롬프트, Claude API 호출, 파싱 |

**역할**: Claude 비전 API를 사용하여 렌더된 이미지 + 소스코드를 평가하고, 개선된 코드를 제안하는 반복 루프. CLI와 웹 API 양쪽에서 사용.

### 5. MCP Server

| 파일 | 역할 |
|------|------|
| `src/openscad_mcp/server.py` | MCP 프로토콜 서버 (stdio transport) |

**역할**: Claude Desktop 등 외부 AI 클라이언트가 OpenSCAD 렌더링을 MCP tool로 호출할 수 있게 노출. 웹 UI와는 독립적으로 동작.

### 6. Claude API (LLM)

**역할**: Design Agent의 두뇌. 두 가지 모드로 사용됨:
- **비전 평가**: 렌더된 PNG 이미지 + .scad 소스코드를 보고 품질 점수, 이슈, 개선 코드를 JSON으로 반환
- **코드 생성**: 텍스트 설명으로부터 초기 .scad 코드를 생성

| 항목 | 값 |
|------|-----|
| 모델 | `claude-opus-4-20250514` |
| SDK | `anthropic` Python SDK |
| max_tokens | 8192 |
| 재시도 | 지수 백오프, 최대 3회 |
| API 키 | `.env` 또는 환경변수 `ANTHROPIC_API_KEY` |

### 7. OpenSCAD CLI

**역할**: CSG(Constructive Solid Geometry) 렌더링 엔진. `.scad` 스크립트를 읽어 PNG 이미지 또는 STL 3D 모델로 출력.

| 항목 | 값 |
|------|-----|
| 실행 파일 | `bin/openscad` (AppImage 래퍼) |
| 라이브러리 | `bin/lib/` (번들된 OpenGL) |
| 타임아웃 | 120초 |

---

## 데이터 흐름 상세

### 흐름 1: PNG 미리보기

```
사용자: "Preview PNG" 클릭
  │
  ▼
App.jsx → renderPng(scadFile)
  │
  ▼  POST /api/render/png {scad_file, width:1024, height:768}
  │
web_api.py → render_to_png(scad_file, overrides={num_steps:100, $fn:60})
  │
  ▼  subprocess
  │
renderer.py → bin/openscad -D'$fn=60' -D'num_steps=100' -o /tmp/out.png input.scad
  │
  ▼  RenderResult{success, output_path}
  │
web_api.py → FileResponse(PNG 바이너리, 전송 후 삭제)
  │
  ▼  blob
  │
App.jsx → URL.createObjectURL(blob) → <img src={url}>
```

### 흐름 2: 에이전트 평가 (Review 모드)

```
사용자: "AI Review" 클릭
  │
  ▼
App.jsx → agentStart(scadFile, 'review')
  │
  ▼  POST /api/agent/start {scad_file, mode:"review"}
  │
web_api.py
  ├── 파일 읽기 → current_code
  ├── AgentSession 생성 (uuid, messages=[], history=[])
  └── 응답: {session_id, scad_file, mode}
  │
  ▼
App.jsx → agentEvaluate(session_id)
  │
  ▼  POST /api/agent/evaluate {session_id}
  │
web_api.py ─────────────────────────────────────────────────┐
  │                                                          │
  │ 1. 렌더링                                                │
  ├──→ renderer.py → render_to_png(overrides=QUALITY_EVAL)   │
  │    → OpenSCAD → /tmp/preview.png                         │
  │    → image_to_base64(png) → "iVBOR..."                   │
  │                                                          │
  │ 2. Claude 호출                                           │
  ├──→ messages에 추가:                                      │
  │    user: [텍스트, PNG이미지(base64), .scad코드]          │
  │                                                          │
  ├──→ call_claude(SYSTEM_PROMPT, messages, model)           │
  │    → anthropic.messages.create()                         │
  │    → Claude 응답: ```json { score, issues, code } ```    │
  │                                                          │
  │ 3. 파싱                                                  │
  ├──→ parse_evaluation(response_text)                       │
  │    → EvalResult{score, criteria_scores, issues,          │
  │                 suggested_code, stop_reason}              │
  │                                                          │
  │ 4. 세션 업데이트                                         │
  ├──→ session.pending_code = suggested_code                 │
  ├──→ session.history.append(record)                        │
  ├──→ 수렴 판정 (점수 + 잔여 이슈)                         │
  │                                                          │
  └──→ 응답: {score, criteria_scores, issues,                │
              has_suggested_code, preview_base64,             │
              converged, history}                             │
  │                                                          │
  ▼                                                          │
App.jsx                                                      │
  ├── 점수 배지 (색상 코딩)                                  │
  ├── 기준별 프로그레스 바                                    │
  ├── 이슈 목록                                              │
  ├── [Apply] / [Skip] / [Send Feedback] 버튼                │
  └── 점수 이력 (4 → 7 → 9)                                 │
       │                                                     │
       ▼ 사용자 선택                                         │
  ┌────┴─────────────────────────────────────────┐           │
  │                                               │           │
  │ [Apply Changes]                               │           │
  │  → POST /api/agent/apply {session_id}         │           │
  │  → apply_code(scad_path, pending_code)        │           │
  │    → .scad.tmp 작성 → validate → rename       │           │
  │  → session.current_code 갱신                  │           │
  │  → 다시 agentEvaluate() ──────────────────────┼──→ 반복  │
  │                                               │           │
  │ [Skip]                                        │           │
  │  → 코드 변경 없이 agentEvaluate() ───────────┼──→ 반복  │
  │                                               │           │
  │ [Send Feedback]                               │           │
  │  → agentEvaluate(session_id, feedback) ───────┼──→ 반복  │
  │    (사용자 피드백이 다음 메시지에 포함)        │           │
  │                                               │           │
  │ [Stop]                                        │           │
  │  → POST /api/agent/stop {session_id}          │           │
  │  → 세션 삭제, 패널 닫기                       │           │
  └───────────────────────────────────────────────┘           │
```

### 흐름 3: 에이전트 생성 (Generate 모드)

```
사용자: Generate 탭 → "simple zippo lighter" 입력 → AI Review 클릭
  │
  ▼  POST /api/agent/start {mode:"generate", description:"simple zippo lighter"}
  │
web_api.py
  ├── slug 생성: "simple_zippo_lighter" (한글은 UUID 폴백)
  ├── generate_initial_code(client, description, model)
  │     │
  │     ▼  Claude API 호출 (GENERATE_SYSTEM_PROMPT)
  │     │  user: "Create an OpenSCAD design for: simple zippo lighter"
  │     │
  │     ▼  Claude 응답: ```openscad ... ``` 블록
  │     │
  │     └── .scad 코드 추출
  │
  ├── apply_code(data/simple_zippo_lighter.scad, code)
  │     → validate → 파일 저장
  │
  ├── AgentSession 생성
  └── 응답: {session_id, scad_file, mode:"generate"}
  │
  ▼
  이후 Review 모드와 동일한 평가 루프 진행
```

### 흐름 4: MCP Tool 호출 (외부 AI 연동)

```
Claude Desktop / AI 클라이언트
  │
  ▼  MCP tool call: render_preview(scad_file="data/suv.scad")
  │
server.py (stdio transport)
  │
  ├── renderer.py → render_to_png()
  │     → OpenSCAD CLI → PNG 파일
  │
  ├── PNG → base64 인코딩
  │
  └── MCP 응답: [{type:"image", data:base64}, {type:"text", ...}]
  │
  ▼
Claude가 렌더 이미지를 보고 분석/대화 가능
```

### 흐름 5: 파일 변경 자동 감지

```
useFileWatcher (2초 간격 폴링)
  │
  ▼  GET /api/files/status
  │
web_api.py → data/*.scad 의 mtime 반환
  │
  ▼  이전 mtime과 비교
  │
  ├── 변경된 파일 있음 → onChange(changedFiles)
  │     → 현재 선택된 파일이면 자동 렌더링 갱신
  │
  └── 새 파일 있음 → onNewFiles()
        → 파일 목록 드롭다운 갱신
```

---

## Claude API 호출 상세

### 시스템 프롬프트

| 프롬프트 | 용도 | 핵심 원칙 |
|----------|------|-----------|
| `SYSTEM_PROMPT` | 평가 (Review/Evaluate) | "실루엣 우선, 디테일 나중". recognizability와 proportions에 2배 가중치 |
| `GENERATE_SYSTEM_PROMPT` | 코드 생성 (Generate) | 아이코닉/기본 상태로 디자인. 내부 구조보다 외형 형태 우선 |

### 멀티턴 대화 구조

```
session.messages = [
  ── 반복 1 ──
  {role: "user", content: [
    {type: "text",  text: "이 디자인을 평가해주세요..."},
    {type: "image", source: {type: "base64", data: "PNG데이터"}},
    {type: "text",  text: "현재 코드:\n```openscad\n...\n```"}
  ]},
  {role: "assistant", content: "```json\n{score:5, issues:[...], suggested_code:\"...\"}\n```"},

  ── 반복 2 ──
  {role: "user", content: [
    {type: "text",  text: "반복 2: 이전 제안 적용 후 업데이트된 렌더와 코드입니다."},
    {type: "image", source: {type: "base64", data: "새PNG데이터"}},
    {type: "text",  text: "현재 코드:\n```openscad\n...(개선된 코드)\n```"}
  ]},
  {role: "assistant", content: "```json\n{score:8, issues:[], suggested_code:null}\n```"},
  ...
]
```

Claude는 이전 모든 반복의 이미지/코드/평가를 컨텍스트로 보유 → 진행 상황 추적, 정체 감지 가능.

### 평가 응답 JSON 구조

```json
{
  "score": 7,
  "summary": "비율이 정확하지만 상단 디테일 부족",
  "criteria_scores": {
    "recognizability": 8,
    "proportions": 8,
    "visual_quality": 7,
    "structural": 6,
    "code_quality": 7
  },
  "issues": [
    "상단 뚜껑이 완전히 닫히지 않음",
    "힌지가 본체와 분리되어 보임"
  ],
  "suggested_code": "// Full .scad code...\nmodule lighter_body() { ... }",
  "stop_reason": null
}
```

---

## 수렴 로직

에이전트는 다음 조건에서 반복을 종료:

| 조건 | 설명 |
|------|------|
| `score >= target` AND `suggested_code == null` | 목표 도달 + 잔여 이슈 없음 |
| `stop_reason == "no_improvement"` | Claude가 더 개선 불가 판단 |
| 최근 3회 점수 비감소 | 점수 정체 (stagnant) |
| `iteration >= max_iterations` | 최대 반복 횟수 도달 |

핵심: 점수가 목표에 도달해도 이슈가 남아있으면(`suggested_code != null`) 계속 반복.

---

## API 엔드포인트 전체 목록

| 메서드 | 경로 | 입력 | 출력 | 용도 |
|--------|------|------|------|------|
| GET | `/api/health` | — | `{status}` | 상태 확인 |
| GET | `/api/files` | — | `{files: [{name, path}]}` | .scad 목록 |
| GET | `/api/files/status` | — | `{files: {name: mtime}}` | 변경 감지 |
| POST | `/api/validate` | `{scad_file}` | `{success, message}` | 문법 검사 |
| POST | `/api/render/png` | `{scad_file, width, height}` | PNG blob | 미리보기 |
| POST | `/api/render/stl` | `{scad_file, quality}` | STL blob | 3D 모델 |
| POST | `/api/agent/start` | `{scad_file, mode, description, model, target_score, max_iterations}` | `{session_id, scad_file, mode}` | 세션 생성 |
| POST | `/api/agent/evaluate` | `{session_id, feedback?}` | `{score, criteria_scores, issues, preview_base64, converged, history, ...}` | 1회 평가 반복 |
| POST | `/api/agent/apply` | `{session_id}` | `{success, message}` | 코드 적용 |
| POST | `/api/agent/stop` | `{session_id}` | `{success, history}` | 세션 종료 |

---

## MCP Tool 목록

| Tool | 입력 | 출력 | 용도 |
|------|------|------|------|
| `render_preview` | `scad_file, width?, height?` | base64 PNG + 텍스트 | 미리보기 렌더링 |
| `render_stl` | `scad_file, output_path?` | 파일 경로 + 메타 | STL 렌더링 |
| `validate_scad` | `scad_file` | 성공/실패 + stderr | 문법 검증 |

---

## CLI 진입점

| 명령 | 모듈 | 설명 |
|------|------|------|
| `openscad-web` | `web_api:main` | FastAPI 서버 (port 8000) |
| `openscad-mcp` | `server:main` | MCP stdio 서버 |
| `openscad-agent review <file>` | `design_agent:main` | 기존 파일 리뷰 |
| `openscad-agent generate "<설명>"` | `design_agent:main` | 새 디자인 생성 |

CLI 옵션: `--auto`, `--dry-run`, `-n`, `-t`, `-m`, `-o`

---

## 품질 프리셋

| 용도 | `num_steps` | `$fn` | 소요 시간 | 사용처 |
|------|-------------|-------|-----------|--------|
| 3D View (STL 미리보기) | 30 | 36 | ~5초 | 웹 인터랙티브 뷰어 |
| 에이전트 평가 | 50 | 60 | ~10초 | design_agent 반복 루프 |
| PNG 미리보기 | 100 | 60 | ~30초 | Preview PNG 버튼 |
| STL 최종 출력 | 100 | 90 | ~1-2분 | Download STL 버튼 |

---

## 파일 수명 주기

| 경로 | 생성자 | 수명 |
|------|--------|------|
| `data/*.scad` | 사용자 / design_agent | 영구 |
| `data/*_preview.png` | renderer.py | 선택적 보관 |
| `data/*.stl` | renderer.py | 선택적 보관 |
| `/tmp/openscad_preview_*.png` | renderer.py | 평가 후 즉시 삭제 |
| `/tmp/openscad_web_*.stl` | web_api.py | HTTP 전송 후 삭제 |
| `*.scad.tmp` | design_agent | 검증 후 rename 또는 삭제 |
| `.run/*.pid, .run/*.log` | run.sh | 서버 종료 시 삭제 |
| `.env` | 사용자 | 영구 (gitignored) |
