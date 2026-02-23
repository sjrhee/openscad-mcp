# openscad-mcp CLAUDE.md

## 프로젝트 개요

OpenSCAD 3D 모델을 생성·렌더링·웹으로 미리보기하는 도구.

- **백엔드**: FastAPI (port 8000) — OpenSCAD CLI 래퍼
- **프론트엔드**: Vite + React (port 3000) — 3D 웹 뷰어
- **Python 환경**: `.venv/` (프로젝트 루트)

---

## 디렉토리 구조

```
openscad-mcp/
├── data/                        # .scad 디자인 파일 및 렌더링 결과물
│   ├── *.scad                   # OpenSCAD 디자인 소스
│   ├── *_preview.png            # 렌더링된 PNG 미리보기
│   └── *.stl                    # 3D 프린팅용 STL
├── src/openscad_mcp/
│   ├── renderer.py              # OpenSCAD CLI 래퍼 (PNG/STL 렌더링)
│   ├── web_api.py               # FastAPI 서버
│   └── server.py                # MCP 서버
├── web/                         # Vite + React 프론트엔드
│   └── src/
│       ├── App.jsx              # 메인 UI (파일 입력, 버튼)
│       └── StlViewer.jsx        # Three.js 3D 뷰어
└── .claude/launch.json          # 서버 실행 설정
```

---

## 환경 설정 (최초 1회)

```bash
# venv 생성
python -m venv .venv

# 패키지 설치 (백엔드)
.venv/Scripts/pip install -e .

# 패키지 설치 (프론트엔드)
cd web && npm install
```

OpenSCAD 실행 파일 위치: `C:\Program Files\OpenSCAD\openscad.exe`

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

### 2. PNG 미리보기 + STL 렌더링

```python
# .venv 활성화 후 실행
from src.openscad_mcp.renderer import render_to_png, render_to_stl

scad = 'data/파일명.scad'
render_to_png(scad, 'data/파일명_preview.png', width=1024, height=768)
render_to_stl(scad, 'data/파일명.stl')
```

또는 Python 스크립트로:

```bash
.venv/Scripts/python -c "
from src.openscad_mcp.renderer import render_to_png, render_to_stl
scad = 'data/파일명.scad'
print(render_to_png(scad, 'data/파일명_preview.png'))
print(render_to_stl(scad, 'data/파일명.stl'))
"
```

### 3. 웹 뷰어로 3D 확인

`preview_start` 도구로 두 서버 실행:
- `fastapi-backend` (port 8000)
- `vite-frontend` (port 3000)

웹 UI에서:
1. 입력란에 `.scad` 절대 경로 입력 (예: `D:\Work\openscad-mcp\data\파일명.scad`)
2. **3D View** 버튼 클릭 → Three.js로 인터랙티브 3D 확인
3. **Preview PNG** 버튼 → 정적 PNG 확인
4. **Download STL** 버튼 → 고품질 STL 다운로드

---

## 렌더링 품질 프리셋

| 용도 | num_steps | $fn | 소요 시간 |
|------|-----------|-----|-----------|
| 웹 미리보기 (3D View) | 30 | 36 | ~5초 |
| PNG 미리보기 | 50 | 60 | ~20초 |
| STL 최종 출력 | 100 | 90 | ~1~2분 |

---

## 기존 디자인 목록

| 파일 | 설명 |
|------|------|
| `circle_to_ellipse_transition_pipe.scad` | 원형 Ø50mm → 평타원 80×10mm, 길이 150mm |
| `50_to_100_transition_pipe.scad` | 원형 Ø50mm → 원형 Ø100mm, 양끝 10mm 평탄, 길이 150mm |

---

## API 엔드포인트 (백엔드 port 8000)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/health` | 서버 상태 확인 |
| POST | `/api/validate` | .scad 문법 검사 |
| POST | `/api/render/png` | PNG 렌더링 |
| POST | `/api/render/stl` | STL 렌더링 (`quality`: preview / export) |
