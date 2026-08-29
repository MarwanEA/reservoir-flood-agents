"""
Shared paths and constants for the reservoir-agents pipeline.

Every constant below is tagged CONFIRMED or ASSUMED:
  - CONFIRMED: taken directly from data/reference/dam_parameters.json or
    data/reference/dgm_bulletin_trail.json (official/press-sourced figures).
  - ASSUMED: not present in either reference file. Needed to make the
    rainfall-runoff transform (Agent 2) and routing/regulatory rules
    (Agents 3-5) runnable. Each has a one-line justification. These flow
    into every downstream number as "derived/illustrative" per the
    provenance_note in dam_parameters.json - never blend with CONFIRMED
    figures without the tag.
"""
import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_REF_DIR = os.path.join(PROJECT_ROOT, "data", "reference")
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs")

FORECAST_CSV = os.path.join(DATA_RAW_DIR, "archived_forecast_loukkos_jan-feb2026.csv")
OBSERVED_CSV = os.path.join(DATA_RAW_DIR, "actual_observed_loukkos_jan-feb2026.csv")
DAILY_QA_CSV = os.path.join(DATA_RAW_DIR, "daily_comparison_loukkos_jan-feb2026.csv")
DAM_PARAMS_JSON = os.path.join(DATA_REF_DIR, "dam_parameters.json")
DGM_BULLETIN_JSON = os.path.join(DATA_REF_DIR, "dgm_bulletin_trail.json")

with open(DAM_PARAMS_JSON, encoding="utf-8") as f:
    _dam_params = json.load(f)

# ---- CONFIRMED (dam_parameters.json) ----
DAM_LAT = _dam_params["dam"]["coordinates"]["lat"]                    # 34.94
DAM_LON = _dam_params["dam"]["coordinates"]["lon"]                    # -5.83
NOMINAL_CAPACITY_MM3 = _dam_params["dam"]["nominal_capacity_Mm3"]     # 672.9
PEAK_CONTROLLED_OUTFLOW_M3S = _dam_params["confirmed_figures"]["peak_controlled_outflow_m3s"]  # 878
RUN_START_DATE = "2026-01-14"
RUN_END_DATE = "2026-02-08"

# ---- ASSUMED (not in either reference file - documented here, used everywhere) ----

# Drainage area of the Oued El Makhazine watershed. Published figure (2,414 km2),
# not in dam_parameters.json. Source: ResearchGate watershed location map fig.
# https://www.researchgate.net/figure/Oued-El-Makhazine-watershed-location-map_fig1_296335817
BASIN_AREA_KM2 = 2414.0

# SCS Curve Number, AMC-II (normal antecedent moisture), for a mixed
# agricultural/scrubland Mediterranean basin. Standard textbook mid-range
# value (SCS-CN typically 65-85 for such land cover) - not basin-calibrated.
CURVE_NUMBER_AMC2 = 75.0

# Antecedent-moisture 5-day lookback window used to shift CN between
# AMC-I/II/III (standard SCS practice), keyed off the D0 forecast series.
AMC_LOOKBACK_DAYS = 5

# Linear-reservoir (single-tank / Nash n=1) storage constant, i.e. the
# basin's characteristic runoff lag. ~1.5 days is a generic planning-level
# estimate for a basin of this size and relief; not calibrated to observed
# hydrographs (none available at daily resolution for this basin).
LINEAR_RESERVOIR_K_DAYS = 1.5

# Reservoir storage assumed on RUN_START_DATE (2026-01-14), before the
# precursor rainfall began. dam_parameters.json has no pre-crisis fill level.
# 60% of nominal capacity is used as a generic "normal pre-flood-season
# operating pool" assumption for a Moroccan multi-purpose dam entering winter.
INITIAL_FILL_FRACTION = 0.60

# Fill-fraction (of nominal capacity) thresholds used by Agent 3/4 policy
# and risk logic. Reservoirs can exceed 100% of "nominal" capacity into
# flood-surcharge storage (confirmed: real peak_fill_percent reached 166.4%),
# so these are operational alert bands, not hard caps.
FILL_WATCH_THRESHOLD = 0.90    # anticipatory policy starts early release
FILL_ELEVATED_THRESHOLD = 1.00  # Agent 4: elevated downstream risk
FILL_CRITICAL_THRESHOLD = 1.30  # Agent 4: critical downstream risk

# Release-policy outflow ceilings (m3/s). PEAK_CONTROLLED_OUTFLOW_M3S (878,
# confirmed) is used as the hard ceiling both policies may not exceed.
# NORMAL_SAFE_OUTFLOW_M3S is an assumed baseline "no downstream nuisance"
# release rate, used by Agent 5 as the regulatory watch threshold - no
# official Loukkos-at-Larache channel-capacity figure was found in public
# sources for this basin.
NORMAL_SAFE_OUTFLOW_M3S = 150.0
REGULATORY_MAX_OUTFLOW_M3S = PEAK_CONTROLLED_OUTFLOW_M3S  # 878, CONFIRMED ceiling

# Agent 3 release-controller tuning (simple proportional control: drain the
# excess-above-threshold volume over N days, clipped to [min_release, max]).
# Generic planning-level values, not optimized/calibrated.
MIN_RELEASE_M3S = 5.0            # baseline ecological/operational release
REACTIVE_DRAIN_DAYS = 3.0        # reactive policy: drain excess over 3 days
ANTICIPATORY_DRAIN_DAYS = 5.0    # anticipatory: gentler since it starts earlier

# --- Agent 4 primary trigger: rate-of-rise, not absolute fill/outflow ---
#
# This was NOT the original design. Agents 3/4 were first built with
# absolute thresholds only (FILL_ELEVATED/CRITICAL_THRESHOLD above). Running
# the pipeline showed those never fire: Agent 2's simplified, uncalibrated
# transform tops out around 78% simulated fill (T-72h; peak inflow 358 m3/s),
# ~9x below the CONFIRMED real peak inflow of 3210 m3/s. Two disclosed
# factors contribute to that gap, not just the transform:
#   1. The rainfall-runoff transform itself (SCS-CN + single-tank routing)
#      is a planning-level approximation with no basin-specific calibration
#      data available (see BASIN_AREA_KM2, CURVE_NUMBER_AMC2 notes below).
#   2. The forcing data itself: this project independently confirmed the
#      GFS forecast underestimates observed rainfall for this exact site.
#      For 2026-02-04, D0 (gfs_seamless) forecast 20.9mm vs. 49.9mm actually
#      observed (ERA5, archive-api) - forecast at ~42% of observed, roughly
#      half. See data/raw/daily_comparison_loukkos_jan-feb2026.csv. GFS
#      underestimation of that specific event's rainfall therefore likely
#      explains part of the inflow-magnitude gap upstream of the transform.
#
# Given both factors, an absolute fill/outflow threshold calibrated to real
# capacity is not a fair test of this pipeline's timing behavior - it would
# silently never fire regardless of how well the pipeline tracked the shape
# of the event. Rate-of-rise (inflow vs. its own trailing baseline) is
# scale-independent and is standard real-world flood early-warning practice
# for exactly this reason, so it was adopted as the PRIMARY signal after
# this limitation surfaced. The absolute-threshold rules are kept and still
# logged for every run (see risk_df / regulatory_df) for transparency, even
# though they currently show 0 crossings.
RATE_RISE_FACTOR = 3.0
RATE_RISE_LOOKBACK_DAYS = 3
RATE_RISE_MIN_INFLOW_M3S = 20.0

# Lead time -> how many days earlier that information was actually available
# (Open-Meteo previous-runs-api semantics: the T-72h value for valid-date D
# was the forecast issued on D-3, i.e. known 72h/3 days before D).
LEAD_TIME_OFFSET_DAYS = {"D0": 0, "T-24h": 1, "T-48h": 2, "T-72h": 3}

LEAD_TIMES = ["D0", "T-24h", "T-48h", "T-72h"]

# Agent 5 regulatory ramp-rate constraint: max allowed day-over-day change in
# outflow (m3/s per day), a standard type of downstream-safety operating
# rule (sudden releases endanger anyone in the channel). Generic planning
# value, not a published Loukkos-specific figure (none found in public
# sources for this basin).
RAMP_RATE_LIMIT_M3S_PER_DAY = 200.0
