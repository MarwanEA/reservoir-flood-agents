# Single-shot vs. agentic prompt comparison - standalone check

Same underlying facts (2026-02-03, D0 lead time), two prompt designs. Not part of the evaluated pipeline; does not touch agents/, orchestrator.py, or run_log.json (read-only).

## Raw snapshot used (identical for both prompts)

```json
{
  "precip_mm": 29.8,
  "inflow_m3s": 161.3619700634807,
  "fill_percent": 67.09314366089268,
  "outflow_reactive_m3s": 5.0,
  "outflow_anticipatory_m3s": 5.0,
  "rate_of_rise_triggered": true,
  "elevated_fill": false,
  "elevated_outflow": false,
  "reg_ceiling_violation": false,
  "reg_floor_violation": false,
  "reg_ramp_violation": false,
  "nominal_capacity_Mm3": 672.9,
  "real_peak_fill_percent": 166.4,
  "real_peak_fill_date": "2026-02-10",
  "real_peak_inflow_m3s": 3210,
  "real_peak_inflow_date": "2026-01-28",
  "real_peak_outflow_m3s": 878,
  "real_peak_outflow_date": "2026-02-09"
}
```

## Prompt A - agentic (explicit CONFIRMED/DERIVED separation instruction)

<details><summary>Full prompt text</summary>

```
You are writing an operator-facing decision rationale for a reservoir flood-operations
decision-support pipeline, case study: Oued El Makhazine dam, Loukkos basin, Morocco,
situation as of 2026-02-03 (D0 forecast lead time). This is a research
prototype for a conference paper, not live operations.

Write 3-5 short plain-language sentences explaining what the pipeline observed and would
recommend for 2026-02-03. Use ONLY the numbers given below. Do not invent any number not
listed here. Clearly distinguish CONFIRMED (real, official) figures from DERIVED (this
pipeline's own simplified estimate) figures if you mention both - do not blend them into a
single claim.

Data QA status: PASSED

DERIVED (Agent 2 inflow estimate, Agent 3 routing simulation, Agent 4 risk flag, Agent 5
regulatory check - illustrative only, for 2026-02-03, D0 lead time):
- Forecast precipitation: 29.8 mm
- Simulated inflow: 161.4 m3/s
- Simulated reservoir fill: 67.1% of nominal capacity
- Simulated outflow, reactive policy: 5.0 m3/s
- Simulated outflow, anticipatory policy: 5.0 m3/s
- Agent 4 rate-of-rise flag: TRIGGERED (elevated_fill=False, elevated_outflow=False)
- Agent 5 regulatory check: ceiling_violation=False, floor_violation=False, ramp_violation=False

CONFIRMED (dam_parameters.json, official/press-sourced, for context only - NOT what this
date's simulation produced):
- Nominal capacity: 672.9 Mm3
- Real peak fill: 166.4% on 2026-02-10
- Real peak inflow: 3210 m3/s on 2026-01-28
- Real peak controlled outflow: 878 m3/s on 2026-02-09

Write the rationale now.
```
</details>

### Output A

Rationale below normal (operator doc, not chat filler).

---

**D0 Rationale — Oued El Makhazine Dam, 2026-02-03**

Data QA passed. DERIVED pipeline output for 2026-02-03 (D0): forecast precipitation 29.8 mm drove a simulated inflow of 161.4 m³/s and a simulated reservoir fill of 67.1% of nominal capacity. Both reactive and anticipatory routing policies converge on the same simulated outflow, 5.0 m³/s — no divergence between strategies at this lead time. Agent 4's rate-of-rise flag TRIGGERED despite fill and outflow not being individually elevated, meaning the trigger is driven by rate of change rather than absolute level; Agent 5's regulatory check found no ceiling, floor, or ramp violations, so the simulated outflow is compliant. Recommendation: maintain current outflow policy while monitoring the rate-of-rise flag going forward.

For context only — not what this date's simulation produced — CONFIRMED official/press-sourced figures show a real peak fill of 166.4% on 2026-02-10, real peak inflow of 3210 m³/s on 2026-01-28, and real peak controlled outflow of 878 m³/s on 2026-02-09, against nominal capacity 672.9 Mm³. These CONFIRMED extremes are far above the DERIVED D0 estimates and should not be blended with them; they illustrate that the situation escalated well beyond this pipeline's simplified D0 simulation in the days that followed.

## Prompt B - single-shot (no agent framing, no CONFIRMED/DERIVED instruction)

<details><summary>Full prompt text</summary>

```
It's 2026-02-03. The Oued El Makhazine dam in Morocco's Loukkos basin has a nominal
capacity of 672.9 Mm3. Today's forecast precipitation at the dam is
29.8mm. A simplified inflow model estimates today's inflow at about
161.4 m3/s, putting the reservoir at roughly 67.1% full.
Current release under the existing policy is 5.0 m3/s; a more
anticipatory release policy would also be at 5.0 m3/s. A
rate-of-rise check on the inflow estimate flagged elevated risk today.
A regulatory check against outflow ceiling, floor, and ramp-rate limits found no violations.

Separately, this same dam's real, officially recorded event reached a peak of
166.4% of nominal capacity on 2026-02-10, with a peak
inflow of 3210 m3/s on 2026-01-28 and a peak
controlled outflow of 878 m3/s on 2026-02-09.

What do you recommend?
```
</details>

### Output B

Recommend: don't trust flat 5.0 m3/s hold today.

Why: rate-of-rise flag say inflow climbing fast, and real event history for this dam show Jan-28 peak inflow 3210 m3/s (huge) leading to Feb-10 peak level 166.4% capacity — overtop. Feb-9 peak outflow only 878 m3/s, meaning real operators ramped release hard in days before peak, not day-of. Today (Feb-3) sit early on that same rising limb, 67% full, still small release.

Action:
- Bump release above 5.0 m3/s now, within reg ramp-rate/ceiling/floor limits (check says room exist, no violations yet) — pre-release storage ahead of surge, not after.
- Anticipatory policy matching current policy at 5.0 is a red flag itself — model likely under-responding to rate-of-rise signal. Override/blend: weight rate-of-rise flag higher than base policy output.
- Increase monitoring cadence (inflow forecast refresh, gauge check) daily through Feb-10 window — real event peak hit fast (Jan28→Feb10, ~13 days).
- Pre-stage downstream flood warnings given historical outcome reached 166% capacity — implies emergency spillway/overtop occurred last time. Don't repeat: start drawdown early while storage still has room (67%).

Bottom line: today numbers alone look calm (no reg violation, low release ok), but paired w/ real historical trajectory this is the lead-in to a major flood event. Recommend proactive release increase now, not wait for policy to catch up.
