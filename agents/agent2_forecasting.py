"""
Agent 2 - Inflow Forecasting.

Real forcing data in (Agent 1's validated D0/T-24h/T-48h/T-72h precipitation
CSV), a simple documented rainfall-runoff transform, real output.

Method (deliberately simple, not overengineered):
  1. Daily precipitation depth per lead time (hourly sums from Agent 1's data,
     already QA-verified against the server's own daily aggregate).
  2. SCS Curve-Number method to convert rainfall depth -> runoff (excess
     rainfall) depth, with antecedent-moisture (AMC) adjustment using a
     5-day rolling total of the D0 series (dormant-season SCS thresholds,
     since this is a Moroccan winter event).
  3. Runoff depth -> runoff volume via the basin drainage area.
  4. A single linear-reservoir (Nash cascade, n=1) routing step converts the
     daily runoff volume into a lagged/attenuated inflow rate in m3/s - this
     is the "basic unit hydrograph" the brief asked for: a one-parameter
     conceptual IUH, not a calibrated model.

All CN/AMC/basin-area/routing-constant parameters are ASSUMED (see
agents/config.py for each one's justification) since dam_parameters.json
has no calibration data for this basin. Every output column here is
DERIVED/ILLUSTRATIVE, never to be blended with dam_parameters.json's
CONFIRMED figures without this tag - see qa provenance note.
"""
import math

import pandas as pd

from . import config


def _amc_class(antecedent_5day_mm: float) -> str:
    """Dormant-season SCS antecedent moisture condition thresholds."""
    if antecedent_5day_mm < 13.0:
        return "AMC-I"   # dry
    elif antecedent_5day_mm <= 28.0:
        return "AMC-II"  # normal
    else:
        return "AMC-III"  # wet


def _cn_for_amc(cn2: float, amc_class: str) -> float:
    if amc_class == "AMC-I":
        return cn2 / (2.281 - 0.01281 * cn2)
    elif amc_class == "AMC-III":
        return cn2 / (0.427 + 0.00573 * cn2)
    return cn2


def _scs_runoff_mm(precip_mm: float, cn: float) -> float:
    """SCS Curve Number excess-rainfall (runoff depth) equation."""
    if precip_mm <= 0:
        return 0.0
    s = (25400.0 / cn) - 254.0
    ia = 0.2 * s
    if precip_mm <= ia:
        return 0.0
    return ((precip_mm - ia) ** 2) / (precip_mm - ia + s)


def _linear_reservoir_route(daily_volumes_m3: list, k_days: float) -> list:
    """Single-tank (Nash n=1) linear reservoir routing of daily inflow volumes
    into a lagged/attenuated mean daily inflow rate (m3/s). This is the
    'unit hydrograph' step: alpha = exp(-1/k) is the recession fraction
    carried over from the previous day."""
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


def run(state: dict) -> dict:
    if not state["qa_report"]["passed"]:
        raise RuntimeError("Agent 2 refused to run: Agent 1 QA did not pass.")

    forecast_df = state["forecast_df"].copy()
    forecast_df["date"] = pd.to_datetime(forecast_df["timestamp"]).dt.date

    lead_cols = {
        "D0": "forecast_precip_mm_D0",
        "T-24h": "forecast_precip_mm_T-24h",
        "T-48h": "forecast_precip_mm_T-48h",
        "T-72h": "forecast_precip_mm_T-72h",
    }

    daily_precip = forecast_df.groupby("date").agg(
        **{f"precip_mm_{lt}": (col, "sum") for lt, col in lead_cols.items()}
    ).reset_index()
    daily_precip = daily_precip.sort_values("date").reset_index(drop=True)

    # Antecedent moisture from the D0 series (best-available precip record),
    # 5-day rolling sum of the *preceding* days (excludes the current day).
    d0_series = daily_precip["precip_mm_D0"]
    antecedent = d0_series.rolling(window=config.AMC_LOOKBACK_DAYS, min_periods=1).sum().shift(1).fillna(0.0)
    daily_precip["antecedent_5day_mm"] = antecedent
    daily_precip["amc_class"] = antecedent.apply(_amc_class)

    basin_area_m2 = config.BASIN_AREA_KM2 * 1e6

    for lt in lead_cols:
        cn_series = daily_precip["amc_class"].apply(lambda c: _cn_for_amc(config.CURVE_NUMBER_AMC2, c))
        runoff_mm = [
            _scs_runoff_mm(p, cn)
            for p, cn in zip(daily_precip[f"precip_mm_{lt}"], cn_series)
        ]
        daily_precip[f"runoff_mm_{lt}"] = runoff_mm
        daily_precip[f"runoff_volume_m3_{lt}"] = [r / 1000.0 * basin_area_m2 for r in runoff_mm]
        daily_precip[f"inflow_m3s_{lt}"] = _linear_reservoir_route(
            daily_precip[f"runoff_volume_m3_{lt}"].tolist(), config.LINEAR_RESERVOIR_K_DAYS
        )

    daily_precip.attrs["provenance"] = "DERIVED/ILLUSTRATIVE - simplified SCS-CN + linear-reservoir transform"
    daily_precip.attrs["assumed_params"] = {
        "basin_area_km2": config.BASIN_AREA_KM2,
        "curve_number_amc2": config.CURVE_NUMBER_AMC2,
        "linear_reservoir_k_days": config.LINEAR_RESERVOIR_K_DAYS,
    }

    print(f"[Agent 2: Inflow Forecasting] computed inflow estimates for {len(daily_precip)} dates, "
          f"4 lead times. CN(AMC-II)={config.CURVE_NUMBER_AMC2}, basin_area={config.BASIN_AREA_KM2}km2, "
          f"k={config.LINEAR_RESERVOIR_K_DAYS}d [ASSUMED params, DERIVED output].")
    peak_row = daily_precip.loc[daily_precip["inflow_m3s_D0"].idxmax()]
    print(f"  Peak D0 inflow estimate: {peak_row['inflow_m3s_D0']:.1f} m3/s on {peak_row['date']} "
          f"(cf. CONFIRMED real peak_inflow_m3s=3210 on 2026-01-28 - this transform is illustrative "
          f"and not expected to match that magnitude; see run_log provenance tags).")

    state["inflow_df"] = daily_precip
    return state
