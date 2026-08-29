# reservoir-flood-agents

Code for "A Multi-Agent AI Decision-Support Framework for Reservoir Flood Operations: The 2026 Oued El Makhazine Crisis, Morocco," submitted to CAISN 2026.

The paper proposes a six-agent pipeline for reservoir flood-release decisions and evaluates it against the January-February 2026 crisis at the Oued El Makhazine dam in Morocco's Loukkos basin. This repository has the pipeline code, the archived weather data it runs on, three standalone sensitivity checks, and the pipeline's own output for the case-study window.

## What's here

- `agents/` - the six agents (perception and data QA, inflow forecasting, reservoir routing, downstream risk, regulatory constraints, decision synthesis) and shared config. Agents 1-5 are plain rule-based Python; only Agent 6 calls an LLM.
- `orchestrator.py`, `run_case_study.py` - LangGraph orchestration and the script that runs the full case study and writes `outputs/run_log.json`.
- `evaluate_vs_dgm.py` - builds the comparison between the pipeline's risk flags and the regional weather-alert timeline (Figure 2 in the paper).
- `backfill_agent6.py` - regenerates Agent 6's rationale text without re-running Agents 1-5.
- `analysis/` - three standalone checks, kept separate from the evaluated pipeline: a basin-average-rainfall forcing check, a rate-of-rise threshold sensitivity check, and a single-shot-vs-agentic prompt comparison.
- `data/public/` - archived GFS forecast and ERA5-based observed precipitation at the dam's coordinates, pulled from Open-Meteo, and the script that fetched them.
- `data/reference/` - dam parameters, the regional weather-alert bulletin timeline, and a dated timeline of confirmed crisis milestones.
- `outputs/` - the pipeline's own log for the case-study run and the comparison figure.

## Running it

Needs Python 3.11 or newer (developed on 3.13) and, for Agent 6 only, a Claude Code subscription. Agents 1-5 need neither an API key nor Claude Code.

```
pip install -r requirements.txt
python run_case_study.py
```

This runs Agents 1-5 on the archived weather data in `data/public/` and writes `outputs/run_log.json`. Agent 6 then calls `claude -p` to generate operator-facing rationale text for each forecast lead time. If that call fails (no Claude Code session, no network), the run still finishes and the numeric output is unaffected; only the rationale text gets marked as failed. To regenerate just Agent 6's output afterward:

```
python backfill_agent6.py
```

The `analysis/` scripts don't depend on the pipeline or on each other:

```
python analysis/threshold_sensitivity_check.py
python analysis/single_shot_vs_agentic_check.py
```

`analysis/step5_basin_rainfall_forcing_check.py` needs a restricted input file that isn't in this repository. See Data availability below.

## Data availability

This repository splits into two parts.

**Open.** The archived weather data (`data/public/`), the pipeline code, its output for the case-study run (`outputs/`), and the regional weather-alert bulletin timeline (`data/reference/dgm_bulletin_trail.json`) are all here under the MIT license. The weather data is redistributed from Open-Meteo (GFS forecast archive and ERA5-based reanalysis), CC-BY 4.0.

**Restricted.** Five rainfall-station records and a daily reservoir bilan were provided directly to the authors by ABHL (Agence du Bassin Hydraulique du Loukkos), the basin authority, for this specific research. They aren't included here and the authors can't redistribute them. `data/reference/confirmed_milestones.json` has the specific dated figures from the case study that are already public through ministry press statements, with sources for each one. One analysis script, `analysis/step5_basin_rainfall_forcing_check.py`, needs the restricted rainfall-station file to run past its first step; the script and its aggregate output are both in this repository, but the input file is not.

See DATA_AVAILABILITY.md for the full breakdown and how to request the restricted data.

## Citation

If you use this code, cite the paper. See CITATION.cff.

Zenodo DOI: ==FILL_ZENODO_DOI_HERE==
