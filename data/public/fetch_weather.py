"""
Fetch archived forecast (with lead-time offsets) and actual observed precipitation
for the Oued El Makhazine dam site, Jan 14 - Feb 8 2026 crisis window
(matches dam_parameters.json's crisis_window, covers the Feb 7 DGM bulletin
and the second fatality event, Feb 7-8).

Data sources (Open-Meteo, no API key required):
  - previous-runs-api: archived forecasts as they existed at issue time, using
    fixed lead-time offsets (precipitation_previous_dayN = forecast issued N days
    before the valid date, i.e. T-24h/48h/72h). Model: gfs_seamless.
      NOTE: ecmwf_ifs025 was tried first and rejected - it is natively 3-hourly,
      and hand-summing its open-meteo-interpolated hourly values to daily totals
      gave figures up to 2.5x off the server's own daily aggregate. gfs_seamless
      is natively hourly; hourly-sum vs server daily aggregate was verified to
      match exactly for this window (see Agent 1's QA check).
  - archive-api: ERA5-based historical observed precipitation (ground truth).

Coordinates: dam site (34.94, -5.83), Loukkos basin - NOT Fes.
"""
import json
import os
import requests
import pandas as pd

LATITUDE = 34.94
LONGITUDE = -5.83
START_DATE = "2026-01-14"
END_DATE = "2026-02-08"
MODEL = "gfs_seamless"

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_archived_forecast() -> pd.DataFrame:
    """Hourly forecast precipitation at D0 and lead times T-24h/48h/72h (gfs_seamless)."""
    print("Fetching archived forecast data (previous-runs-api, gfs_seamless)...")
    url = "https://previous-runs-api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": "precipitation,precipitation_previous_day1,precipitation_previous_day2,precipitation_previous_day3",
        "models": MODEL,
        "timezone": "auto",
    }
    response = requests.get(url, params=params, timeout=30)
    if response.status_code != 200:
        print(f"HTTP Error {response.status_code}: {response.text[:200]}")
        response.raise_for_status()

    data = response.json()
    h = data["hourly"]
    df = pd.DataFrame({
        "timestamp": h["time"],
        "forecast_precip_mm_D0": h["precipitation"],
        "forecast_precip_mm_T-24h": h["precipitation_previous_day1"],
        "forecast_precip_mm_T-48h": h["precipitation_previous_day2"],
        "forecast_precip_mm_T-72h": h["precipitation_previous_day3"],
    })
    meta = {
        "requested_lat": LATITUDE, "requested_lon": LONGITUDE,
        "returned_lat": data["latitude"], "returned_lon": data["longitude"],
        "elevation_m": data.get("elevation"), "timezone": data.get("timezone"),
    }
    return df, meta


def fetch_daily_reference(latitude, longitude) -> pd.DataFrame:
    """Server-computed daily precipitation_sum for D0 (QA cross-check target)."""
    url = "https://previous-runs-api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": "precipitation_sum",
        "models": MODEL,
        "timezone": "auto",
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    return pd.DataFrame({
        "date": data["daily"]["time"],
        "server_daily_precip_sum_mm_D0": data["daily"]["precipitation_sum"],
    })


def fetch_actual_observed() -> pd.DataFrame:
    """Hourly + daily-aggregate observed precipitation (archive-api, ERA5-based)."""
    print("Fetching actual observed data (archive-api)...")
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": "precipitation",
        "daily": "precipitation_sum",
        "timezone": "auto",
    }
    response = requests.get(url, params=params, timeout=30)
    if response.status_code != 200:
        print(f"HTTP Error {response.status_code}: {response.text[:200]}")
        response.raise_for_status()

    data = response.json()
    hourly_df = pd.DataFrame({
        "timestamp": data["hourly"]["time"],
        "observed_precipitation_mm": data["hourly"]["precipitation"],
    })
    daily_df = pd.DataFrame({
        "date": data["daily"]["time"],
        "server_daily_precip_sum_mm_observed": data["daily"]["precipitation_sum"],
    })
    meta = {
        "requested_lat": LATITUDE, "requested_lon": LONGITUDE,
        "returned_lat": data["latitude"], "returned_lon": data["longitude"],
        "elevation_m": data.get("elevation"), "timezone": data.get("timezone"),
    }
    return hourly_df, daily_df, meta


if __name__ == "__main__":
    try:
        df_forecast, forecast_meta = fetch_archived_forecast()
        df_forecast_daily_ref = fetch_daily_reference(LATITUDE, LONGITUDE)
        df_observed_hourly, df_observed_daily_ref, observed_meta = fetch_actual_observed()

        forecast_csv = os.path.join(OUT_DIR, "archived_forecast_loukkos_jan-feb2026.csv")
        observed_csv = os.path.join(OUT_DIR, "actual_observed_loukkos_jan-feb2026.csv")
        comparison_csv = os.path.join(OUT_DIR, "daily_comparison_loukkos_jan-feb2026.csv")
        metadata_json = os.path.join(OUT_DIR, "fetch_metadata.json")

        df_forecast.to_csv(forecast_csv, index=False)
        df_observed_hourly.to_csv(observed_csv, index=False)
        with open(metadata_json, "w", encoding="utf-8") as f:
            json.dump({
                "expected_dam_lat": 34.94, "expected_dam_lon": -5.83,
                "start_date": START_DATE, "end_date": END_DATE, "model": MODEL,
                "forecast_source": {"endpoint": "previous-runs-api.open-meteo.com", **forecast_meta},
                "observed_source": {"endpoint": "archive-api.open-meteo.com", **observed_meta},
            }, f, indent=2)

        # Build the daily comparison / QA table: hand-summed hourly vs server's own
        # daily aggregate, for every lead time plus observed. This is the check that
        # would have caught the ecmwf_ifs025 3-hourly-interpolation bug.
        df_forecast["date"] = pd.to_datetime(df_forecast["timestamp"]).dt.date
        df_observed_hourly["date"] = pd.to_datetime(df_observed_hourly["timestamp"]).dt.date

        daily_summed = df_forecast.groupby("date").agg(
            handsum_D0=("forecast_precip_mm_D0", "sum"),
            handsum_T24h=("forecast_precip_mm_T-24h", "sum"),
            handsum_T48h=("forecast_precip_mm_T-48h", "sum"),
            handsum_T72h=("forecast_precip_mm_T-72h", "sum"),
        )
        observed_summed = df_observed_hourly.groupby("date").agg(
            handsum_observed=("observed_precipitation_mm", "sum"),
        )

        df_forecast_daily_ref["date"] = pd.to_datetime(df_forecast_daily_ref["date"]).dt.date
        df_observed_daily_ref["date"] = pd.to_datetime(df_observed_daily_ref["date"]).dt.date
        df_forecast_daily_ref = df_forecast_daily_ref.set_index("date")
        df_observed_daily_ref = df_observed_daily_ref.set_index("date")

        comparison = daily_summed.join(observed_summed).join(df_forecast_daily_ref).join(df_observed_daily_ref)
        comparison["D0_vs_server_diff_mm"] = (comparison["handsum_D0"] - comparison["server_daily_precip_sum_mm_D0"]).round(3)
        comparison["observed_vs_server_diff_mm"] = (comparison["handsum_observed"] - comparison["server_daily_precip_sum_mm_observed"]).round(3)
        comparison.to_csv(comparison_csv)

        max_d0_diff = comparison["D0_vs_server_diff_mm"].abs().max()
        max_obs_diff = comparison["observed_vs_server_diff_mm"].abs().max()

        print("\n==========================================")
        print("SUCCESS! Files created:")
        print(f" 1. {forecast_csv} ({len(df_forecast)} rows, hourly, D0 + T-24/48/72h)")
        print(f" 2. {observed_csv} ({len(df_observed_hourly)} rows, hourly observed)")
        print(f" 3. {comparison_csv} ({len(comparison)} rows, daily QA comparison)")
        print("==========================================")
        print(f"\nQA: max |hand-summed D0 - server daily_sum| = {max_d0_diff:.3f} mm")
        print(f"QA: max |hand-summed observed - server daily_sum| = {max_obs_diff:.3f} mm")
        if max_d0_diff > 1.0 or max_obs_diff > 1.0:
            print("WARNING: hand-summed hourly totals diverge from server daily aggregate by >1mm.")
        else:
            print("Hand-summed hourly totals match server daily aggregates (gfs_seamless is natively hourly).")

        print("\n--- Daily Comparison (Jan 14 - Feb 8, 2026) ---")
        print(comparison.to_string())

    except Exception as e:
        print(f"\nExecution failed: {e}")
        raise
