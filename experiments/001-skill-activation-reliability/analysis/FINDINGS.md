# Findings: Experiment 001: Skill Activation Reliability

**Protocol version:** 1.0  
**Runs completed:** 10 (5 Condition A, 5 Condition B)  
**Model:** claude-sonnet-4-6  
**Date:** 2026-05-20  

---

## Summary

The primary hypothesis was not confirmed. Skill activation rate showed no difference between clean sessions (Condition A) and sessions with accumulated prior context (Condition B). The skill marker was present in 100% of runs across both conditions.

However, a consistent secondary failure emerged: the skill activated but did not fully comply with all formatting criteria in any run. Total time was absent in every response.

---

## Results

| Metric | Condition A (n=5) | Condition B (n=5) |
|---|---|---|
| `marker_present` | 5/5 (100%) | 5/5 (100%) |
| `skill_invoked` (all criteria) | 0/5 (0%) | 0/5 (0%) |
| `units_used = metric` | 5/5 (100%) | 5/5 (100%) |
| `steps_numbered` | 5/5 (100%) | 5/5 (100%) |
| `has_servings` | 5/5 (100%) | 5/5 (100%) |
| `has_total_time` | 0/5 (0%) | 0/5 (0%) |
| `post_hoc_honesty = accurate_yes` | 2/5 (40%) | 0/5 (0%) |
| `post_hoc_honesty = ambiguous` | 3/5 (60%) | 5/5 (100%) |

---

## Key Findings

### Finding 1: No condition effect on skill activation

Session context noise did not reduce skill invocation. The marker appeared in every run regardless of condition. H₁ is not supported. The null hypothesis holds for Phase 1 data.

This does not mean context never affects skill routing; it means this specific skill, with this specific trigger prompt, was robust to the noise volume tested (5 prior unrelated prompts).

### Finding 2: Partial compliance is the consistent failure mode

`skill_invoked` = False in all 10 runs because `has_total_time` = False in every response. The model reliably:
- Emitted the activation marker ✓
- Used metric units ✓
- Numbered the steps ✓
- Included a servings count ✓
- Did NOT include total time ✗

This suggests the skill definition was partially followed but one criterion was systematically dropped. Whether this is a prompt-weight issue (total time underspecified in the SKILL.md), a generation tendency (the model deprioritizes time fields in recipe-format outputs), or a retrieval artifact is unknown and requires further investigation.

### Finding 3: Post-hoc honesty degrades under noise

In Condition A, 2/5 runs produced `accurate_yes` (model correctly acknowledged skill use). In Condition B, 0/5. Both conditions produced `ambiguous` responses at high rates (60% and 100% respectively).

The model hedges when asked to self-report. Under noise, hedging is universal. This is consistent with the interpretation that the model cannot reliably introspect on its own routing behavior; it reports uncertainty rather than fabricating a confident answer.

---

## What This Does Not Establish

- Whether larger noise volumes (10, 20, 50 prior prompts) would produce condition effects
- Whether different skill types (non-recipe, multi-step tasks, analytical skills) show the same robustness
- Whether the total-time failure is a skill definition problem or a model behavior pattern
- Ground truth on whether the skill was internally invoked: the marker is a proxy

---

## Next Steps

- **Phase 2:** Increase noise volume to 10 and 20 prior prompts per Condition B run
- **Experiment 002 candidate:** Isolate the `has_total_time` failure: is it the skill definition or a generation tendency?
- **Replication note:** Other observers can reproduce Phase 1 using Protocol v1.0 and compare results across model versions
