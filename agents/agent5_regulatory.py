"""
Agent 5 - Regulatory & Constraints (rule-based, not LLM-based).

Independent checks of Agent 3's routed trajectories against known
operating limits - deliberately re-derived from the raw trajectory rather
than trusting Agent 3's internal clipping, so this agent can catch a bug
in Agent 3 rather than just rubber-stamp it:

  1. outflow_ceiling: outflow must never exceed REGULATORY_MAX_OUTFLOW_M3S
     (878 m3/s, CONFIRMED real peak_controlled_outflow_m3s - the policy may
     not invent a release rate higher than what was actually achieved).
  2. outflow_floor: outflow must never drop below MIN_RELEASE_M3S (ASSUMED
     ecological/operational minimum).
  3. ramp_rate: day-over-day outflow change must stay within
     RAMP_RATE_LIMIT_M3S_PER_DAY (ASSUMED downstream-safety limit).
  4. evacuation_trigger: an illustrative recommendation flag (NOT an actual
     evacuation order) raised when critical_fill is active, for comparison
     against the CONFIRMED real evacuation count/date in dam_parameters.json.
"""
import pandas as pd

from . import config


def run(state: dict) -> dict:
    routing_results = state["routing_results"]
    risk_df = state["risk_df"]

    records = []
    for lead_time in config.LEAD_TIMES:
        for policy in ["reactive", "anticipatory"]:
            traj = routing_results[lead_time][policy].reset_index(drop=True)
            prev_outflow = None
            for i, row in traj.iterrows():
                outflow = row["outflow_m3s"]
                ceiling_violation = outflow > config.REGULATORY_MAX_OUTFLOW_M3S + 1e-6
                floor_violation = outflow < config.MIN_RELEASE_M3S - 1e-6
                ramp = abs(outflow - prev_outflow) if prev_outflow is not None else 0.0
                ramp_violation = ramp > config.RAMP_RATE_LIMIT_M3S_PER_DAY
                prev_outflow = outflow

                critical_row = risk_df[
                    (risk_df["date"] == str(row["date"])) & (risk_df["lead_time"] == lead_time)
                    & (risk_df["policy"] == policy)
                ]
                critical_fill = bool(critical_row["critical_fill"].iloc[0]) if len(critical_row) else False

                records.append({
                    "date": str(row["date"]), "lead_time": lead_time, "policy": policy,
                    "outflow_m3s": round(outflow, 2), "ramp_m3s_per_day": round(ramp, 2),
                    "outflow_ceiling_violation": bool(ceiling_violation),
                    "outflow_floor_violation": bool(floor_violation),
                    "ramp_rate_violation": bool(ramp_violation),
                    "evacuation_trigger_recommended": critical_fill,
                })

    reg_df = pd.DataFrame(records)
    n_ceiling = int(reg_df["outflow_ceiling_violation"].sum())
    n_floor = int(reg_df["outflow_floor_violation"].sum())
    n_ramp = int(reg_df["ramp_rate_violation"].sum())
    n_evac = int(reg_df["evacuation_trigger_recommended"].sum())

    print(f"[Agent 5: Regulatory & Constraints] checked {len(reg_df)} rows. "
          f"ceiling_violations={n_ceiling} (limit={config.REGULATORY_MAX_OUTFLOW_M3S} m3/s, CONFIRMED), "
          f"floor_violations={n_floor} (limit={config.MIN_RELEASE_M3S} m3/s, ASSUMED), "
          f"ramp_violations={n_ramp} (limit={config.RAMP_RATE_LIMIT_M3S_PER_DAY} m3/s/day, ASSUMED), "
          f"evacuation_trigger_rows={n_evac} (illustrative recommendation only; "
          f"CONFIRMED real evacuations=108423 as_of 2026-02-04, per dam_parameters.json).")
    if n_ceiling or n_floor:
        print("  WARNING: Agent 3's own clipping should make ceiling/floor violations impossible - "
              "investigate if either count above is nonzero.")

    state["regulatory_df"] = reg_df
    return state
