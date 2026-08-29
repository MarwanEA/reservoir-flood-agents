"""
Re-runs ONLY Agent 6 (Decision Synthesis) and patches its section into the
existing outputs/run_log.json in place - everything else in the file
(Agents 1-5's numeric outputs, QA, DGM comparison data) is left untouched.

Agents 1-5 are re-run first (fast, local, deterministic, no network calls -
they only read the already-fetched CSVs/JSON) purely to reconstruct the
in-memory state Agent 6 needs as input. This is NOT a full pipeline re-run
in the sense of re-fetching or re-deriving anything; it produces bit-identical
Agents 1-5 output to what's already in run_log.json.

Use once `claude login` has been re-confirmed to work in this environment.
"""
import datetime
import json

from agents import agent1_perception, agent2_forecasting, agent3_routing
from agents import agent4_downstream_risk, agent5_regulatory, agent6_synthesis
from agents import config
from run_case_study import RUN_LOG_PATH, _json_default


def main():
    print("Reconstructing pipeline state (Agents 1-5, local/deterministic)...")
    state = {}
    state = agent1_perception.run(state)
    if not state["qa_report"]["passed"]:
        raise RuntimeError("QA failed - cannot backfill Agent 6 against invalid data.")
    state = agent2_forecasting.run(state)
    state = agent3_routing.run(state)
    state = agent4_downstream_risk.run(state)
    state = agent5_regulatory.run(state)

    print("Calling Agent 6 (claude -p headless)...")
    state = agent6_synthesis.run(state)

    with open(RUN_LOG_PATH, encoding="utf-8") as f:
        run_log = json.load(f)

    run_log["agent6_decision_synthesis"] = {
        "provenance": "LLM-GENERATED (Claude Code headless) narration of the DERIVED numeric outputs "
                       "above - or LLM_SYNTHESIS_FAILED if the call could not complete",
        "backfilled_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "by_lead_time": state["synthesis"],
    }

    with open(RUN_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(run_log, f, indent=2, default=_json_default)

    n_ok = sum(1 for v in state["synthesis"].values() if v["status"] == "ok")
    print(f"\nPatched {RUN_LOG_PATH}: {n_ok}/{len(state['synthesis'])} lead times got real rationale text.")


if __name__ == "__main__":
    main()
