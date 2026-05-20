# ai-eval-toolkit

A public collection of reproducible LLM evaluation experiments documenting 
real-world Claude behavior in production contexts.

**Author:** Carlos Garcia — [Holteck](https://holteck.com)  
**Focus:** Field observations of LLM behavior under controlled conditions,  
designed to be reproduced independently and compared across sessions.

---

## What this is

Each experiment in this repo tests a specific, observable aspect of LLM 
behavior. The goal is not to expose failures — it is to document patterns 
with enough rigor that others can reproduce the conditions and verify the 
findings.

Every experiment is self-contained in its own folder under `experiments/`.  
Each has its own README, a full PROTOCOL, stimuli, and a results log.

---

## Experiments

| # | Title | Status |
|---|-------|--------|
| 001 | [Skill Activation Reliability](experiments/001-skill-activation-reliability/README.md) | In progress |

---

## Methodology principles

- Stimuli are fixed and versioned — exact prompts are committed, not paraphrased
- Results are logged in CSV — one row per run, reproducible by anyone
- Observations are documented before analysis — raw data first
- No cherry-picking — all runs are logged, including null results

---

*Part of the [AI-Human Interaction Observatory](https://github.com/cgarciamx80/ai-human-observatory) research project.*
