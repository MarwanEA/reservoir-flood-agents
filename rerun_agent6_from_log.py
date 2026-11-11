"""
Reruns ONLY Agent 6 for the four lead times, using the Agent 2-5 results
already stored in outputs/run_log.json (each entry's numeric_summary is
exactly the payload Agent 6's prompt is built from). Agents 1-5 are not run.

Uses the model and effort pinned in agents/agent6_synthesis.py. Per lead time
it writes the provenance fields agent6_model_requested,
agent6_model_id_returned, agent6_effort, agent6_temperature, agent6_isolation,
agent6_cli_version, agent6_run_timestamp_utc and agent6_session_id. The rationale
it replaces is kept under agent6_rationale_previous (provenance of the run that
wrote it under agent6_previous_run).

run_log.json is rewritten only if all four calls succeed, and only the
agent6_decision_synthesis block changes.
"""
import datetime
import json
import os

from agents import agent6_synthesis, config

RUN_LOG_PATH = os.path.join(config.OUTPUTS_DIR, "run_log.json")


def main():
    with open(RUN_LOG_PATH, encoding="utf-8") as f:
        log = json.load(f)
    old_block = log["agent6_decision_synthesis"]

    cli_ver = agent6_synthesis.cli_version()
    new_entries = {}
    for lead_time in config.LEAD_TIMES:
        old = old_block["by_lead_time"][lead_time]
        entry = agent6_synthesis.synthesize(lead_time, old["numeric_summary"], cli_ver)
        if entry["status"] != "ok":
            raise SystemExit(f"{lead_time} failed: {entry['error']}\nrun_log.json was NOT modified.")
        # the rationale being replaced becomes agent6_rationale_previous, with the provenance of the run that wrote it
        # (agent6_isolation None = run without isolation); an older previous, if any, is kept as agent6_rationale_before_previous
        entry["agent6_rationale_previous"] = old["rationale"]
        entry["agent6_previous_run"] = {"agent6_isolation": None,
                                        **{k: v for k, v in old.items() if k.startswith("agent6_") and k not in
                                           ("agent6_rationale_previous", "agent6_previous_run", "agent6_rationale_before_previous")}}
        if "agent6_rationale_previous" in old:
            entry["agent6_rationale_before_previous"] = old["agent6_rationale_previous"]
        new_entries[lead_time] = entry

    log["agent6_decision_synthesis"] = {
        **old_block,
        "agent6_rerun_note": "Rationales regenerated from the stored Agent 2-5 summaries with the pinned model "
                             "and CLI isolation (agent6_isolation) (Agents 1-5 not rerun); the replaced rationale is kept per "
                             "entry under agent6_rationale_previous, with its provenance under agent6_previous_run.",
        "agent6_rerun_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "by_lead_time": new_entries,
    }
    with open(RUN_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
    returned = {e["agent6_model_id_returned"] if isinstance(e["agent6_model_id_returned"], str)
                else tuple(e["agent6_model_id_returned"]) for e in new_entries.values()}
    print(f"\nPatched {RUN_LOG_PATH}: 4/4 lead times regenerated. Model ID(s) returned: {sorted(map(str, returned))}; "
          f"effort {agent6_synthesis.EFFORT}; CLI {cli_ver}.")


if __name__ == "__main__":
    main()
