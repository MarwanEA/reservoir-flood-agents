"""
Runs the full six-agent pipeline over the 2026-01-14 to 2026-02-08 crisis
window and writes outputs/run_log.json.

Every top-level section of run_log.json is tagged CONFIRMED, DERIVED, or
ASSUMED per the provenance rule in data/reference/dam_parameters.json - see
each section's "provenance" field.
"""
import datetime
import json

import numpy as np
import pandas as pd

from agents import config
from orchestrator import run_pipeline

RUN_LOG_PATH = f"{config.OUTPUTS_DIR}/run_log.json"


def _json_default(o):
    if isinstance(o, (pd.Timestamp, datetime.date, datetime.datetime)):
        return str(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if hasattr(o, "to_dict"):
        return o.to_dict(orient="records")
    raise TypeError(f"not JSON serializable: {type(o)}")


def _rate_of_rise_episodes(risk_df: pd.DataFrame) -> dict:
    """All rate-of-rise trigger episodes per lead time (not just the first) -
    policy-independent, so dedupe on policy=='reactive' arbitrarily."""
    episodes = {}
    for lead_time in config.LEAD_TIMES:
        rows = risk_df[(risk_df["lead_time"] == lead_time) & (risk_df["policy"] == "reactive")
                        & (risk_df["rate_of_rise"])]
        offset = config.LEAD_TIME_OFFSET_DAYS[lead_time]
        ep_list = []
        for _, row in rows.iterrows():
            valid_date = pd.Timestamp(row["date"])
            flag_raised_date = valid_date - pd.Timedelta(days=offset)
            ep_list.append({
                "valid_date": row["date"],
                "flag_raised_date": str(flag_raised_date.date()),
                "lead_offset_days": offset,
                "inflow_m3s": row["inflow_m3s"],
            })
        episodes[lead_time] = ep_list
    return episodes


def main():
    print("=" * 70)
    print(f"Running full pipeline: {config.RUN_START_DATE} to {config.RUN_END_DATE}")
    print("=" * 70)

    state = run_pipeline()

    episodes = _rate_of_rise_episodes(state["risk_df"])

    run_log = {
        "run_metadata": {
            "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "window_start": config.RUN_START_DATE,
            "window_end": config.RUN_END_DATE,
            "dam": "Oued El Makhazine, Loukkos basin, Morocco",
        },
        "data_qa": {
            "provenance": "PIPELINE OUTPUT (Agent 1)",
            **state["qa_report"],
        },
        "confirmed_figures": {
            "provenance": "CONFIRMED - data/reference/dam_parameters.json, verbatim",
            **state["dam_params"],
        },
        "dgm_bulletin_trail": {
            "provenance": "CONFIRMED (press-sourced) - data/reference/dgm_bulletin_trail.json, verbatim, "
                           "ground truth for the evaluation section below",
            **state["dgm_bulletins"],
        },
        "design_decisions": [
            {
                "id": "rate_of_rise_primary_trigger",
                "made_in_response_to": "disclosed limitation, surfaced after first full pipeline run - "
                                        "NOT the original design",
                "rationale": (
                    "Agent 3's routing, forced by Agent 2's inflow estimates, tops out at ~78% simulated "
                    "fill across all lead times - far below the CONFIRMED real peak (159%). Absolute "
                    "fill/outflow thresholds calibrated to real capacity therefore never fire and would "
                    "not be a fair test of the pipeline's timing behavior. Two disclosed factors "
                    "contribute to that ~15x inflow-magnitude gap: (1) Agent 2's rainfall-runoff "
                    "transform (SCS-CN + single-tank routing) is an uncalibrated, planning-level "
                    "approximation - no basin-specific hydrograph data was available to fit it; "
                    "(2) the forcing data itself: this project independently confirmed gfs_seamless "
                    "underestimates observed rainfall at this site - for 2026-02-04, the D0 forecast was "
                    "20.9mm vs. 49.9mm actually observed (ERA5, archive-api), i.e. the forecast captured "
                    "roughly 42% of the observed total. See data/raw/daily_comparison_loukkos_jan-feb2026.csv. "
                    "Given both factors, Agent 4 adopted rate-of-rise (inflow vs. its own trailing 3-day "
                    "mean) as the PRIMARY elevated-risk signal - scale-independent, and standard real-world "
                    "flood early-warning practice for exactly this situation. Absolute-threshold rules are "
                    "still computed and logged every run for transparency (see agent4_risk / "
                    "agent5_regulatory below) even though they currently show 0 crossings."
                ),
                "evidence": {
                    "gfs_forecast_2026-02-04_mm": 20.9,
                    "era5_observed_2026-02-04_mm": 49.9,
                    "forecast_as_fraction_of_observed": round(20.9 / 49.9, 3),
                    "source_file": "data/raw/daily_comparison_loukkos_jan-feb2026.csv",
                },
            },
        ],
        "agent2_inflow_forecast": {
            "provenance": "DERIVED/ILLUSTRATIVE - simplified SCS-CN + linear-reservoir transform, "
                           "see agents/agent2_forecasting.py and assumed params in agents/config.py",
            "daily_estimates": state["inflow_df"].assign(date=lambda d: d["date"].astype(str)),
        },
        "agent3_routing": {
            "provenance": "DERIVED/ILLUSTRATIVE - rule-based mass balance, forced by Agent 2 output. "
                           f"initial_fill_fraction={config.INITIAL_FILL_FRACTION} [ASSUMED, no ground truth "
                           "for 2026-01-14 pre-crisis storage]",
            "trajectories": {
                lead_time: {
                    policy: state["routing_results"][lead_time][policy].assign(
                        date=lambda d: d["date"].astype(str))
                    for policy in ["reactive", "anticipatory"]
                }
                for lead_time in config.LEAD_TIMES
            },
        },
        "agent4_risk_flags": {
            "provenance": "DERIVED/ILLUSTRATIVE - rule-based thresholds over Agent 3 trajectories",
            "primary_rule": "rate_of_rise (see design_decisions above)",
            "rate_of_rise_episodes_by_lead_time": episodes,
            "absolute_threshold_crossings": {
                "elevated_fill_count": int(state["risk_df"]["elevated_fill"].sum()),
                "critical_fill_count": int(state["risk_df"]["critical_fill"].sum()),
                "elevated_outflow_count": int(state["risk_df"]["elevated_outflow"].sum()),
                "note": "kept for transparency - see design_decisions.rate_of_rise_primary_trigger",
            },
            "full_records": state["risk_df"],
        },
        "agent5_regulatory": {
            "provenance": "DERIVED/ILLUSTRATIVE, checked against a mix of CONFIRMED "
                           f"(ceiling={config.REGULATORY_MAX_OUTFLOW_M3S} m3/s = real peak_controlled_outflow_m3s) "
                           "and ASSUMED (floor, ramp rate) limits",
            "full_records": state["regulatory_df"],
        },
        "agent6_decision_synthesis": {
            "provenance": "LLM-GENERATED (Claude Code headless) narration of the DERIVED numeric outputs "
                           "above - or LLM_SYNTHESIS_FAILED if the call could not complete",
            "by_lead_time": state["synthesis"],
        },
    }

    with open(RUN_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(run_log, f, indent=2, default=_json_default)

    print(f"\nWrote {RUN_LOG_PATH}")
    return state, run_log


if __name__ == "__main__":
    main()
