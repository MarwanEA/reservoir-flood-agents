"""
Agent 1 - Perception & Data-QA.

Loads the archived forecast CSV, observed CSV, daily QA CSV, and both
reference JSON files. Runs independent validation checks (does not just
trust the fetch script's own printed QA) and flags any data-quality issue:
missing dates, coordinate mismatch, suspicious repeated values, bad ranges.

Downstream agents should not run if qa_report["passed"] is False.
"""
import json
import math

import pandas as pd

from . import config


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _check_coordinates(issues, checks):
    """Flag if the API actually returned data for somewhere other than the dam
    (this is the exact bug the old script had: Fes, ~100km away, instead of the dam)."""
    meta_path = config.DATA_RAW_DIR + "/fetch_metadata.json"
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    except FileNotFoundError:
        issues.append({"severity": "error", "check": "coordinates",
                        "detail": f"fetch_metadata.json not found at {meta_path}; cannot verify coordinates."})
        checks["coordinates"] = "FAIL"
        return

    max_km = 0.0
    for source_name in ["forecast_source", "observed_source"]:
        src = meta[source_name]
        dist_km = _haversine_km(config.DAM_LAT, config.DAM_LON, src["returned_lat"], src["returned_lon"])
        max_km = max(max_km, dist_km)
        # GFS/ERA5 grid spacing is ~11-25km; >25km means we likely queried the wrong place.
        if dist_km > 25.0:
            issues.append({"severity": "error", "check": "coordinates",
                            "detail": f"{source_name} returned data {dist_km:.1f} km from the dam "
                                      f"(expected ({config.DAM_LAT}, {config.DAM_LON}), "
                                      f"got ({src['returned_lat']}, {src['returned_lon']})) - coordinate mismatch."})
    checks["coordinates"] = "PASS" if max_km <= 25.0 else "FAIL"
    checks["coordinates_max_offset_km"] = round(max_km, 2)


def _check_completeness(issues, checks, df, label, value_col):
    expected_start = pd.Timestamp(config.RUN_START_DATE)
    expected_end = pd.Timestamp(config.RUN_END_DATE) + pd.Timedelta(hours=23)
    expected_hours = int((expected_end - expected_start) / pd.Timedelta(hours=1)) + 1

    ts = pd.to_datetime(df["timestamp"])
    if len(df) != expected_hours:
        issues.append({"severity": "error", "check": f"completeness_{label}",
                        "detail": f"{label}: expected {expected_hours} hourly rows "
                                  f"({config.RUN_START_DATE} to {config.RUN_END_DATE}), got {len(df)}."})
    full_range = pd.date_range(expected_start, expected_end, freq="h")
    missing = full_range.difference(ts)
    if len(missing) > 0:
        issues.append({"severity": "error", "check": f"completeness_{label}",
                        "detail": f"{label}: {len(missing)} missing timestamps, "
                                  f"e.g. {list(missing[:5].astype(str))}."})
    checks[f"completeness_{label}"] = "PASS" if len(df) == expected_hours and len(missing) == 0 else "FAIL"

    if df[value_col].isna().any():
        n = int(df[value_col].isna().sum())
        issues.append({"severity": "error", "check": f"nulls_{label}",
                        "detail": f"{label}: {n} null values in {value_col}."})
    if (df[value_col] < 0).any():
        n = int((df[value_col] < 0).sum())
        issues.append({"severity": "error", "check": f"range_{label}",
                        "detail": f"{label}: {n} negative precipitation values in {value_col}."})


def _check_repeated_values(issues, checks, df, label, value_col, run_threshold=6):
    """Flag suspiciously long runs of an identical *non-zero* value - stuck-sensor /
    bad-interpolation smell. Runs of 0.0 (dry hours) are normal and excluded."""
    vals = df[value_col].to_numpy()
    max_run = 1
    run_len = 1
    run_start = 0
    flagged = []
    for i in range(1, len(vals)):
        if vals[i] == vals[i - 1] and vals[i] != 0.0:
            run_len += 1
        else:
            if run_len >= run_threshold:
                flagged.append((run_start, i - 1, vals[i - 1], run_len))
            run_len = 1
            run_start = i
        max_run = max(max_run, run_len)
    if run_len >= run_threshold:
        flagged.append((run_start, len(vals) - 1, vals[-1], run_len))

    if flagged:
        for start, end, val, length in flagged:
            issues.append({"severity": "warning", "check": f"repeated_values_{label}",
                            "detail": f"{label}: {length} consecutive hours of identical non-zero value "
                                      f"{val}mm at rows {start}-{end} ({df['timestamp'].iloc[start]} to "
                                      f"{df['timestamp'].iloc[end]})."})
    checks[f"repeated_values_{label}"] = "PASS" if not flagged else "WARN"


def _check_daily_qa(issues, checks, tolerance_mm=1.0):
    try:
        qa = pd.read_csv(config.DAILY_QA_CSV)
    except FileNotFoundError:
        issues.append({"severity": "error", "check": "daily_qa_file",
                        "detail": f"{config.DAILY_QA_CSV} not found."})
        checks["daily_qa"] = "FAIL"
        return
    max_d0 = qa["D0_vs_server_diff_mm"].abs().max()
    max_obs = qa["observed_vs_server_diff_mm"].abs().max()
    checks["daily_qa_max_D0_diff_mm"] = round(float(max_d0), 4)
    checks["daily_qa_max_observed_diff_mm"] = round(float(max_obs), 4)
    if max_d0 > tolerance_mm or max_obs > tolerance_mm:
        issues.append({"severity": "error", "check": "daily_qa",
                        "detail": f"Hand-summed hourly totals diverge from server daily aggregate by "
                                  f">{tolerance_mm}mm (max D0 diff {max_d0:.3f}, max observed diff {max_obs:.3f}). "
                                  f"This is the failure mode ecmwf_ifs025 had - do not trust hourly sums."})
        checks["daily_qa"] = "FAIL"
    else:
        checks["daily_qa"] = "PASS"


def run(state: dict) -> dict:
    issues = []
    checks = {}

    forecast_df = pd.read_csv(config.FORECAST_CSV)
    observed_df = pd.read_csv(config.OBSERVED_CSV)

    with open(config.DAM_PARAMS_JSON, encoding="utf-8") as f:
        dam_params = json.load(f)
    with open(config.DGM_BULLETIN_JSON, encoding="utf-8") as f:
        dgm_bulletins = json.load(f)

    _check_coordinates(issues, checks)
    _check_completeness(issues, checks, forecast_df, "forecast_D0", "forecast_precip_mm_D0")
    _check_completeness(issues, checks, observed_df, "observed", "observed_precipitation_mm")
    for col in ["forecast_precip_mm_D0", "forecast_precip_mm_T-24h", "forecast_precip_mm_T-48h", "forecast_precip_mm_T-72h"]:
        _check_repeated_values(issues, checks, forecast_df, col, col)
    _check_repeated_values(issues, checks, observed_df, "observed_precipitation_mm", "observed_precipitation_mm")
    _check_daily_qa(issues, checks)

    # Cross-check config constants against dam_parameters.json (source of truth).
    if dam_params["dam"]["nominal_capacity_Mm3"] != config.NOMINAL_CAPACITY_MM3:
        issues.append({"severity": "error", "check": "config_drift",
                        "detail": "config.NOMINAL_CAPACITY_MM3 does not match dam_parameters.json."})

    n_errors = sum(1 for i in issues if i["severity"] == "error")
    n_warnings = sum(1 for i in issues if i["severity"] == "warning")
    passed = n_errors == 0

    qa_report = {
        "passed": passed,
        "n_errors": n_errors,
        "n_warnings": n_warnings,
        "checks": checks,
        "issues": issues,
    }

    print(f"[Agent 1: Perception & Data-QA] passed={passed} errors={n_errors} warnings={n_warnings}")
    for i in issues:
        print(f"  [{i['severity'].upper()}] {i['check']}: {i['detail']}")

    state["forecast_df"] = forecast_df
    state["observed_df"] = observed_df
    state["dam_params"] = dam_params
    state["dgm_bulletins"] = dgm_bulletins
    state["qa_report"] = qa_report
    return state
