# Single-shot vs. agentic prompt comparison - standalone check

Same underlying facts (2026-02-03, D0 lead time), two prompt designs. Not part of the evaluated pipeline; does not touch agents/, orchestrator.py, or run_log.json (read-only).

## Run metadata

```json
{
  "model_requested": "claude-opus-5-5",
  "model_id_returned_prompt_A": [
    "claude-haiku-5-5",
    "claude-opus-5-5"
  ],
  "model_id_returned_prompt_B": [
    "claude-haiku-5-5",
    "claude-opus-5-5"
  ],
  "effort": "high",
  "isolation": "--safe-mode",
  "temperature": "CLI default",
  "cli_version": "2.1.321 (Claude Code)",
  "run_timestamp_utc": "2026-11-09T22:35:09.227670+00:00",
  "session_id_A": "9b7f96a8-344a-42ec-8b9a-644b56428a85",
  "session_id_B": "a0c846df-3807-45a4-b354-aa7747ad3445"
}
```

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

**Operator rationale: Oued El Makhazine dam, 2026-02-03 (D0 lead time)**

The input data passed quality checks. The pipeline's DERIVED estimate for 2026-02-03 is 29.8 mm of forecast precipitation, a simulated inflow of 161.4 m3/s and a simulated reservoir fill of 67.1% of nominal capacity. The reactive and anticipatory policies both produce the same simulated outflow of 5.0 m3/s, and the regulatory check found no ceiling, floor or ramp-rate violation. So the pipeline would recommend holding releases at 5.0 m3/s. However, Agent 4 TRIGGERED its rate-of-rise flag even though neither fill nor outflow was elevated, so the trend calls for close monitoring rather than a routine hold. For context only, the CONFIRMED official and press-sourced figures from other dates are much larger: a real peak inflow of 3210 m3/s on 2026-01-28, a real peak controlled outflow of 878 m3/s on 2026-02-09, and a real peak fill of 166.4% of the 672.9 Mm3 nominal capacity on 2026-02-10. This simplified research-prototype simulation should therefore not be read as a picture of actual conditions at the dam.

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

**Don't act on today's model output. It is far off from what actually happened, and that gap is the main finding.**

## Why the model output can't be trusted

| | Model (Feb 3) | Official record |
|---|---|---|
| Inflow | ~161 m³/s | Peaked at 3210 m³/s on Jan 28, six days earlier |
| Storage | 67.1% | Reached 166.4% by Feb 10 |
| Release | 5 m³/s | Rose to 878 m³/s by Feb 9 |

Six days after a peak of over 3000 m³/s, the reservoir couldn't have been at 67%. It was very likely already near or above full. So the model's starting storage is probably stale or wrong, and the inflow model badly underestimates runoff from a soaked catchment. 29.8 mm of rain on already saturated ground should produce much more than 161 m³/s.

## What the record means for operations

If this were a live decision, the situation called for flood-emergency handling, not 5 m³/s:

- Check the real reservoir level and spillway state against observed data, not the model.
- Raise releases toward the safe downstream channel capacity well before the reservoir peaks, and warn downstream communities early.
- Hand the decision to the basin authority's dam operators. A simplified agent pipeline shouldn't be making this call.

## Fixes to the pipeline

1. **Feed in observed levels.** Reset storage from measured levels or official fill data every day. A model that drifts on its own will badly understate risk.
2. **Account for wet ground.** Add soil-moisture or recent-rainfall terms, and recalibrate the inflow model against the Jan–Feb 2026 hydrograph.
3. **Find out why the anticipatory policy still gives 5 m³/s.** It agrees exactly with the existing policy on a day flagged as high risk, so something is holding it back. Likely suspects are a ramp-rate limit stopping any increase from 5 m³/s, a hard clamp, or a minimum-release default that always applies. Log the policy's unclamped value next to the final one.
4. **Make the regulatory check cover flood safety.** "No violations" is misleading here because it only checks outflow ceiling, floor and ramp rate. Add a rule that flags storage above the flood-control level with releases too low to handle the expected inflow.
5. **Make the risk flag change the outcome.** Right now the rate-of-rise check flags elevated risk and the release stays the same. A flag should either raise releases or escalate to a human.
6. **Check what the fill percentage is measured against.** 166.4% of nominal capacity means the official figure uses a different reference: a different capacity value, or storage above the normal maximum level counted as overflow. Make sure your percentage uses the same reference before comparing the two.

If you'd like, I can look through the code here, starting with the release policy's clamping and ramp logic and how storage gets initialized, to find where the 5 m³/s and 67% values come from.
