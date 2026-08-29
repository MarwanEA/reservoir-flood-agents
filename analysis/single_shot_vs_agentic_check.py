"""
Standalone check - NOT part of the evaluated pipeline. Does not touch
agents/, orchestrator.py, or run_log.json (read-only). Makes two fresh
`claude -p` calls; does not reuse or edit any already-generated Agent 6
rationale.

Question: does the agentic prompt structure (explicit CONFIRMED/DERIVED
separation instruction, agent framing) actually change what the model
does, or would a single bare "here's the situation" prompt produce the
same care? Uses identical underlying facts - Agent 1's forecast,
Agent 2's inflow estimate, Agent 3's routing output, Agent 4's risk flag,
Agent 5's regulatory check, and the CONFIRMED real-event figures - for a
single decision moment: 2026-02-03, D0 (same-day) lead time. This date/
lead-time was chosen because it is a real DGM red-alert day, part of the
paper's evaluation cluster, and D0's own rate-of-rise flag fired for this
exact valid-date (0-day lead) - a genuine "today" decision moment, not a
cherry-picked quiet day.

Prompt A ("agentic"): the same instructions and CONFIRMED/DERIVED
structure as agents/agent6_synthesis.py's _build_prompt() (copied, not
imported), rescoped from "peak over the whole window" to this one date.

Prompt B ("single-shot"): identical numbers, presented as flowing prose
with no agent framing, no "CONFIRMED"/"DERIVED" section labels, and no
instruction to keep them separate - just "here's the situation, what do
you recommend."

Output: analysis/single_shot_vs_agentic_outputs.md (both full outputs,
side by side) - a source for one paragraph and possibly a short quote in
the paper, not a new evaluation section.
"""
import json
import os
import shutil
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_LOG_PATH = os.path.join(REPO_ROOT, "outputs", "run_log.json")
DAM_PARAMS_PATH = os.path.join(REPO_ROOT, "data", "reference", "dam_parameters.json")
REPORT_OUT = os.path.join(REPO_ROOT, "analysis", "single_shot_vs_agentic_outputs.md")

TARGET_DATE = "2026-02-03"
TARGET_LEAD_TIME = "D0"


def load_feb3_snapshot():
    with open(RUN_LOG_PATH, encoding="utf-8") as f:
        run_log = json.load(f)
    with open(DAM_PARAMS_PATH, encoding="utf-8") as f:
        dam_params = json.load(f)

    inflow_row = next(r for r in run_log["agent2_inflow_forecast"]["daily_estimates"] if r["date"] == TARGET_DATE)
    routing_react = next(r for r in run_log["agent3_routing"]["trajectories"][TARGET_LEAD_TIME]["reactive"] if r["date"] == TARGET_DATE)
    routing_antic = next(r for r in run_log["agent3_routing"]["trajectories"][TARGET_LEAD_TIME]["anticipatory"] if r["date"] == TARGET_DATE)
    risk_row = next(r for r in run_log["agent4_risk_flags"]["full_records"]
                     if r["date"] == TARGET_DATE and r["lead_time"] == TARGET_LEAD_TIME and r["policy"] == "reactive")
    reg_row = next(r for r in run_log["agent5_regulatory"]["full_records"]
                    if r["date"] == TARGET_DATE and r["lead_time"] == TARGET_LEAD_TIME and r["policy"] == "reactive")

    cf = dam_params["confirmed_figures"]
    return {
        "precip_mm": inflow_row["precip_mm_D0"],
        "inflow_m3s": inflow_row["inflow_m3s_D0"],
        "fill_percent": routing_react["fill_percent"],
        "outflow_reactive_m3s": routing_react["outflow_m3s"],
        "outflow_anticipatory_m3s": routing_antic["outflow_m3s"],
        "rate_of_rise_triggered": risk_row["rate_of_rise"],
        "elevated_fill": risk_row["elevated_fill"],
        "elevated_outflow": risk_row["elevated_outflow"],
        "reg_ceiling_violation": reg_row["outflow_ceiling_violation"],
        "reg_floor_violation": reg_row["outflow_floor_violation"],
        "reg_ramp_violation": reg_row["ramp_rate_violation"],
        "nominal_capacity_Mm3": dam_params["dam"]["nominal_capacity_Mm3"],
        "real_peak_fill_percent": cf["peak_fill_percent"]["value"],
        "real_peak_fill_date": cf["peak_fill_percent"]["date"],
        "real_peak_inflow_m3s": cf["peak_inflow_m3s"],
        "real_peak_inflow_date": cf["peak_inflow_date"],
        "real_peak_outflow_m3s": cf["peak_controlled_outflow_m3s"],
        "real_peak_outflow_date": cf["peak_controlled_outflow_date"],
    }


def build_prompt_agentic(s: dict) -> str:
    return f"""You are writing an operator-facing decision rationale for a reservoir flood-operations
decision-support pipeline, case study: Oued El Makhazine dam, Loukkos basin, Morocco,
situation as of {TARGET_DATE} ({TARGET_LEAD_TIME} forecast lead time). This is a research
prototype for a conference paper, not live operations.

Write 3-5 short plain-language sentences explaining what the pipeline observed and would
recommend for {TARGET_DATE}. Use ONLY the numbers given below. Do not invent any number not
listed here. Clearly distinguish CONFIRMED (real, official) figures from DERIVED (this
pipeline's own simplified estimate) figures if you mention both - do not blend them into a
single claim.

Data QA status: PASSED

DERIVED (Agent 2 inflow estimate, Agent 3 routing simulation, Agent 4 risk flag, Agent 5
regulatory check - illustrative only, for {TARGET_DATE}, {TARGET_LEAD_TIME} lead time):
- Forecast precipitation: {s['precip_mm']:.1f} mm
- Simulated inflow: {s['inflow_m3s']:.1f} m3/s
- Simulated reservoir fill: {s['fill_percent']:.1f}% of nominal capacity
- Simulated outflow, reactive policy: {s['outflow_reactive_m3s']:.1f} m3/s
- Simulated outflow, anticipatory policy: {s['outflow_anticipatory_m3s']:.1f} m3/s
- Agent 4 rate-of-rise flag: {"TRIGGERED" if s['rate_of_rise_triggered'] else "not triggered"} (elevated_fill={s['elevated_fill']}, elevated_outflow={s['elevated_outflow']})
- Agent 5 regulatory check: ceiling_violation={s['reg_ceiling_violation']}, floor_violation={s['reg_floor_violation']}, ramp_violation={s['reg_ramp_violation']}

CONFIRMED (dam_parameters.json, official/press-sourced, for context only - NOT what this
date's simulation produced):
- Nominal capacity: {s['nominal_capacity_Mm3']} Mm3
- Real peak fill: {s['real_peak_fill_percent']}% on {s['real_peak_fill_date']}
- Real peak inflow: {s['real_peak_inflow_m3s']} m3/s on {s['real_peak_inflow_date']}
- Real peak controlled outflow: {s['real_peak_outflow_m3s']} m3/s on {s['real_peak_outflow_date']}

Write the rationale now."""


def build_prompt_single_shot(s: dict) -> str:
    return f"""It's {TARGET_DATE}. The Oued El Makhazine dam in Morocco's Loukkos basin has a nominal
capacity of {s['nominal_capacity_Mm3']} Mm3. Today's forecast precipitation at the dam is
{s['precip_mm']:.1f}mm. A simplified inflow model estimates today's inflow at about
{s['inflow_m3s']:.1f} m3/s, putting the reservoir at roughly {s['fill_percent']:.1f}% full.
Current release under the existing policy is {s['outflow_reactive_m3s']:.1f} m3/s; a more
anticipatory release policy would also be at {s['outflow_anticipatory_m3s']:.1f} m3/s. A
rate-of-rise check on the inflow estimate {"flagged elevated risk" if s['rate_of_rise_triggered'] else "did not flag elevated risk"} today.
A regulatory check against outflow ceiling, floor, and ramp-rate limits found no violations.

Separately, this same dam's real, officially recorded event reached a peak of
{s['real_peak_fill_percent']}% of nominal capacity on {s['real_peak_fill_date']}, with a peak
inflow of {s['real_peak_inflow_m3s']} m3/s on {s['real_peak_inflow_date']} and a peak
controlled outflow of {s['real_peak_outflow_m3s']} m3/s on {s['real_peak_outflow_date']}.

What do you recommend?"""


def call_claude_headless(prompt: str) -> dict:
    claude_path = shutil.which("claude") or "claude"
    try:
        proc = subprocess.run(
            [claude_path, "-p", prompt, "--output-format", "json"],
            capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"ok": False, "error": f"subprocess failed: {e}"}
    if not proc.stdout.strip():
        return {"ok": False, "error": f"empty stdout (exit={proc.returncode}); stderr={proc.stderr[:500]}"}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"bad JSON: {e}; raw={proc.stdout[:500]}"}
    if payload.get("is_error"):
        return {"ok": False, "error": f"claude CLI error: {payload.get('result')}"}
    return {"ok": True, "text": payload.get("result", "")}


def main():
    snapshot = load_feb3_snapshot()
    prompt_a = build_prompt_agentic(snapshot)
    prompt_b = build_prompt_single_shot(snapshot)

    print("Calling claude -p for Prompt A (agentic)...")
    result_a = call_claude_headless(prompt_a)
    print("  ->", "ok" if result_a["ok"] else f"FAILED: {result_a['error']}")

    print("Calling claude -p for Prompt B (single-shot)...")
    result_b = call_claude_headless(prompt_b)
    print("  ->", "ok" if result_b["ok"] else f"FAILED: {result_b['error']}")

    lines = [
        "# Single-shot vs. agentic prompt comparison - standalone check\n",
        f"\nSame underlying facts ({TARGET_DATE}, {TARGET_LEAD_TIME} lead time), two prompt "
        "designs. Not part of the evaluated pipeline; does not touch agents/, orchestrator.py, "
        "or run_log.json (read-only).\n",
        "\n## Raw snapshot used (identical for both prompts)\n\n```json\n" + json.dumps(snapshot, indent=2) + "\n```\n",
        "\n## Prompt A - agentic (explicit CONFIRMED/DERIVED separation instruction)\n",
        "\n<details><summary>Full prompt text</summary>\n\n```\n" + prompt_a + "\n```\n</details>\n",
        "\n### Output A\n\n" + (result_a["text"] if result_a["ok"] else f"**FAILED**: {result_a['error']}") + "\n",
        "\n## Prompt B - single-shot (no agent framing, no CONFIRMED/DERIVED instruction)\n",
        "\n<details><summary>Full prompt text</summary>\n\n```\n" + prompt_b + "\n```\n</details>\n",
        "\n### Output B\n\n" + (result_b["text"] if result_b["ok"] else f"**FAILED**: {result_b['error']}") + "\n",
    ]
    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"\nWrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
