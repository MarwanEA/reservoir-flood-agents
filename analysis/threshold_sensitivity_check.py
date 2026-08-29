"""
Standalone sensitivity check - NOT part of the evaluated pipeline. Does not
touch agents/, orchestrator.py, or run_log.json; only reads run_log.json.

Question: how much does the paper's headline result ("pipeline matched or
led the Feb 1-3 red/orange bulletin cluster by up to two days") depend on
the specific 3x rate-of-rise multiplier Agent 4 uses? And how does a naive
fixed-precipitation-threshold detector do on the same cluster?

Method:
  1. Re-applies the rate-of-rise rule (same trailing-3-day-mean logic as
     agents/agent4_downstream_risk.py, copied not imported) at multipliers
     2x, 2.5x, 3x (current), 3.5x, 4x, 5x, to Agent 2's already-computed
     inflow_m3s_{lead_time} series (read from outputs/run_log.json).
  2. Adds a naive baseline: flags any date where Agent 1's forecast
     precipitation (precip_mm_{lead_time}, also in run_log.json) exceeds a
     fixed threshold - tried at 20mm and 30mm.
  3. For every (method, parameter, lead_time) combination, finds the
     nearest flag to each of the 7 DGM bulletins (same nearest-flag
     matching as evaluate_vs_dgm.py) and reports days led/lagged.

Output: analysis/threshold_sensitivity_results.csv (full matrix) and
analysis/threshold_sensitivity_report.md (summary tables + the specific
Feb 1-3 cluster comparison).
"""
import csv
import json
import os

import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_LOG_PATH = os.path.join(REPO_ROOT, "outputs", "run_log.json")
CSV_OUT = os.path.join(REPO_ROOT, "analysis", "threshold_sensitivity_results.csv")
REPORT_OUT = os.path.join(REPO_ROOT, "analysis", "threshold_sensitivity_report.md")

# --- copied verbatim (unchanged) from agents/config.py ---
LEAD_TIMES = ["D0", "T-24h", "T-48h", "T-72h"]
LEAD_TIME_OFFSET_DAYS = {"D0": 0, "T-24h": 1, "T-48h": 2, "T-72h": 3}
RATE_RISE_LOOKBACK_DAYS = 3
RATE_RISE_MIN_INFLOW_M3S = 20.0

MULTIPLIERS = [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
PRECIP_THRESHOLDS_MM = [20.0, 30.0]

FEB_1_3_BULLETINS = {"2026-02-01", "2026-02-02", "2026-02-03"}


def load_inputs():
    with open(RUN_LOG_PATH, encoding="utf-8") as f:
        run_log = json.load(f)
    inflow_df = pd.DataFrame(run_log["agent2_inflow_forecast"]["daily_estimates"])
    inflow_df["date"] = pd.to_datetime(inflow_df["date"]).dt.date
    inflow_df = inflow_df.sort_values("date").reset_index(drop=True)
    bulletins = run_log["dgm_bulletin_trail"]["bulletins"]
    return inflow_df, bulletins


def rate_of_rise_episodes(dates, values, multiplier: float, min_floor: float) -> list:
    """Same logic as agents/agent4_downstream_risk.py's _rate_of_rise_flags,
    parameterized by multiplier instead of the fixed 3x."""
    episodes = []
    values = list(values)
    for i, (date, v) in enumerate(zip(dates, values)):
        lookback = values[max(0, i - RATE_RISE_LOOKBACK_DAYS):i]
        baseline = sum(lookback) / len(lookback) if lookback else 0.0
        triggered = v >= min_floor and baseline > 0 and v >= multiplier * baseline
        if triggered:
            episodes.append({"valid_date": date, "value": v, "baseline": baseline})
    return episodes


def naive_threshold_episodes(dates, precip_values, threshold_mm: float) -> list:
    """Naive baseline: flag any date where forecast precip exceeds a fixed threshold."""
    episodes = []
    for date, p in zip(dates, precip_values):
        if p >= threshold_mm:
            episodes.append({"valid_date": date, "value": p})
    return episodes


def nearest_flag_for_bulletin(bulletin_date: pd.Timestamp, episodes: list, offset_days: int):
    if not episodes:
        return None
    best = min(episodes, key=lambda e: abs((pd.Timestamp(e["valid_date"]) - pd.Timedelta(days=offset_days) - bulletin_date).days))
    flag_raised_date = pd.Timestamp(best["valid_date"]) - pd.Timedelta(days=offset_days)
    offset = (flag_raised_date - bulletin_date).days
    return {"flag_raised_date": str(flag_raised_date.date()), "valid_date": str(best["valid_date"]), "offset_days": offset}


def direction_label(offset_days: int) -> str:
    if offset_days < 0:
        return f"led {abs(offset_days)}d"
    elif offset_days > 0:
        return f"lag {offset_days}d"
    return "match"


def main():
    inflow_df, bulletins = load_inputs()
    dates = inflow_df["date"].tolist()

    rows = []  # method, param, lead_time, bulletin_date, level, flag_raised_date, offset_days, direction

    # --- rate-of-rise at each multiplier ---
    for mult in MULTIPLIERS:
        for lt in LEAD_TIMES:
            values = inflow_df[f"inflow_m3s_{lt}"].tolist()
            episodes = rate_of_rise_episodes(dates, values, mult, RATE_RISE_MIN_INFLOW_M3S)
            offset_days = LEAD_TIME_OFFSET_DAYS[lt]
            for b in bulletins:
                bdate = pd.Timestamp(b["date"])
                nearest = nearest_flag_for_bulletin(bdate, episodes, offset_days)
                rows.append({
                    "method": "rate_of_rise", "param": f"{mult}x", "lead_time": lt,
                    "bulletin_date": b["date"], "level": b["level"],
                    "n_episodes": len(episodes),
                    "flag_raised_date": nearest["flag_raised_date"] if nearest else None,
                    "offset_days": nearest["offset_days"] if nearest else None,
                    "direction": direction_label(nearest["offset_days"]) if nearest else "no flag",
                })

    # --- naive fixed-precipitation-threshold baseline ---
    for thresh in PRECIP_THRESHOLDS_MM:
        for lt in LEAD_TIMES:
            precip_values = inflow_df[f"precip_mm_{lt}"].tolist()
            episodes = naive_threshold_episodes(dates, precip_values, thresh)
            offset_days = LEAD_TIME_OFFSET_DAYS[lt]
            for b in bulletins:
                bdate = pd.Timestamp(b["date"])
                nearest = nearest_flag_for_bulletin(bdate, episodes, offset_days)
                rows.append({
                    "method": "naive_precip_threshold", "param": f"{thresh:.0f}mm", "lead_time": lt,
                    "bulletin_date": b["date"], "level": b["level"],
                    "n_episodes": len(episodes),
                    "flag_raised_date": nearest["flag_raised_date"] if nearest else None,
                    "offset_days": nearest["offset_days"] if nearest else None,
                    "direction": direction_label(nearest["offset_days"]) if nearest else "no flag",
                })

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {CSV_OUT} ({len(rows)} rows)")

    # --- build report ---
    lines = ["# Threshold sensitivity check: rate-of-rise multiplier and naive baseline\n",
              "Standalone check, not part of the evaluated pipeline. Reads outputs/run_log.json only.\n"]

    lines.append("\n## 1. Rate-of-rise multiplier sensitivity, full DGM comparison\n")
    lines.append("\nDays led (negative)/lagged (positive) vs. each DGM bulletin, by lead time. "
                 "'match' = 0d. 3.0x is the value used in the paper.\n")
    for mult in MULTIPLIERS:
        lines.append(f"\n### Multiplier {mult}x\n")
        lines.append("| DGM bulletin | Level | D0 | T-24h | T-48h | T-72h |\n|---|---|---|---|---|---|\n")
        for b in bulletins:
            cells = []
            for lt in LEAD_TIMES:
                r = [row for row in rows if row["method"] == "rate_of_rise" and row["param"] == f"{mult}x"
                     and row["lead_time"] == lt and row["bulletin_date"] == b["date"]][0]
                cells.append(r["direction"])
            lines.append(f"| {b['date']} | {b['level'][:20]} | " + " | ".join(cells) + " |\n")

    lines.append("\n## 2. Naive fixed-precipitation-threshold baseline, full DGM comparison\n")
    for thresh in PRECIP_THRESHOLDS_MM:
        lines.append(f"\n### Threshold {thresh:.0f}mm\n")
        lines.append("| DGM bulletin | Level | D0 | T-24h | T-48h | T-72h |\n|---|---|---|---|---|---|\n")
        for b in bulletins:
            cells = []
            for lt in LEAD_TIMES:
                r = [row for row in rows if row["method"] == "naive_precip_threshold"
                     and row["param"] == f"{thresh:.0f}mm" and row["lead_time"] == lt
                     and row["bulletin_date"] == b["date"]][0]
                cells.append(r["direction"])
            lines.append(f"| {b['date']} | {b['level'][:20]} | " + " | ".join(cells) + " |\n")

    lines.append("\n## 3. Focused comparison: the Feb 1-3 cluster (the paper's headline claim)\n")
    lines.append("\nDoes 'matched or led by up to 2 days' hold at other multipliers, and how does "
                 "the naive baseline do on the same three bulletins?\n")
    lines.append("\n| Method | Param | DGM bulletin | D0 | T-24h | T-48h | T-72h |\n|---|---|---|---|---|---|---|\n")
    for row_source, params, method_name in [
        ("rate_of_rise", [f"{m}x" for m in MULTIPLIERS], "rate_of_rise"),
        ("naive_precip_threshold", [f"{t:.0f}mm" for t in PRECIP_THRESHOLDS_MM], "naive_precip_threshold"),
    ]:
        for param in params:
            for b in bulletins:
                if b["date"] not in FEB_1_3_BULLETINS:
                    continue
                cells = []
                for lt in LEAD_TIMES:
                    r = [row for row in rows if row["method"] == method_name and row["param"] == param
                         and row["lead_time"] == lt and row["bulletin_date"] == b["date"]][0]
                    cells.append(r["direction"])
                lines.append(f"| {method_name} | {param} | {b['date']} | " + " | ".join(cells) + " |\n")

    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Wrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
