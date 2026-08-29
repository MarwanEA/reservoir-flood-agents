# Data Availability

This repository accompanies "A Multi-Agent AI Decision-Support Framework for Reservoir Flood Operations: The 2026 Oued El Makhazine Crisis, Morocco" (CAISN 2026). Some of the data behind it the authors can redistribute. Some of it they cannot, and this document explains which is which and why.

## Open data

| Item | Source | License | Location |
|---|---|---|---|
| Archived GFS precipitation forecast at the dam's coordinates, 2026-01-14 to 2026-02-08, at four lead times (same-day, T-24h, T-48h, T-72h) | Open-Meteo Previous Runs API | CC-BY 4.0 | `data/public/archived_forecast_loukkos_jan-feb2026.csv` |
| ERA5-based observed precipitation, same coordinates and window | Open-Meteo Archive API | CC-BY 4.0 | `data/public/actual_observed_loukkos_jan-feb2026.csv` |
| Regional weather-alert bulletin timeline | compiled from public press citations | public record | `data/reference/dgm_bulletin_trail.json` |
| Confirmed crisis milestones (dates, peak inflow/outflow/fill, evacuations, fatalities) | named ministry press briefings, one source per entry | public record | `data/reference/confirmed_milestones.json` |
| Pipeline code, orchestrator, analysis scripts | this work | MIT | `agents/`, `orchestrator.py`, `analysis/` |
| Pipeline output for the case-study run | this work, generated from the two rows above | MIT | `outputs/run_log.json` |

Open-Meteo's terms require attribution: https://open-meteo.com/en/license.

## Restricted data

Five rainfall-station records (Meska, Oughane, M'Douar, Bouferrah, Sahel; hydrological years 2015/16-2025/26) and a daily reservoir bilan for the Oued El Makhazine dam (2015-01-01 to 2026-08-01) were provided directly to the authors by ABHL (Agence du Bassin Hydraulique du Loukkos), the Loukkos basin authority, for this specific research.

This data is not in this repository, in any form, including a derivative that would let someone reconstruct the daily-resolution series. The authors are not permitted to redistribute it and do not control access to it.

One script, `analysis/step5_basin_rainfall_forcing_check.py`, takes this data as input and stops before its second step without it. It's included anyway so the method is open and auditable, with a note in its docstring explaining what's missing and why.

**Why it's restricted.** ABHL shared this dataset for the analysis in the paper, not for open redistribution. Basin-authority hydrological records like this are normally held under institutional access control rather than published as open data, and the authors are respecting the terms under which they received it.

**What's public despite this.** The specific figures the paper actually reports (peak inflow, peak fill, peak outflow, evacuations, fatalities) were separately made public by Morocco's Ministry of Equipment and Water through named press briefings, independent of ABHL. Those figures, dated and sourced, are in `data/reference/confirmed_milestones.json`. In the paper, the ABHL dataset served two purposes: cross-validating these already-public figures against the basin authority's own record, and forcing the rainfall-runoff transform with basin-average rather than single-point rainfall in the sensitivity check above. The result of that check, a single cumulative rainfall total over the case-study window rather than a daily series, is in `analysis/step5_result.md`.

**Requesting access.** Contact ABHL directly. The authors don't own this data and can't grant access to it on ABHL's behalf; this repository doesn't gatekeep access to data it doesn't control. Current contact information is in the Zenodo record for this repository: [https://doi.org/10.5281/zenodo.22152127](https://doi.org/10.5281/zenodo.22152127).

## FAIR

Everything in the open-data table is Findable and Accessible through this repository and its Zenodo archive ([https://doi.org/10.5281/zenodo.22152127](https://doi.org/10.5281/zenodo.22152127)), Interoperable as CSV or JSON with the schemas the code itself defines, and Reusable under CC-BY 4.0 (weather data) or MIT (code and derived output). The restricted dataset is not FAIR by design. It sits under third-party access control, and this repository doesn't work around that.
