"""
Step 5 (CAISN'26 paper, ABHL real-data integration) - standalone check, NOT
part of the evaluated pipeline.

Question: does replacing Agent 2's single-point GFS forcing with the real
5-station ABHL basin-average rainfall - with NO other recalibration - narrow
the ~9x inflow-magnitude gap documented in the paper's Limitations section?

Method: copies (does not import/modify) the exact SCS-CN + AMC + single
linear-reservoir transform from agents/agent2_forecasting.py, and runs it
twice over the same overlapping date window:
  (a) GFS D0 forecast at the dam point (data/public/daily_comparison_...,
      column handsum_D0) - what Agent 2 actually used.
  (b) 5-station ABHL basin average (rainfall_stations_jan_feb_2026.csv).

RESTRICTED INPUT: (b) requires rainfall_stations_jan_feb_2026.csv, which is
NOT included in this repository - the five rainfall-station records were
provided directly by ABHL (Agence du Bassin Hydraulique du Loukkos) for this
research and are not the authors' to redistribute. This script will not run
past step (a) without that file. See DATA_AVAILABILITY.md for how to request
it from ABHL. The script is published so the method is fully open and
auditable even though the restricted input isn't; analysis/step5_result.md
in this repository is the aggregate output of a run made with that file, and
contains a single 23-day cumulative total, not a daily time series.

Window caveat: the ABHL 5-station file is indexed by day-of-month (1-28) for
Jan and Feb separately, so it has NO Jan 29-31 rows (Feb 2026 has 28 days,
so those are fully covered; Jan is truncated at day 28). The overlap window
usable for a fair (a)-vs-(b) comparison is therefore 2026-01-14 to 2026-01-28
plus 2026-02-01 to 2026-02-08 = 23 days, not the full 26-day pipeline window.
Both series are restricted to this same 23-day window so the comparison
isolates the forcing-data effect, not a window-length effect.

Does not touch agents/, orchestrator.py, run_log.json, or dam_parameters.json.
Output: analysis/step5_result.md
"""
import math
import os

import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GFS_DAILY_CSV = os.path.join(REPO_ROOT, "data", "public", "daily_comparison_loukkos_jan-feb2026.csv")
STATIONS_CSV = os.path.join(REPO_ROOT, "data", "restricted", "rainfall_stations_jan_feb_2026.csv")
RESULT_MD = os.path.join(REPO_ROOT, "analysis", "step5_result.md")

# --- copied verbatim from agents/config.py (ASSUMED, unchanged) ---
BASIN_AREA_KM2 = 2414.0
CURVE_NUMBER_AMC2 = 75.0
AMC_LOOKBACK_DAYS = 5
LINEAR_RESERVOIR_K_DAYS = 1.5
CONFIRMED_REAL_PEAK_INFLOW_M3S = 3210.0  # corrected per ABHL/ministry, was 3163


# --- copied verbatim (logic unchanged) from agents/agent2_forecasting.py ---
def _amc_class(antecedent_5day_mm: float) -> str:
    if antecedent_5day_mm < 13.0:
        return "AMC-I"
    elif antecedent_5day_mm <= 28.0:
        return "AMC-II"
    else:
        return "AMC-III"


def _cn_for_amc(cn2: float, amc_class: str) -> float:
    if amc_class == "AMC-I":
        return cn2 / (2.281 - 0.01281 * cn2)
    elif amc_class == "AMC-III":
        return cn2 / (0.427 + 0.00573 * cn2)
    return cn2


def _scs_runoff_mm(precip_mm: float, cn: float) -> float:
    if precip_mm <= 0:
        return 0.0
    s = (25400.0 / cn) - 254.0
    ia = 0.2 * s
    if precip_mm <= ia:
        return 0.0
    return ((precip_mm - ia) ** 2) / (precip_mm - ia + s)


def _linear_reservoir_route(daily_volumes_m3: list, k_days: float) -> list:
    dt_days = 1.0
    alpha = math.exp(-dt_days / k_days)
    routed_m3s = []
    prev = 0.0
    for v in daily_volumes_m3:
        raw_m3s = v / 86400.0
        routed = prev * alpha + raw_m3s * (1 - alpha)
        routed_m3s.append(routed)
        prev = routed
    return routed_m3s


def run_transform(dates: list, precip_mm: list) -> pd.DataFrame:
    """Same SCS-CN + AMC + linear-reservoir transform as Agent 2, applied to
    one precipitation series (AMC computed from that same series)."""
    df = pd.DataFrame({"date": dates, "precip_mm": precip_mm}).sort_values("date").reset_index(drop=True)
    antecedent = df["precip_mm"].rolling(window=AMC_LOOKBACK_DAYS, min_periods=1).sum().shift(1).fillna(0.0)
    df["antecedent_5day_mm"] = antecedent
    df["amc_class"] = antecedent.apply(_amc_class)
    cn_series = df["amc_class"].apply(lambda c: _cn_for_amc(CURVE_NUMBER_AMC2, c))
    runoff_mm = [_scs_runoff_mm(p, cn) for p, cn in zip(df["precip_mm"], cn_series)]
    df["runoff_mm"] = runoff_mm
    basin_area_m2 = BASIN_AREA_KM2 * 1e6
    df["runoff_volume_m3"] = [r / 1000.0 * basin_area_m2 for r in runoff_mm]
    df["inflow_m3s"] = _linear_reservoir_route(df["runoff_volume_m3"].tolist(), LINEAR_RESERVOIR_K_DAYS)
    return df


def main():
    if not os.path.exists(STATIONS_CSV):
        print(f"Restricted input file not found: {STATIONS_CSV}")
        print()
        print("This file (5-station ABHL rainfall records) is not included in this")
        print("repository - it was provided directly to the authors by ABHL for this")
        print("research and the authors cannot redistribute it. See DATA_AVAILABILITY.md")
        print("for what it is and how to request it from ABHL.")
        print()
        print("If you have access to it, place it at the path above (create the")
        print("data/restricted/ directory if needed) and re-run this script.")
        return

    # --- (a) GFS D0 point forecast, restricted to the 23-day overlap window ---
    gfs = pd.read_csv(GFS_DAILY_CSV)
    gfs["date"] = pd.to_datetime(gfs["date"]).dt.date
    overlap_dates = (
        [d for d in gfs["date"] if pd.Timestamp(d).month == 1 and pd.Timestamp(d).day <= 28]
        + [d for d in gfs["date"] if pd.Timestamp(d).month == 2 and pd.Timestamp(d).day <= 8]
    )
    gfs_overlap = gfs[gfs["date"].isin(overlap_dates)].sort_values("date")
    full_window_peak_D0 = gfs["handsum_D0"].max()  # for context only (26-day window, as in the paper)

    gfs_result = run_transform(gfs_overlap["date"].tolist(), gfs_overlap["handsum_D0"].tolist())

    # --- (b) 5-station ABHL basin average, same 23-day window ---
    stations = pd.read_csv(STATIONS_CSV)
    rows = []
    for _, r in stations.iterrows():
        day = int(r["day"])
        if day <= 28:
            rows.append({"date": pd.Timestamp(2026, 1, day).date(), "station": r["station"], "mm": r["jan_2026_mm"]})
        if day <= 8:
            rows.append({"date": pd.Timestamp(2026, 2, day).date(), "station": r["station"], "mm": r["feb_2026_mm"]})
    long_df = pd.DataFrame(rows)
    basin_avg = long_df.groupby("date")["mm"].mean().reset_index().sort_values("date")
    n_stations_per_day = long_df.groupby("date")["station"].nunique()
    assert (n_stations_per_day == 5).all(), "expected all 5 stations present every day in overlap window"

    basin_result = run_transform(basin_avg["date"].tolist(), basin_avg["mm"].tolist())

    # --- comparison ---
    gfs_peak = gfs_result["inflow_m3s"].max()
    gfs_peak_date = gfs_result.loc[gfs_result["inflow_m3s"].idxmax(), "date"]
    basin_peak = basin_result["inflow_m3s"].max()
    basin_peak_date = basin_result.loc[basin_result["inflow_m3s"].idxmax(), "date"]

    gap_gfs = CONFIRMED_REAL_PEAK_INFLOW_M3S / gfs_peak
    gap_basin = CONFIRMED_REAL_PEAK_INFLOW_M3S / basin_peak
    narrowing_pct = (1 - gap_basin / gap_gfs) * 100

    cum_gfs = gfs_overlap["handsum_D0"].sum()
    cum_basin = basin_avg["mm"].sum()

    lines = []
    lines.append("# Step 5 result: basin-average rainfall forcing check (standalone, not part of evaluated pipeline)\n")
    lines.append(f"Overlap window used (both series): {overlap_dates[0]} to {overlap_dates[-1]}, "
                 f"{len(overlap_dates)} days (Jan 29-31 excluded - not present in the 5-station file; "
                 f"see script docstring).\n")
    lines.append("## Cumulative rainfall over the 23-day overlap window\n")
    lines.append(f"- GFS D0 (dam point): {cum_gfs:.1f} mm\n")
    lines.append(f"- 5-station ABHL basin average: {cum_basin:.1f} mm ({cum_basin/cum_gfs:.2f}x GFS)\n")
    lines.append("\n## Peak simulated inflow (same SCS-CN + linear-reservoir transform, unchanged parameters)\n")
    lines.append(f"- GFS D0 forcing (23-day window): {gfs_peak:.1f} m3/s, on {gfs_peak_date}\n")
    lines.append(f"  (for reference, full 26-day pipeline window peak D0: {full_window_peak_D0:.1f} mm/day precip "
                 f"-> not directly comparable, different window length; the 358 m3/s figure quoted in the paper "
                 f"is the full-window T-72h peak, not D0 - see run_log.json)\n")
    lines.append(f"- 5-station basin-average forcing (23-day window): {basin_peak:.1f} m3/s, on {basin_peak_date}\n")
    lines.append(f"\n## Magnitude gap vs. confirmed real peak inflow ({CONFIRMED_REAL_PEAK_INFLOW_M3S:.0f} m3/s)\n")
    lines.append(f"- GFS point forcing: {gap_gfs:.1f}x gap ({gfs_peak:.1f} -> {CONFIRMED_REAL_PEAK_INFLOW_M3S:.0f})\n")
    lines.append(f"- Basin-average forcing: {gap_basin:.1f}x gap ({basin_peak:.1f} -> {CONFIRMED_REAL_PEAK_INFLOW_M3S:.0f})\n")
    lines.append(f"\n**Result: replacing point forcing with basin-average forcing alone, no other recalibration, "
                 f"narrows the magnitude gap by {narrowing_pct:.0f}% "
                 f"({gap_gfs:.1f}x -> {gap_basin:.1f}x).**\n")
    lines.append("\nThis uses the SAME uncalibrated CN=75/AMC/k=1.5d parameters throughout - it isolates the "
                 "effect of forcing-data choice alone, exactly as asked. A full recalibration (fitting these "
                 "parameters to the basin) was out of scope for this check.\n")

    with open(RESULT_MD, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("".join(lines))
    print(f"\nWrote {RESULT_MD}")


if __name__ == "__main__":
    main()
