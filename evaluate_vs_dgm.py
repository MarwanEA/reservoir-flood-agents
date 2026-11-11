"""
Evaluation section: compares the pipeline's rate-of-rise flag dates (Agent 4,
run_log.json) against the real DGM alert timeline (dgm_bulletin_trail.json).

Reads outputs/run_log.json (does not re-run the pipeline) for the flags and the
inflow series. The DGM bulletins come straight from data/reference/dgm_bulletin_trail.json,
not from the copy embedded in run_log.json, so a stale embedded copy cannot leak in.
Writes:
  - outputs/evaluation_comparison.md   (two markdown tables)
  - outputs/figures/evaluation_timeline.png  (timeline plot)

For each pipeline lead time, "flag_raised_date" is the date that flag would
actually have been available (valid_date minus the lead-time offset - see
design note in agents/config.py: the T-72h column for valid-date D was the
forecast issued on D-3).
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

from agents import config

RUN_LOG_PATH = f"{config.OUTPUTS_DIR}/run_log.json"
COMPARISON_MD_PATH = f"{config.OUTPUTS_DIR}/evaluation_comparison.md"
TIMELINE_PNG_PATH = f"{config.OUTPUTS_DIR}/figures/evaluation_timeline.png"

# Figure is drawn at its printed width, so the font sizes below are as-printed points.
# LNCS text width 12.2 cm x 0.90 = 11.0 cm = 4.3 in -> \includegraphics[width=0.90\textwidth].
FIG_W_IN, FIG_H_IN, FIG_DPI = 4.3, 3.0, 300
TICK_FS, XTICK_FS, LABEL_FS, LEGEND_FS = 11, 10, 10, 10
LEGEND_BAND = 0.225  # fraction of figure height reserved for the legend at the bottom


def _load():
    with open(RUN_LOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_bulletins():
    with open(config.DGM_BULLETIN_JSON, encoding="utf-8") as f:
        return json.load(f)["bulletins"]


def _nearest_episode(dgm_date: pd.Timestamp, episodes: list):
    if not episodes:
        return None
    best = min(episodes, key=lambda e: abs((pd.Timestamp(e["flag_raised_date"]) - dgm_date).days))
    offset = (pd.Timestamp(best["flag_raised_date"]) - dgm_date).days
    return {"flag_raised_date": best["flag_raised_date"], "valid_date": best["valid_date"],
            "offset_days": offset}


def build_comparison(run_log: dict):
    bulletins = _load_bulletins()
    episodes_by_lead = run_log["agent4_risk_flags"]["rate_of_rise_episodes_by_lead_time"]

    # --- Table 1: chronological interleaved timeline ---
    events = []
    for b in bulletins:
        events.append({
            "date": b["date"], "source": "DGM bulletin", "detail":
                f"{b['level']} - {b['region']} - forecast {b.get('forecast_mm', 'n/a')}mm "
                f"(valid {b.get('valid_period', 'n/a')})",
        })
    for lead_time, eps in episodes_by_lead.items():
        for e in eps:
            events.append({
                "date": e["flag_raised_date"], "source": f"Pipeline flag ({lead_time})",
                "detail": f"rate-of-rise flag for valid-date {e['valid_date']} "
                          f"(inflow {e['inflow_m3s']:.1f} m3/s, {e['lead_offset_days']}d lead)",
            })
    events.sort(key=lambda e: e["date"])

    table1_lines = ["| Date | Source | Detail |", "|---|---|---|"]
    for e in events:
        table1_lines.append(f"| {e['date']} | {e['source']} | {e['detail']} |")

    # --- Table 2: nearest pipeline flag per DGM bulletin, per lead time ---
    table2_lines = [
        "| DGM bulletin date | Level | D0 | T-24h | T-48h | T-72h |",
        "|---|---|---|---|---|---|",
    ]
    for b in bulletins:
        dgm_date = pd.Timestamp(b["date"])
        cells = []
        for lead_time in config.LEAD_TIMES:
            nearest = _nearest_episode(dgm_date, episodes_by_lead[lead_time])
            if nearest is None:
                cells.append("no flag")
            else:
                d = nearest["offset_days"]
                direction = "led by" if d < 0 else ("lagged by" if d > 0 else "matched")
                cells.append(f"{nearest['flag_raised_date']} ({direction} {abs(d)}d)" if d != 0
                              else f"{nearest['flag_raised_date']} (matched)")
        table2_lines.append(f"| {b['date']} | {b['level']} | " + " | ".join(cells) + " |")

    md = "\n".join([
        "# Evaluation: Pipeline flags vs. DGM alert timeline",
        "",
        "## Table 1 - Chronological timeline (DGM bulletins + pipeline rate-of-rise flags)",
        "",
        *table1_lines,
        "",
        "## Table 2 - Nearest pipeline flag per DGM bulletin, by lead time",
        "",
        "Negative/'led by' = pipeline flag came before the DGM bulletin (earlier warning). "
        "Positive/'lagged by' = pipeline flag came after.",
        "",
        *table2_lines,
        "",
    ])
    with open(COMPARISON_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {COMPARISON_MD_PATH}")
    return events, bulletins, episodes_by_lead


def build_plot(bulletins, episodes_by_lead, inflow_records, inflow_lead="D0"):
    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN))
    ax2 = ax.twinx()  # right axis: pipeline's simulated (derived) inflow, drawn behind the flags
    ax2.set_zorder(0)
    ax.set_zorder(1)
    ax.patch.set_visible(False)

    rows = ["DGM\nbulletin"] + config.LEAD_TIMES
    y_pos = {label: i for i, label in enumerate(rows)}

    # Agent 2 simulated inflow, one representative lead time. D0 has 0-day lead, so its
    # valid dates line up with its flag-available dates on the shared x-axis.
    # Kept faint so the flag markers stay the visual focus. Derived only, no observed data.
    (inflow_line,) = ax2.plot(
        [pd.Timestamp(r["date"]) for r in inflow_records],
        [r[f"inflow_m3s_{inflow_lead}"] for r in inflow_records],
        color="0.4", lw=1.0, alpha=0.55,
    )
    ax2.set_ylim(bottom=0)
    ax2.yaxis.set_major_locator(MaxNLocator(nbins=3, integer=True, steps=[1, 2, 5, 10]))
    ax2.tick_params(labelsize=TICK_FS)
    ax2.set_ylabel("Simulated inflow\n(derived, m³/s)", fontsize=LABEL_FS)

    # DGM bulletins: diamonds, filled by the Larache alert level (official bulletins, not pipeline output)
    level_colors = {"orange": "#f39c12", "red": "#c0392b"}
    levels = [b["level"].split(",")[0].split("(")[0].strip() for b in bulletins]
    ax.scatter([pd.Timestamp(b["date"]) for b in bulletins], [y_pos["DGM\nbulletin"]] * len(bulletins),
               marker="D", s=40, facecolors=[level_colors[lv] for lv in levels],
               edgecolors="black", linewidths=0.8, zorder=3)

    # Pipeline flags: circles, one color per lead time
    colors = {"D0": "#0072B2", "T-24h": "#009E73", "T-48h": "#7B3294", "T-72h": "#56B4E9"}
    for lead_time in config.LEAD_TIMES:
        dates = [pd.Timestamp(e["flag_raised_date"]) for e in episodes_by_lead[lead_time]]
        if dates:
            ax.scatter(dates, [y_pos[lead_time]] * len(dates), marker="o", s=32,
                       color=colors[lead_time], edgecolors="white", linewidths=0.6, zorder=3)

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlim(pd.Timestamp("2026-01-13"), pd.Timestamp("2026-02-09"))
    ax.set_xticks([pd.Timestamp(d) for d in ("2026-01-14", "2026-01-20", "2026-01-26", "2026-02-01", "2026-02-07")])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_minor_locator(mdates.DayLocator())
    ax.tick_params(axis="both", labelsize=TICK_FS)
    ax.tick_params(axis="x", labelsize=XTICK_FS)  # a touch smaller so neighbouring date labels keep a gap
    ax.grid(axis="x", alpha=0.3)

    flag_handles = [Line2D([], [], marker="o", ls="", color=colors[lt], markersize=6.5) for lt in config.LEAD_TIMES]
    dgm_handle = tuple(Line2D([], [], marker="D", ls="", markerfacecolor=level_colors[lv],
                              markeredgecolor="black", markersize=5) for lv in ("orange", "red"))
    labels = [f"{lt} flag (derived)" for lt in config.LEAD_TIMES] + \
             ["DGM bulletin (official)", f"Inflow, {inflow_lead} (derived)"]
    fig.legend(flag_handles + [dgm_handle, inflow_line], labels, loc="lower center", ncol=2,
               fontsize=LEGEND_FS, frameon=False, columnspacing=1.2, handletextpad=0.4,
               handler_map={tuple: HandlerTuple(ndivide=None, pad=0.2)})
    fig.tight_layout(rect=(0, LEGEND_BAND, 1, 1))
    fig.savefig(TIMELINE_PNG_PATH, dpi=FIG_DPI)
    print(f"Wrote {TIMELINE_PNG_PATH}")


def main():
    run_log = _load()
    events, bulletins, episodes_by_lead = build_comparison(run_log)
    build_plot(bulletins, episodes_by_lead, run_log["agent2_inflow_forecast"]["daily_estimates"])


if __name__ == "__main__":
    main()
