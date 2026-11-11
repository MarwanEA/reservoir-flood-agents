"""
Agent 6 - Decision Synthesis & Explanation.

The only LLM-based agent in the pipeline (Agents 3-5 are rule-based by
design). Takes the pipeline's actual numeric outputs - Agent 1's QA status,
Agent 2's inflow estimate, Agent 3's routing trajectory, Agent 4's risk
flags, Agent 5's regulatory checks - for a given lead time, and calls
Claude Code headless to produce a plain-language, operator-facing rationale.

Calls `claude -p "<prompt>" --model <MODEL> --effort <EFFORT> --safe-mode --output-format json`
via subprocess (NOT --bare, which would skip subscription login and require
separate API billing). The model and effort are pinned below and recorded,
with the model ID the CLI reports having used, in every run_log entry. The
CLI has no temperature option, so temperature is recorded as "CLI default".
--safe-mode (documented in `claude --help`) starts the child session with all
user customizations disabled (hooks, installed plugins, CLAUDE.md, skills,
MCP servers, output styles) while auth and model selection work normally, so
the output does not depend on the operator's personal Claude Code setup.
If the call fails for any reason (auth, timeout, non-zero exit), the failure
is recorded but does NOT crash the pipeline - the rest of the run_log
(Agents 1-5's real numeric outputs) remains valid and usable even if the LLM
narration step is unavailable.
"""
import datetime
import json
import shutil
import subprocess

from . import config

MODEL = "claude-opus-5-5"   # passed as --model
EFFORT = "high"             # passed as --effort (documented: low, medium, high, xhigh, max)
TEMPERATURE = "CLI default"  # claude -p exposes no temperature setting
ISOLATION = "--safe-mode"    # no user hooks/plugins/CLAUDE.md/skills in the child session; recorded as agent6_isolation


def _build_prompt(lead_time: str, summary: dict) -> str:
    return f"""You are writing an operator-facing decision rationale for a reservoir flood-operations
decision-support pipeline, case study: Oued El Makhazine dam, Loukkos basin, Morocco,
Jan-Feb 2026 crisis. This is a research prototype for a conference paper, not live operations.

Write 3-5 short plain-language sentences explaining what the pipeline observed and would have
recommended, for the {lead_time} forecast lead time. Use ONLY the numbers given below. Do not
invent any number not listed here. Clearly distinguish CONFIRMED (real, official) figures from
DERIVED (this pipeline's own simplified estimate) figures if you mention both - do not blend them
into a single claim.

Data QA status: {summary['qa_status']}

DERIVED (Agent 2 inflow estimate, Agent 3 routing simulation, illustrative only):
- Peak simulated inflow at this lead time: {summary['peak_inflow_m3s']:.1f} m3/s on {summary['peak_inflow_date']}
- Peak simulated reservoir fill reached: {summary['peak_fill_percent']:.1f}% of nominal capacity
- Peak simulated outflow (anticipatory policy): {summary['peak_outflow_anticipatory_m3s']:.1f} m3/s
- Peak simulated outflow (reactive policy): {summary['peak_outflow_reactive_m3s']:.1f} m3/s
- Agent 4 rate-of-rise elevated-risk flag: {summary['first_flag_summary']}
- Agent 5 regulatory violations: {summary['regulatory_violations']}

CONFIRMED (dam_parameters.json, official/press-sourced, for context only - NOT what this lead
time's simulation produced):
- Nominal capacity: {config.NOMINAL_CAPACITY_MM3} Mm3
- Real peak fill: 166.4% on 2026-02-10
- Real peak inflow: 3210 m3/s on 2026-01-28
- Real peak controlled outflow: 878 m3/s on 2026-02-09

Write the rationale now."""


def cli_version() -> str:
    try:
        proc = subprocess.run([shutil.which("claude") or "claude", "--version"],
                              capture_output=True, text=True, encoding="utf-8", timeout=30)
        return proc.stdout.strip() or "unknown"
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return f"unknown ({e})"


def _call_claude_headless(prompt: str) -> dict:
    claude_path = shutil.which("claude") or "claude"
    try:
        proc = subprocess.run(
            [claude_path, "-p", prompt, "--model", MODEL, "--effort", EFFORT, ISOLATION, "--output-format", "json"],
            capture_output=True, text=True, encoding="utf-8", timeout=300,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"ok": False, "error": f"subprocess failed to run claude CLI: {e}"}

    if not proc.stdout.strip():
        return {"ok": False, "error": f"empty stdout from claude CLI (exit={proc.returncode}); stderr={proc.stderr[:500]}"}

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"could not parse claude CLI JSON output: {e}; raw={proc.stdout[:500]}"}

    if payload.get("is_error"):
        return {"ok": False, "error": f"claude CLI returned an error: {payload.get('result')}", "raw": payload}

    return {"ok": True, "text": payload.get("result", ""), "raw": payload}


def synthesize(lead_time: str, summary: dict, cli_ver: str) -> dict:
    """One Agent 6 call for one lead time, returned as a run_log entry with provenance fields."""
    result = _call_claude_headless(_build_prompt(lead_time, summary))
    raw = result.get("raw") or {}
    used = sorted((raw.get("modelUsage") or {}).keys())  # model IDs the CLI reports having used
    entry = {
        "status": "ok" if result["ok"] else "failed",
        "rationale" if result["ok"] else "error": result["text"] if result["ok"] else result["error"],
        "numeric_summary": summary,
        "agent6_model_requested": MODEL,
        "agent6_model_id_returned": used[0] if len(used) == 1 else used,
        "agent6_effort": EFFORT,
        "agent6_temperature": TEMPERATURE,
        "agent6_isolation": ISOLATION,
        "agent6_cli_version": cli_ver,
        "agent6_run_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "agent6_session_id": raw.get("session_id"),
    }
    if result["ok"]:
        print(f"[Agent 6: Decision Synthesis] {lead_time}: rationale generated ({len(result['text'])} chars, "
              f"model returned: {entry['agent6_model_id_returned']}).")
    else:
        print(f"[Agent 6: Decision Synthesis] {lead_time}: LLM call FAILED ({result['error']}). "
              f"Numeric pipeline outputs for this lead time remain valid; only the narration is missing.")
    return entry


def run(state: dict) -> dict:
    routing_results = state["routing_results"]
    inflow_df = state["inflow_df"]
    risk_first_flags = state["risk_first_flags"]
    regulatory_df = state["regulatory_df"]
    qa_status = "PASSED" if state["qa_report"]["passed"] else "FAILED"

    syntheses = {}
    cli_ver = cli_version()
    for lead_time in config.LEAD_TIMES:
        inflow_col = f"inflow_m3s_{lead_time}"
        peak_idx = inflow_df[inflow_col].idxmax()
        peak_inflow = inflow_df[inflow_col].iloc[peak_idx]
        peak_inflow_date = str(inflow_df["date"].iloc[peak_idx])

        anticip = routing_results[lead_time]["anticipatory"]
        react = routing_results[lead_time]["reactive"]

        flag = risk_first_flags.get(lead_time)
        first_flag_summary = (
            f"first triggered for valid-date {flag['valid_date']} "
            f"({flag['ratio_vs_baseline']}x baseline inflow), information available on "
            f"{flag['flag_raised_date']} ({flag['lead_offset_days']}d lead)"
            if flag else "no rate-of-rise flag triggered in this run window"
        )

        reg_lead = regulatory_df[regulatory_df["lead_time"] == lead_time]
        n_violations = int((reg_lead["outflow_ceiling_violation"] | reg_lead["outflow_floor_violation"]
                             | reg_lead["ramp_rate_violation"]).sum())

        summary = {
            "qa_status": qa_status,
            "peak_inflow_m3s": float(peak_inflow),
            "peak_inflow_date": peak_inflow_date,
            "peak_fill_percent": float(anticip["fill_percent"].max()),
            "peak_outflow_anticipatory_m3s": float(anticip["outflow_m3s"].max()),
            "peak_outflow_reactive_m3s": float(react["outflow_m3s"].max()),
            "first_flag_summary": first_flag_summary,
            "regulatory_violations": f"{n_violations} rows with a constraint violation",
        }

        syntheses[lead_time] = synthesize(lead_time, summary, cli_ver)

    state["synthesis"] = syntheses
    return state
