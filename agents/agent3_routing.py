"""
Agent 3 - Reservoir Routing & Scenario Simulation (rule-based, not LLM-based).

Daily mass-balance routing against NOMINAL_CAPACITY_MM3 (672.9 Mm3,
CONFIRMED), forced by Agent 2's DERIVED inflow estimates. Storage is allowed
to exceed 100% of nominal capacity (flood-surcharge storage) since the real
event confirmed a peak_fill_percent of 166.4%.

Two release policies are simulated, each run independently against all four
of Agent 2's lead-time inflow series (D0, T-24h, T-48h, T-72h) - i.e. "what
would this policy have done if the only inflow signal available was the one
implied by a T-Xh-ahead forecast":

  - reactive: only opens extra release once storage crosses 100% of nominal
    capacity (FILL_ELEVATED_THRESHOLD). Mirrors a policy that waits for the
    reservoir to actually be full before acting.
  - anticipatory: opens extra release earlier, once storage crosses 90% of
    nominal capacity (FILL_WATCH_THRESHOLD) - a policy that starts creating
    buffer capacity before the reservoir is nominally full.

Both use simple proportional control (drain the excess-above-threshold
volume over N days, clipped to [MIN_RELEASE_M3S, REGULATORY_MAX_OUTFLOW_M3S]
which is the CONFIRMED real peak_controlled_outflow_m3s of 878 - the policies
may not invent a higher ceiling than was actually achieved in the real event).

Output is entirely DERIVED/ILLUSTRATIVE: it depends on Agent 2's inflow
estimates and on ASSUMED initial storage / controller constants
(agents/config.py), not on any CONFIRMED trajectory (dam_parameters.json has
only point-in-time confirmed figures, not a daily storage series).
"""
import pandas as pd

from . import config


def _simulate(dates, inflow_m3s, policy: str) -> pd.DataFrame:
    capacity_m3 = config.NOMINAL_CAPACITY_MM3 * 1e6
    storage_m3 = config.INITIAL_FILL_FRACTION * capacity_m3

    watch_frac = config.FILL_WATCH_THRESHOLD if policy == "anticipatory" else config.FILL_ELEVATED_THRESHOLD
    drain_days = config.ANTICIPATORY_DRAIN_DAYS if policy == "anticipatory" else config.REACTIVE_DRAIN_DAYS

    rows = []
    for date, inflow in zip(dates, inflow_m3s):
        inflow_vol_m3 = inflow * 86400.0
        storage_before_release_m3 = storage_m3 + inflow_vol_m3
        fill_frac_pre = storage_before_release_m3 / capacity_m3

        if fill_frac_pre >= watch_frac:
            excess_m3 = storage_before_release_m3 - watch_frac * capacity_m3
            extra_m3s = excess_m3 / (drain_days * 86400.0)
            outflow_m3s = min(max(config.MIN_RELEASE_M3S, config.MIN_RELEASE_M3S + extra_m3s),
                               config.REGULATORY_MAX_OUTFLOW_M3S)
        else:
            outflow_m3s = config.MIN_RELEASE_M3S

        outflow_vol_m3 = outflow_m3s * 86400.0
        storage_m3 = max(0.0, storage_before_release_m3 - outflow_vol_m3)
        fill_frac_post = storage_m3 / capacity_m3

        rows.append({
            "date": date,
            "inflow_m3s": inflow,
            "outflow_m3s": outflow_m3s,
            "storage_Mm3": storage_m3 / 1e6,
            "fill_fraction": fill_frac_post,
            "fill_percent": fill_frac_post * 100.0,
        })
    return pd.DataFrame(rows)


def run(state: dict) -> dict:
    inflow_df = state["inflow_df"]
    dates = inflow_df["date"].tolist()

    routing_results = {}
    for lead_time in config.LEAD_TIMES:
        inflow_series = inflow_df[f"inflow_m3s_{lead_time}"].tolist()
        routing_results[lead_time] = {
            "reactive": _simulate(dates, inflow_series, "reactive"),
            "anticipatory": _simulate(dates, inflow_series, "anticipatory"),
        }

    print(f"[Agent 3: Reservoir Routing & Scenario Simulation] simulated 2 policies x "
          f"{len(config.LEAD_TIMES)} lead times over {len(dates)} days. "
          f"initial_fill={config.INITIAL_FILL_FRACTION*100:.0f}% [ASSUMED], "
          f"capacity={config.NOMINAL_CAPACITY_MM3} Mm3 [CONFIRMED]. Output DERIVED/ILLUSTRATIVE.")
    for lead_time in config.LEAD_TIMES:
        r = routing_results[lead_time]["reactive"]
        a = routing_results[lead_time]["anticipatory"]
        print(f"  {lead_time}: reactive peak fill={r['fill_percent'].max():.1f}% "
              f"(max outflow={r['outflow_m3s'].max():.1f} m3/s) | "
              f"anticipatory peak fill={a['fill_percent'].max():.1f}% "
              f"(max outflow={a['outflow_m3s'].max():.1f} m3/s)")

    state["routing_results"] = routing_results
    return state
