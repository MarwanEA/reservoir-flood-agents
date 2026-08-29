"""
Agent 4 - Downstream Risk & Impact (rule-based, not LLM-based).

Applies three independent rule-based flags to Agent 3's routed trajectories:

  1. rate_of_rise: inflow estimate on date D exceeds RATE_RISE_FACTOR x the
     mean of the preceding RATE_RISE_LOOKBACK_DAYS (above a noise floor).
     Policy-independent (inflow is a forcing input, not a policy output).
     This is the PRIMARY signal used for the evaluation vs the DGM timeline,
     because Agent 2's simplified transform under-estimates absolute inflow
     magnitude relative to the CONFIRMED real peak - see agents/config.py.
  2. elevated_fill / critical_fill: storage fraction (of nominal capacity)
     crosses FILL_ELEVATED_THRESHOLD (100%) / FILL_CRITICAL_THRESHOLD (130%).
     Policy-dependent (reactive vs anticipatory produce different storage
     trajectories).
  3. elevated_outflow: outflow crosses NORMAL_SAFE_OUTFLOW_M3S. Policy-
     dependent.

All outputs are DERIVED/ILLUSTRATIVE - they flag periods in the pipeline's
own simulated trajectories, not real observed risk.
"""
import pandas as pd

from . import config


def _rate_of_rise_flags(dates, inflow_m3s):
    flags = []
    for i, (date, inflow) in enumerate(zip(dates, inflow_m3s)):
        lookback = inflow_m3s[max(0, i - config.RATE_RISE_LOOKBACK_DAYS):i]
        baseline = sum(lookback) / len(lookback) if lookback else 0.0
        triggered = (
            inflow >= config.RATE_RISE_MIN_INFLOW_M3S
            and baseline > 0
            and inflow >= config.RATE_RISE_FACTOR * baseline
        )
        flags.append({
            "date": date, "inflow_m3s": inflow, "baseline_m3s": baseline,
            "ratio": (inflow / baseline) if baseline > 0 else None,
            "rate_of_rise_flag": triggered,
        })
    return flags


def run(state: dict) -> dict:
    routing_results = state["routing_results"]
    inflow_df = state["inflow_df"]
    dates = inflow_df["date"].tolist()

    risk_records = []
    rate_of_rise_by_lead = {}

    for lead_time in config.LEAD_TIMES:
        inflow_series = inflow_df[f"inflow_m3s_{lead_time}"].tolist()
        ror_flags = _rate_of_rise_flags(dates, inflow_series)
        rate_of_rise_by_lead[lead_time] = ror_flags

        for policy in ["reactive", "anticipatory"]:
            traj = routing_results[lead_time][policy]
            for i, row in traj.iterrows():
                elevated_fill = row["fill_fraction"] >= config.FILL_ELEVATED_THRESHOLD
                critical_fill = row["fill_fraction"] >= config.FILL_CRITICAL_THRESHOLD
                elevated_outflow = row["outflow_m3s"] >= config.NORMAL_SAFE_OUTFLOW_M3S
                ror = ror_flags[i]["rate_of_rise_flag"]

                any_flag = elevated_fill or critical_fill or elevated_outflow or ror
                level = "critical" if critical_fill else ("elevated" if any_flag else "normal")

                risk_records.append({
                    "date": str(row["date"]), "lead_time": lead_time, "policy": policy,
                    "fill_percent": round(row["fill_percent"], 2),
                    "outflow_m3s": round(row["outflow_m3s"], 2),
                    "inflow_m3s": round(row["inflow_m3s"], 2),
                    "elevated_fill": bool(elevated_fill), "critical_fill": bool(critical_fill),
                    "elevated_outflow": bool(elevated_outflow), "rate_of_rise": bool(ror),
                    "risk_level": level,
                })

    risk_df = pd.DataFrame(risk_records)

    # First-flag date per lead time, using the policy-independent rate-of-rise
    # rule as the primary "when would the pipeline have raised this" signal.
    first_flags = {}
    for lead_time in config.LEAD_TIMES:
        triggered = [f for f in rate_of_rise_by_lead[lead_time] if f["rate_of_rise_flag"]]
        if triggered:
            first = triggered[0]
            offset_days = config.LEAD_TIME_OFFSET_DAYS[lead_time]
            valid_date = pd.Timestamp(first["date"])
            flag_raised_date = valid_date - pd.Timedelta(days=offset_days)
            first_flags[lead_time] = {
                "valid_date": str(first["date"]),
                "flag_raised_date": str(flag_raised_date.date()),
                "lead_offset_days": offset_days,
                "inflow_m3s": round(first["inflow_m3s"], 2),
                "ratio_vs_baseline": round(first["ratio"], 2) if first["ratio"] else None,
                "rule": "rate_of_rise",
            }
        else:
            first_flags[lead_time] = None

    n_elevated_or_worse = int((risk_df["risk_level"] != "normal").sum())
    print(f"[Agent 4: Downstream Risk & Impact] evaluated {len(risk_df)} (date x lead_time x policy) rows, "
          f"{n_elevated_or_worse} flagged elevated/critical. Rules: rate_of_rise (primary), "
          f"elevated_fill>={config.FILL_ELEVATED_THRESHOLD*100:.0f}%, "
          f"critical_fill>={config.FILL_CRITICAL_THRESHOLD*100:.0f}%, "
          f"elevated_outflow>={config.NORMAL_SAFE_OUTFLOW_M3S} m3/s. Output DERIVED/ILLUSTRATIVE.")
    for lead_time, f in first_flags.items():
        if f:
            print(f"  {lead_time}: first rate-of-rise flag for valid-date {f['valid_date']} "
                  f"(inflow {f['inflow_m3s']} m3/s, {f['ratio_vs_baseline']}x baseline) - "
                  f"info available on {f['flag_raised_date']} ({f['lead_offset_days']}d lead).")
        else:
            print(f"  {lead_time}: no rate-of-rise flag triggered in this window.")

    state["risk_df"] = risk_df
    state["risk_first_flags"] = first_flags
    return state
