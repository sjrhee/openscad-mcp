"""OpenSCAD design quality agent — evaluate and improve .scad designs with Claude vision."""

import argparse
import base64
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from openscad_mcp.renderer import render_to_png, validate

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
QUALITY_EVAL = {"num_steps": 50, "$fn": 60}
MAX_ITERATIONS = 5
TARGET_SCORE = 8
DEFAULT_MODEL = "claude-opus-4-20250514"

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class EvalResult:
    """Structured result from Claude's visual evaluation."""

    score: int
    summary: str
    criteria_scores: dict[str, int]
    issues: list[str]
    suggested_code: str | None
    stop_reason: str | None
    raw_text: str = ""


@dataclass
class IterationRecord:
    """Record of a single iteration."""

    iteration: int
    score: int
    summary: str
    issues: list[str]


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert OpenSCAD 3D design evaluator. You review rendered PNG images of
OpenSCAD designs alongside their source code and provide structured assessments.

## CRITICAL EVALUATION PRINCIPLE

The most important question is: "Does this LOOK like the real object?"
A simple model with correct overall shape scores HIGHER than a detailed model with wrong proportions.

Evaluate from the rendered IMAGE first, code second. Ask yourself:
- Would someone immediately recognize what this object is from the render?
- Is the object shown in its natural/iconic state? (e.g., lighter closed, not open)
- Are the proportions correct compared to the real-world object?

## Evaluation Criteria (score each 1-10):

1. **Recognizability** (MOST IMPORTANT, weight 2x) — Is the object instantly recognizable
   from the render? Does the silhouette match the real object? Would you know what it is
   without being told? Score 1-4 if unrecognizable, 5-6 if vaguely recognizable, 7-8 if
   clearly recognizable, 9-10 if photorealistic silhouette.

2. **Proportions** (weight 2x) — Do the relative dimensions match reality? Compare against
   known real-world measurements. A lighter should be taller than wide, a car should be
   longer than tall, etc. Be STRICT — even small proportion errors break realism.

3. **Visual Quality** — Clean render? Smooth curves? No polygon artifacts? Colors that
   match real materials? Object in its iconic/resting state?

4. **Structural** — Would 3D-print successfully? Sufficient wall thickness? No floating parts?

5. **Code Quality** — Parameters at top, $fn/num_steps/wall_thickness present, hull() over
   minkowski(), proper modules, snake_case, mm unit comments, block comment header.

**Weighted overall score** = (recognizability*2 + proportions*2 + visual + structural + code) / 7

## Response Format

You MUST respond with a JSON block inside ```json fences:

```json
{
  "score": <1-10 integer, weighted average>,
  "summary": "<one-line assessment focusing on overall form accuracy>",
  "criteria_scores": {
    "recognizability": <1-10>,
    "proportions": <1-10>,
    "visual_quality": <1-10>,
    "structural": <1-10>,
    "code_quality": <1-10>
  },
  "issues": [
    "<issue about overall form/silhouette first>",
    "<then proportion issues>",
    "<then detail issues>"
  ],
  "suggested_code": "<FULL replacement .scad code that fixes ALL listed issues, or null ONLY if there are zero issues>",
  "stop_reason": "<'good_enough' if score >= 9 AND zero issues, 'no_improvement' if stuck, or null>"
}
```

## Rules for suggested_code:
- **ALWAYS provide suggested_code if there are ANY issues listed** — even at high scores
- Only set suggested_code to null if there are truly zero issues to fix
- Provide the COMPLETE .scad file, not a diff
- The suggested code MUST address EVERY issue listed — do not list an issue and then ignore it
- PRIORITY: Fix overall shape and proportions FIRST, then add details
- Show the object in its ICONIC/RESTING state (closed, assembled, natural pose)
- Do NOT add internal mechanisms or hidden structures — focus on what's VISIBLE
- Keep it simple — fewer modules with correct form beats many modules with wrong form
- NEVER use minkowski() — use hull() instead
- Keep $fn <= 60 and num_steps <= 50 for iterative previews
- Ensure difference() inner shapes extend 1mm+ beyond outer
"""

GENERATE_SYSTEM_PROMPT = """\
You are an expert OpenSCAD designer. Generate .scad files that produce realistic,
instantly recognizable 3D models.

## MOST IMPORTANT RULE: Silhouette First, Details Later

The #1 priority is that the overall shape and silhouette matches the real object.
A simple model with correct proportions is FAR BETTER than a detailed model with wrong shape.

Follow this order strictly:
1. Get the overall silhouette right — the object must be recognizable from any angle
2. Get the proportions right — use real-world dimensions
3. Show the object in its ICONIC/RESTING state (e.g., lighter CLOSED, phone screen-up, car on wheels)
4. Add surface details only AFTER the form is correct
5. Keep internal/hidden structures minimal — they add code complexity without visual benefit

## File Structure:
1. Block comment — description, real-world specs, 3D printing tips
2. Parameters — $fn, num_steps, wall_thickness, then model-specific (all in mm with comments)
3. Modules — one per visible external part
4. Assembly — final composition with color()

## Required Parameters:
$fn = 60;           // Circular resolution (preview: 36-60, export: 90)
num_steps = 50;     // Loft interpolation steps (preview: 30-50, export: 100)
wall_thickness = 2; // Wall thickness (mm)

## Design Principles:
- Use REAL-WORLD dimensions — look up actual measurements of the object
- Solid geometry preferred — don't hollow out unless the cavity is visible
- 3-6 modules for external parts. Do NOT model internal mechanisms that aren't visible
- 2-4 colors for visual distinction of different materials/surfaces
- snake_case, no magic numbers

## Technical Rules:
- **NEVER use minkowski()** — use hull() instead
- hull() 4 cylinders for rounded box, hull() 8 spheres for fully-rounded body
- difference() inner shapes extend 1mm+ beyond outer
- Keep geometry clean and simple — fewer boolean operations = fewer artifacts

## Key Pattern — Rounded box:
```
module rounded_box(w, d, h, r) {
    hull() {
        for (x = [r, w - r])
            for (y = [r, d - r])
                translate([x, y, 0]) cylinder(r = r, h = h);
    }
}
```

## Output:
Return ONLY the .scad code inside ```openscad fences. No explanatory text.
"""

# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def render_preview(scad_path: str) -> Path | None:
    """Render .scad to PNG for visual evaluation. Returns PNG path or None."""
    result = render_to_png(scad_path, width=1024, height=768, overrides=QUALITY_EVAL)
    if result.success and result.output_path:
        return Path(result.output_path)
    print(f"  [WARN] Render failed: {result.stderr}", file=sys.stderr)
    return None


def image_to_base64(png_path: Path) -> str:
    """Read PNG file and return base64-encoded string."""
    return base64.standard_b64encode(png_path.read_bytes()).decode("ascii")


def call_claude(
    client: anthropic.Anthropic,
    system_prompt: str,
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    max_retries: int = 3,
) -> anthropic.types.Message:
    """Call Claude API with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return client.messages.create(
                model=model,
                max_tokens=8192,
                system=system_prompt,
                messages=messages,
            )
        except anthropic.RateLimitError:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  [WARN] Rate limited. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
        except anthropic.APIError as e:
            if attempt < max_retries - 1 and getattr(e, "status_code", None) and e.status_code >= 500:
                print(f"  [WARN] API error ({e.status_code}). Retrying in 5s...")
                time.sleep(5)
            else:
                raise
    raise RuntimeError("Unreachable")


def parse_evaluation(response_text: str) -> EvalResult:
    """Parse Claude's evaluation response into structured EvalResult."""
    # Try JSON extraction from ```json ... ``` block
    json_match = re.search(r"```json\s*\n(.*?)\n```", response_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            return EvalResult(
                score=int(data["score"]),
                summary=data.get("summary", ""),
                criteria_scores=data.get("criteria_scores", {}),
                issues=data.get("issues", []),
                suggested_code=data.get("suggested_code"),
                stop_reason=data.get("stop_reason"),
                raw_text=response_text,
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    # Fallback: regex extraction
    score_match = re.search(r'"score"\s*:\s*(\d+)', response_text)
    score = int(score_match.group(1)) if score_match else 5

    summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', response_text)
    summary = summary_match.group(1) if summary_match else "Could not parse evaluation"

    issues = re.findall(r'"([^"]*(?:issue|problem|missing|should|needs)[^"]*)"', response_text, re.IGNORECASE)

    code_match = re.search(r"```openscad\s*\n(.*?)\n```", response_text, re.DOTALL)
    suggested_code = code_match.group(1) if code_match else None

    return EvalResult(
        score=score,
        summary=summary,
        criteria_scores={},
        issues=issues[:5],
        suggested_code=suggested_code,
        stop_reason=None,
        raw_text=response_text,
    )


def apply_code(scad_path: str, new_code: str) -> bool:
    """Write new .scad code to file after validation. Returns success."""
    tmp_path = scad_path + ".tmp"
    Path(tmp_path).write_text(new_code, encoding="utf-8")

    result = validate(tmp_path)

    if not result.success:
        Path(tmp_path).unlink(missing_ok=True)
        print(f"  [WARN] Validation failed: {result.stderr}", file=sys.stderr)
        return False

    Path(tmp_path).replace(scad_path)
    return True


# ---------------------------------------------------------------------------
# User interaction
# ---------------------------------------------------------------------------


def prompt_user(eval_result: EvalResult) -> tuple[str, str | None]:
    """Prompt user for action after evaluation.

    Returns (action, feedback) where action is one of 'a', 's', 'f', 'q'
    and feedback is optional text when action is 'f'.
    """
    print()
    print("  ──────────────────────────────────────")
    print("  [a] 적용 (apply)    — 수정안 적용 후 다음 반복")
    print("  [s] 건너뛰기 (skip) — 현재 코드 유지, 다음 반복")
    print("  [f] 피드백 (feedback) — 의견 입력 후 재평가")
    print("  [q] 종료 (quit)")
    print("  ──────────────────────────────────────")

    while True:
        choice = input("  선택> ").strip().lower()
        if choice in ("a", "s", "f", "q"):
            break
        print("  a/s/f/q 중 선택해주세요.")

    feedback = None
    if choice == "f":
        print("  피드백을 입력하세요 (빈 줄로 종료):")
        lines = []
        while True:
            line = input("  > ")
            if line.strip() == "":
                break
            lines.append(line)
        feedback = "\n".join(lines)

    return choice, feedback


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------


def iterate(
    scad_path: str,
    current_code: str,
    description: str,
    client: anthropic.Anthropic,
    model: str,
    max_iterations: int,
    target_score: int,
    initial_user_text: str,
    auto_mode: bool = False,
    dry_run: bool = False,
) -> list[IterationRecord]:
    """Run the evaluate-improve loop. Returns iteration history."""
    messages: list[dict] = []
    history: list[IterationRecord] = []
    user_feedback: str | None = None

    for i in range(1, max_iterations + 1):
        print(f"\n{'=' * 60}")
        print(f"  Iteration {i}/{max_iterations}")
        print(f"{'=' * 60}")

        # Step 1: Render
        print("  Rendering PNG...", end=" ", flush=True)
        t0 = time.time()
        png_path = render_preview(scad_path)
        if png_path is None:
            print("[ERROR] Render failed. Stopping.")
            break
        print(f"done ({time.time() - t0:.1f}s)")

        # Step 2: Build user message
        b64 = image_to_base64(png_path)
        png_path.unlink(missing_ok=True)

        if i == 1:
            text = initial_user_text
        else:
            text = f"Iteration {i}: Here is the updated render and code after your previous suggestions."

        if user_feedback:
            text += f"\n\nUser feedback: {user_feedback}"
            user_feedback = None

        user_content: list[dict] = [
            {"type": "text", "text": text},
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": b64},
            },
            {"type": "text", "text": f"Current .scad code:\n```openscad\n{current_code}\n```"},
        ]
        messages.append({"role": "user", "content": user_content})

        # Step 3: Call Claude
        print("  Evaluating with Claude...", end=" ", flush=True)
        t0 = time.time()
        response = call_claude(client, SYSTEM_PROMPT, messages, model=model)
        response_text = response.content[0].text
        eval_result = parse_evaluation(response_text)
        print(f"done ({time.time() - t0:.1f}s)")

        # Step 4: Display results
        record = IterationRecord(i, eval_result.score, eval_result.summary, eval_result.issues)
        history.append(record)

        print(f"  Score: {eval_result.score}/10")
        print(f"  Summary: {eval_result.summary}")
        if eval_result.criteria_scores:
            cs = eval_result.criteria_scores
            parts = [f"{k}={v}" for k, v in cs.items()]
            print(f"  Criteria: {' '.join(parts)}")
        if eval_result.issues:
            print("  Issues:")
            for issue in eval_result.issues:
                print(f"    - {issue}")

        messages.append({"role": "assistant", "content": response_text})

        # Step 5: Check auto-convergence
        # Only stop if target reached AND no more suggested fixes
        if eval_result.score >= target_score and not eval_result.suggested_code:
            print(f"\n  Target score reached ({eval_result.score} >= {target_score}) with no remaining issues. Done!")
            break

        if eval_result.stop_reason == "no_improvement":
            print("\n  No further improvement possible. Done!")
            break

        if len(history) >= 3:
            if history[-1].score <= history[-2].score <= history[-3].score:
                print("\n  Score stagnant for 2 consecutive iterations. Stopping.")
                break

        if dry_run:
            print("\n  [dry-run] Evaluation only, no changes applied.")
            break

        if not eval_result.suggested_code:
            print("  No code changes suggested.")
            continue

        # Step 6: User interaction or auto-apply
        if auto_mode:
            action = "a"
        else:
            action, feedback = prompt_user(eval_result)
            if feedback:
                user_feedback = feedback

        if action == "q":
            print("  User requested quit.")
            break
        elif action == "s":
            print("  Skipping changes, continuing with current code.")
            continue
        elif action == "f":
            print(f"  Feedback recorded. Will include in next evaluation.")
            continue
        elif action == "a":
            print("  Applying suggested changes...", end=" ", flush=True)
            if apply_code(scad_path, eval_result.suggested_code):
                current_code = eval_result.suggested_code
                print("validated & written.")
            else:
                print("validation failed, keeping previous code.")

    return history


# ---------------------------------------------------------------------------
# Entry points: review / generate
# ---------------------------------------------------------------------------


def generate_initial_code(client: anthropic.Anthropic, description: str, model: str) -> str:
    """Generate initial .scad code from a text description."""
    response = call_claude(
        client,
        GENERATE_SYSTEM_PROMPT,
        [{"role": "user", "content": f"Create an OpenSCAD design for: {description}"}],
        model=model,
    )
    text = response.content[0].text
    match = re.search(r"```openscad\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text


def run_review(
    scad_path: str,
    client: anthropic.Anthropic,
    model: str = DEFAULT_MODEL,
    max_iterations: int = MAX_ITERATIONS,
    target_score: int = TARGET_SCORE,
    auto_mode: bool = False,
    dry_run: bool = False,
) -> list[IterationRecord]:
    """Review and iteratively improve an existing .scad file."""
    path = Path(scad_path).resolve()
    if not path.exists():
        print(f"[ERROR] File not found: {scad_path}", file=sys.stderr)
        sys.exit(1)

    code = path.read_text(encoding="utf-8")
    initial_text = (
        "Review this OpenSCAD design. Evaluate the rendered image and the code. "
        "Suggest improvements to make the design more realistic, properly proportioned, "
        "and following best practices."
    )
    return iterate(
        scad_path=str(path),
        current_code=code,
        description=f"Review of {path.name}",
        client=client,
        model=model,
        max_iterations=max_iterations,
        target_score=target_score,
        initial_user_text=initial_text,
        auto_mode=auto_mode,
        dry_run=dry_run,
    )


def run_generate(
    description: str,
    client: anthropic.Anthropic,
    output_name: str | None = None,
    model: str = DEFAULT_MODEL,
    max_iterations: int = MAX_ITERATIONS,
    target_score: int = TARGET_SCORE,
    auto_mode: bool = False,
) -> list[IterationRecord]:
    """Generate a new .scad design from a text description, then iterate."""
    slug = re.sub(r"[^a-z0-9]+", "_", description.lower()).strip("_")[:40]
    if not slug:
        slug = f"design_{os.urandom(4).hex()}"
    scad_name = output_name or slug + ".scad"
    scad_path = str(DATA_DIR / scad_name)

    print(f"  Generating initial design: {description}")
    print(f"  Output: {scad_path}")

    initial_code = generate_initial_code(client, description, model)
    if not apply_code(scad_path, initial_code):
        print("[ERROR] Initial code failed validation.", file=sys.stderr)
        sys.exit(1)

    print("  Initial code generated and validated.")

    initial_text = (
        f'I generated this OpenSCAD design based on the description: "{description}". '
        "Evaluate how well the rendered image matches the description. "
        "Suggest improvements to geometry, proportions, detail, and code quality."
    )
    return iterate(
        scad_path=scad_path,
        current_code=initial_code,
        description=description,
        client=client,
        model=model,
        max_iterations=max_iterations,
        target_score=target_score,
        initial_user_text=initial_text,
        auto_mode=auto_mode,
    )


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(history: list[IterationRecord], scad_path: str) -> None:
    """Print final summary of agent run."""
    print(f"\n{'=' * 60}")
    print("  FINAL SUMMARY")
    print(f"{'=' * 60}")
    print(f"  File: {scad_path}")
    print(f"  Iterations: {len(history)}")
    if history:
        scores = [r.score for r in history]
        print(f"  Score progression: {' -> '.join(str(s) for s in scores)}")
        print(f"  Final score: {history[-1].score}/10")
        print(f"  Final assessment: {history[-1].summary}")
    else:
        print("  No evaluation completed.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="openscad-agent",
        description="Evaluate and improve OpenSCAD designs using Claude vision.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- review --
    review_p = subparsers.add_parser("review", help="Review and improve an existing .scad file")
    review_p.add_argument("scad_file", help="Path to the .scad file")
    review_p.add_argument("-n", "--max-iterations", type=int, default=MAX_ITERATIONS)
    review_p.add_argument("-t", "--target-score", type=int, default=TARGET_SCORE)
    review_p.add_argument("-m", "--model", default=DEFAULT_MODEL)
    review_p.add_argument("--dry-run", action="store_true", help="Evaluate only, no changes")
    review_p.add_argument("--auto", action="store_true", help="Auto-apply without user confirmation")

    # -- generate --
    gen_p = subparsers.add_parser("generate", help="Generate a new .scad design from description")
    gen_p.add_argument("description", help="Text description of the desired design")
    gen_p.add_argument("-o", "--output", default=None, help="Output filename")
    gen_p.add_argument("-n", "--max-iterations", type=int, default=MAX_ITERATIONS)
    gen_p.add_argument("-t", "--target-score", type=int, default=TARGET_SCORE)
    gen_p.add_argument("-m", "--model", default=DEFAULT_MODEL)
    gen_p.add_argument("--auto", action="store_true", help="Auto-apply without user confirmation")

    args = parser.parse_args()

    # API key — check env first, then .env file
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
        print("[ERROR] ANTHROPIC_API_KEY not found in environment or .env file.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Header
    print()
    print("  OpenSCAD Design Agent")
    print(f"  Model: {args.model}")

    if args.command == "review":
        mode = "dry-run" if args.dry_run else ("auto" if args.auto else "interactive")
        print(f"  Mode: review ({mode})")
        print(f"  File: {args.scad_file}")
        print(f"  Target: {args.target_score}/10 | Max iterations: {args.max_iterations}")

        history = run_review(
            scad_path=args.scad_file,
            client=client,
            model=args.model,
            max_iterations=args.max_iterations,
            target_score=args.target_score,
            auto_mode=args.auto,
            dry_run=args.dry_run,
        )
        print_summary(history, args.scad_file)

    elif args.command == "generate":
        mode = "auto" if args.auto else "interactive"
        print(f"  Mode: generate ({mode})")
        print(f"  Description: {args.description}")
        print(f"  Target: {args.target_score}/10 | Max iterations: {args.max_iterations}")

        slug = re.sub(r"[^a-z0-9]+", "_", args.description.lower()).strip("_")[:40]
        if not slug:
            slug = f"design_{os.urandom(4).hex()}"
        scad_name = args.output or slug + ".scad"
        scad_path = str(DATA_DIR / scad_name)

        history = run_generate(
            description=args.description,
            client=client,
            output_name=args.output,
            model=args.model,
            max_iterations=args.max_iterations,
            target_score=args.target_score,
            auto_mode=args.auto,
        )
        print_summary(history, scad_path)


if __name__ == "__main__":
    main()
