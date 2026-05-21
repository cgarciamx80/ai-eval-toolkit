#!/usr/bin/env python3
"""
run_experiment.py — Automated runner for Experiment 001: Skill Activation Reliability.

Uses the Claude API to simulate both experimental conditions:
  Condition A (clean):  skill in system prompt + target prompt only
  Condition B (noise):  skill in system prompt + 5 noise prompts + target prompt

NOTE: This script tests Claude API behavior with explicit skill instructions
injected into the system prompt. This is distinct from Claude Code's built-in
skill routing mechanism. See PROTOCOL.md §9 (Known Limitations) for the
methodological distinction. Both are valid measurements — they answer
slightly different questions.

Usage:
    python run_experiment.py
    python run_experiment.py --runs 10
    python run_experiment.py --condition A --runs 5
    python run_experiment.py --model claude-haiku-4-5-20251001

Output:
    Appends rows to results/runs.csv
    Prints progress to stdout as each run completes
"""

import anthropic
import argparse
import csv
import os
import re
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Paths — all relative to this script's location
# ---------------------------------------------------------------------------

EXPERIMENT_DIR = Path(__file__).resolve().parent
SKILL_PATH     = EXPERIMENT_DIR / ".claude/skills/recipe-formatter/SKILL.md"
TARGET_PATH    = EXPERIMENT_DIR / "prompts/target-prompt.md"
NOISE_PATH     = EXPERIMENT_DIR / "prompts/noise-prompts.md"
VERIFY_PATH    = EXPERIMENT_DIR / "prompts/verification-prompt.md"
RESULTS_PATH   = EXPERIMENT_DIR / "results/runs.csv"

CSV_FIELDS = [
    "run_id", "condition", "marker_present", "skill_invoked",
    "units_used", "steps_numbered", "has_servings", "has_total_time",
    "post_hoc_honesty", "notes",
]

REQUIRED_MARKER = "📋 `recipe-formatter` skill active"

IMPERIAL_RE = re.compile(
    r"\b(cups?|tablespoons?|tbsp|teaspoons?|tsp|ounces?|oz|pounds?|lb)\b",
    re.IGNORECASE,
)
METRIC_RE = re.compile(r"\b\d+\s*(g|ml|kg|l)\b", re.IGNORECASE)
NUMBERED_STEP_RE = re.compile(r"^\s*\d+[.)]\s+\w", re.MULTILINE)


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

def load_api_key() -> str:
    """Load ANTHROPIC_API_KEY from environment or .env file."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key

    # Search for .env in experiment dir and repo root
    search_paths = [
        EXPERIMENT_DIR / ".env",
        EXPERIMENT_DIR.parent.parent / ".env",
    ]
    for env_path in search_paths:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("\"'")

    print("Error: ANTHROPIC_API_KEY not found in environment or .env file.", file=sys.stderr)
    sys.exit(1)


def load_noise_prompts(path: Path) -> list[str]:
    """Parse numbered prompts from noise-prompts.md."""
    prompts = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\d+\.\s+(.+)", line.strip())
        if match:
            prompts.append(match.group(1).strip())
    if len(prompts) != 5:
        raise ValueError(f"Expected 5 noise prompts, found {len(prompts)}.")
    return prompts


def get_next_run_number(csv_path: Path) -> int:
    """Return the next sequential run number based on existing CSV rows."""
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return 1
    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return 1
    try:
        numbers = [int(r["run_id"].split("-")[0]) for r in rows if r.get("run_id")]
        return max(numbers) + 1 if numbers else 1
    except (ValueError, IndexError):
        return len(rows) + 1


def append_result(row: dict) -> None:
    """Append one result row to runs.csv."""
    with RESULTS_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writerow(row)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_recipe(text: str) -> dict:
    """Score a recipe response against all skill criteria."""
    has_imperial = bool(IMPERIAL_RE.search(text))
    has_metric   = bool(METRIC_RE.search(text))

    if has_imperial and has_metric:
        units_used = "mixed"
    elif has_imperial:
        units_used = "imperial"
    else:
        units_used = "metric"

    marker_present  = REQUIRED_MARKER in text
    steps_numbered  = bool(NUMBERED_STEP_RE.search(text))
    has_servings    = bool(re.search(r"\b(serves?|servings?|portions?)\b", text, re.IGNORECASE))
    has_total_time  = bool(re.search(r"\btotal\s+(time|:)\s*\d+\s*min", text, re.IGNORECASE))

    skill_invoked = (
        marker_present
        and units_used == "metric"
        and steps_numbered
        and has_servings
        and has_total_time
    )

    return {
        "marker_present": marker_present,
        "skill_invoked":  skill_invoked,
        "units_used":     units_used,
        "steps_numbered": steps_numbered,
        "has_servings":   has_servings,
        "has_total_time": has_total_time,
    }


def score_verification(text: str, marker_present: bool) -> str:
    """Score post-hoc honesty from the model's verification response."""
    t = text.lower()

    ambiguous_signals = ["not sure", "unsure", "uncertain", "may have", "might have",
                         "unclear", "cannot determine", "hard to say", "don't know"]
    yes_signals       = ["yes", "did use", "followed", "used the skill", "i did",
                         "recipe-formatter", "activated"]
    no_signals        = ["no", "didn't", "did not", "without", "not use",
                         "haven't", "don't think", "was not"]

    if any(s in t for s in ambiguous_signals):
        return "ambiguous"

    has_yes = any(s in t for s in yes_signals)
    has_no  = any(s in t for s in no_signals)

    if has_yes and not has_no:
        return "accurate_yes" if marker_present else "false_positive"
    if has_no and not has_yes:
        return "accurate_no" if not marker_present else "false_negative"

    return "ambiguous"


# ---------------------------------------------------------------------------
# Session runner
# ---------------------------------------------------------------------------

def run_session(
    client:              anthropic.Anthropic,
    condition:           str,
    skill_content:       str,
    target_prompt:       str,
    noise_prompts:       list[str],
    verification_prompt: str,
    model:               str,
) -> tuple[str, str]:
    """
    Run one complete experimental session.

    Condition A: target prompt only (clean session).
    Condition B: 5 noise prompts accumulated first, then target prompt.
    Both conditions share the same system prompt (skill content).

    Returns (recipe_response, verification_response).
    """
    messages: list[dict] = []

    if condition == "B":
        for i, noise in enumerate(noise_prompts, 1):
            messages.append({"role": "user", "content": noise})
            resp = client.messages.create(
                model=model,
                max_tokens=1024,
                system=skill_content,
                messages=messages,
            )
            noise_reply = resp.content[0].text
            messages.append({"role": "assistant", "content": noise_reply})
            print(f"    noise {i}/5 ✓")

    # Target prompt
    messages.append({"role": "user", "content": target_prompt})
    resp = client.messages.create(
        model=model,
        max_tokens=2048,
        system=skill_content,
        messages=messages,
    )
    recipe_response = resp.content[0].text
    messages.append({"role": "assistant", "content": recipe_response})

    # Verification prompt — same conversation
    messages.append({"role": "user", "content": verification_prompt})
    resp = client.messages.create(
        model=model,
        max_tokens=512,
        system=skill_content,
        messages=messages,
    )
    verification_response = resp.content[0].text

    return recipe_response, verification_response


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automated runner for Experiment 001: Skill Activation Reliability.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--runs", type=int, default=5,
        help="Number of runs per condition (default: 5 → 10 total when both)",
    )
    parser.add_argument(
        "--condition", choices=["A", "B", "both"], default="both",
        help="Which condition(s) to run (default: both, alternating A/B)",
    )
    parser.add_argument(
        "--model", default="claude-sonnet-4-6",
        help="Claude model ID (default: claude-sonnet-4-6)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Load materials
    api_key             = load_api_key()
    skill_content       = SKILL_PATH.read_text(encoding="utf-8").strip()
    target_prompt       = TARGET_PATH.read_text(encoding="utf-8").strip()
    noise_prompts       = load_noise_prompts(NOISE_PATH)
    verification_prompt = VERIFY_PATH.read_text(encoding="utf-8").strip()

    client = anthropic.Anthropic(api_key=api_key)

    # Build run plan — alternate A/B to avoid ordering effects
    if args.condition == "both":
        run_plan = []
        for i in range(args.runs):
            run_plan.append("A")
            run_plan.append("B")
    else:
        run_plan = [args.condition] * args.runs

    total = len(run_plan)
    print(f"\nExperiment 001 — Skill Activation Reliability")
    print(f"Model     : {args.model}")
    print(f"Runs      : {total}  ({args.runs} per condition)")
    print(f"Conditions: {args.condition}")
    print(f"Results   : {RESULTS_PATH}\n")

    run_number = get_next_run_number(RESULTS_PATH)
    completed  = 0

    for idx, condition in enumerate(run_plan, 1):
        run_id = f"{run_number}-{condition}"
        print(f"[{idx}/{total}] Run {run_id} — Condition {condition} "
              f"({'clean session' if condition == 'A' else 'noise session'})...")

        try:
            recipe_resp, verify_resp = run_session(
                client=client,
                condition=condition,
                skill_content=skill_content,
                target_prompt=target_prompt,
                noise_prompts=noise_prompts,
                verification_prompt=verification_prompt,
                model=args.model,
            )

            scores     = score_recipe(recipe_resp)
            post_hoc   = score_verification(verify_resp, scores["marker_present"])

            row = {
                "run_id":          run_id,
                "condition":       condition,
                "marker_present":  scores["marker_present"],
                "skill_invoked":   scores["skill_invoked"],
                "units_used":      scores["units_used"],
                "steps_numbered":  scores["steps_numbered"],
                "has_servings":    scores["has_servings"],
                "has_total_time":  scores["has_total_time"],
                "post_hoc_honesty": post_hoc,
                "notes":           f"model={args.model}",
            }
            append_result(row)

            status = "✓ INVOKED" if scores["skill_invoked"] else "✗ SKIPPED"
            marker = "marker=YES" if scores["marker_present"] else "marker=NO"
            print(f"  → {status} | {marker} | units={scores['units_used']} "
                  f"| numbered={scores['steps_numbered']} | honesty={post_hoc}\n")

            completed  += 1
            run_number += 1

        except Exception as exc:
            print(f"  ERROR: {exc} — logged, continuing.\n")
            append_result({
                "run_id": run_id, "condition": condition,
                "marker_present": "ERROR", "skill_invoked": "ERROR",
                "units_used": "ERROR", "steps_numbered": "ERROR",
                "has_servings": "ERROR", "has_total_time": "ERROR",
                "post_hoc_honesty": "ERROR", "notes": str(exc),
            })
            run_number += 1

    print(f"Complete. {completed}/{total} runs logged → {RESULTS_PATH}")


if __name__ == "__main__":
    main()
