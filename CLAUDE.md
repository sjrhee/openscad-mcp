# openscad-mcp CLAUDE.md

## 프로젝트 개요

OpenSCAD 3D 모델을 생성·렌더링·웹으로 미리보기하는 도구.

- **서버**: FastAPI (port 8000) — REST API + React 정적 파일 서빙
- **프론트엔드**: React + Three.js — 3D 웹 뷰어
- **Python 환경**: `.venv/` (프로젝트 루트)
- **관리 스크립트**: `run.sh` — 설치/시작/종료/빌드 통합
- **프로덕션**: `./run.sh start` → 단일 서버(8000)
- **개발**: `./run.sh dev` → FastAPI(8000) + Vite HMR(3000)

---

## 디렉토리 구조

```
openscad-mcp/
├── run.sh                       # 프로젝트 관리 스크립트
├── data/                        # .scad 디자인 파일 및 렌더링 결과물
│   ├── *.scad                   # OpenSCAD 디자인 소스
│   ├── *_preview.png            # 렌더링된 PNG 미리보기
│   └── *.stl                    # 3D 프린팅용 STL
├── bin/                         # OpenSCAD 실행 환경
│   ├── openscad                 # 래퍼 스크립트 (LD_LIBRARY_PATH 설정)
│   ├── OpenSCAD-x86_64.AppImage # OpenSCAD 바이너리
│   └── lib/                     # 번들된 OpenGL 라이브러리
├── src/openscad_mcp/
│   ├── renderer.py              # OpenSCAD CLI 래퍼 (PNG/STL 렌더링)
│   ├── web_api.py               # FastAPI 서버 (REST API + 정적 파일 서빙)
│   └── server.py                # MCP 서버
├── web/                         # React 프론트엔드
│   ├── vite.config.js           # Vite 설정 (dev 프록시 포함)
│   ├── dist/                    # 프로덕션 빌드 출력
│   └── src/
│       ├── App.jsx              # 메인 UI (파일 드롭다운, 버튼)
│       ├── StlViewer.jsx        # Three.js 3D 뷰어 (스케일 바, 바운딩 박스)
│       ├── api/openscad.js      # HTTP 클라이언트 (API 호출 래퍼)
│       └── hooks/useFileWatcher.js  # 파일 변경 감지 (2초 폴링)
├── .run/                        # 런타임 (PID, 로그) — gitignored
└── .claude/launch.json          # MCP 서버 실행 설정
```

---

## 환경 설정 및 실행

### 관리 스크립트 (`run.sh`)

```bash
./run.sh setup     # venv 생성, 패키지 설치, OpenSCAD 다운로드
./run.sh start     # 프론트엔드 빌드 + 서버 시작 (port 8000)
./run.sh stop      # 모든 서버 종료
./run.sh dev       # 개발 모드: 백엔드(8000) + Vite HMR(3000)
./run.sh restart   # 재시작
./run.sh status    # 서버 상태 확인
./run.sh build     # 프론트엔드 프로덕션 빌드
```

### 수동 실행 (참고)

```bash
# 백엔드
.venv/bin/python -m uvicorn src.openscad_mcp.web_api:app --host 0.0.0.0 --port 8000

# 프론트엔드
cd web && npx vite --port 3000
```

OpenSCAD 실행 파일: `bin/openscad` (프로젝트 내 AppImage + 번들 라이브러리)

---

## 디자인 작업 워크플로우

사용자가 3D 디자인을 설명하면:
1. 표현이 부족하거나 모호한 부분은 **보충 질문**을 해서 요구사항을 명확히 한다
   - 예: 치수, 두께, 각도, 단면 형상, 연결 방식 등
2. 요구사항이 확정되면 `.scad` 파일을 `data/`에 생성한다
3. 웹 뷰어(localhost:8000)에서 3D로 확인할 수 있도록 안내한다

---

## 디자인 작업 절차

### 1. .scad 파일 작성 → `data/` 에 저장

**파일 네이밍**: `{설명}.scad`
**파일 템플릿** (파이프/전환 형태):

```openscad
wall_thickness = 2;
num_steps = 50;   // 미리보기: 50, 고품질 출력: 100
$fn = 60;         // 미리보기: 60, 고품질 출력: 90

module lofted_solid(r0, r1, len, steps) {
    for (i = [0 : steps - 1]) {
        t0 = i / steps; t1 = (i + 1) / steps;
        a0 = r0 + (r1 - r0) * t0;
        a1 = r0 + (r1 - r0) * t1;
        hull() {
            translate([0, 0, t0 * len]) cylinder(r = a0, h = 0.01);
            translate([0, 0, t1 * len]) cylinder(r = a1, h = 0.01);
        }
    }
}
```

**성능 주의**: `minkowski()` 연산은 높은 `$fn` 에서 기하급수적으로 느려짐. 가능하면 `hull()` 기반 접근 사용.

### 2. PNG 미리보기 + STL 렌더링

```bash
.venv/bin/python -c "
from src.openscad_mcp.renderer import render_to_png, render_to_stl
scad = 'data/파일명.scad'
print(render_to_png(scad, 'data/파일명_preview.png'))
print(render_to_stl(scad, 'data/파일명.stl'))
"
```

### 3. 웹 뷰어로 3D 확인

`./run.sh start`로 서버 실행 후 `http://localhost:8000` 접속.

웹 UI에서:
1. 드롭다운에서 `.scad` 파일 선택 (새 파일은 드롭다운 클릭 시 자동 갱신)
2. **3D View** 버튼 클릭 → Three.js 인터랙티브 3D 확인
   - 줌 연동 동적 스케일 바 (좌하단)
   - 바운딩 박스 치수 표시 (우하단)
3. **Preview PNG** 버튼 → 정적 PNG 확인
4. **Download STL** 버튼 → 고품질 STL 다운로드

---

## 렌더링 품질 프리셋

| 용도 | num_steps | $fn | 소요 시간 |
|------|-----------|-----|-----------|
| 웹 미리보기 (3D View) | 30 | 36 | ~5초 |
| PNG 미리보기 | 100 | 60 | ~30초 |
| STL 최종 출력 | 100 | 90 | ~1~2분 |

---

## 기존 디자인 목록

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
| `agent_zippo_lighter.scad` | 에이전트 생성 지포 라이터 v1 |
| `agent_zippo_lighter_v2.scad` | 에이전트 생성 지포 라이터 v2 |
| `agent_zippo_lighter_v3.scad` | 에이전트 생성 지포 라이터 v3 |

---

## API 엔드포인트 (백엔드 port 8000)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/health` | 서버 상태 확인 |
| GET | `/api/files` | `data/` 내 .scad 파일 목록 |
| GET | `/api/files/status` | 파일별 수정 시각 (폴링용 변경 감지) |
| POST | `/api/validate` | .scad 문법 검사 |
| POST | `/api/render/png` | PNG 렌더링 |
| POST | `/api/render/stl` | STL 렌더링 (`quality`: `preview` / `export`) |
