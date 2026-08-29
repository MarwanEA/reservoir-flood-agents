"""
Evaluation section: compares the pipeline's rate-of-rise flag dates (Agent 4,
run_log.json) against the real DGM alert timeline (dgm_bulletin_trail.json).

Reads outputs/run_log.json (does not re-run the pipeline) and writes:
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

from agents import config

RUN_LOG_PATH = f"{config.OUTPUTS_DIR}/run_log.json"
COMPARISON_MD_PATH = f"{config.OUTPUTS_DIR}/evaluation_comparison.md"
TIMELINE_PNG_PATH = f"{config.OUTPUTS_DIR}/figures/evaluation_timeline.png"


def _load():
    with open(RUN_LOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _nearest_episode(dgm_date: pd.Timestamp, episodes: list):
    if not episodes:
        return None
    best = min(episodes, key=lambda e: abs((pd.Timestamp(e["flag_raised_date"]) - dgm_date).days))
    offset = (pd.Timestamp(best["flag_raised_date"]) - dgm_date).days
    return {"flag_raised_date": best["flag_raised_date"], "valid_date": best["valid_date"],
            "offset_days": offset}


def build_comparison(run_log: dict):
    bulletins = run_log["dgm_bulletin_trail"]["bulletins"]
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


def build_plot(bulletins, episodes_by_lead):
    fig, ax = plt.subplots(figsize=(12, 5))

    rows = ["DGM bulletin"] + config.LEAD_TIMES
    y_pos = {label: i for i, label in enumerate(rows)}

    dgm_dates = [pd.Timestamp(b["date"]) for b in bulletins]
    ax.scatter(dgm_dates, [y_pos["DGM bulletin"]] * len(dgm_dates),
               marker="D", s=90, color="#c0392b", label="DGM bulletin (REPORTED)", zorder=3)
    for b in bulletins:
        ax.annotate(b["level"].split(",")[0].split("(")[0].strip(), (pd.Timestamp(b["date"]), y_pos["DGM bulletin"]),
                    textcoords="offset points", xytext=(0, 10), fontsize=7, ha="center", color="#c0392b")

    colors = {"D0": "#2980b9", "T-24h": "#27ae60", "T-48h": "#8e44ad", "T-72h": "#d35400"}
    for lead_time in config.LEAD_TIMES:
        dates = [pd.Timestamp(e["flag_raised_date"]) for e in episodes_by_lead[lead_time]]
        if not dates:
            continue
        ax.scatter(dates, [y_pos[lead_time]] * len(dates), marker="o", s=70,
                   color=colors[lead_time], label=f"Pipeline flag ({lead_time}, DERIVED)", zorder=3)

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows)
    ax.set_ylim(-0.5, len(rows) - 0.5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    plt.xticks(rotation=45, ha="right")
    ax.set_title("Oued El Makhazine crisis: pipeline rate-of-rise flags vs. real DGM alert timeline\n"
                  "(2026-01-14 to 2026-02-08)")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(TIMELINE_PNG_PATH, dpi=150)
    print(f"Wrote {TIMELINE_PNG_PATH}")


def main():
    run_log = _load()
    events, bulletins, episodes_by_lead = build_comparison(run_log)
    build_plot(bulletins, episodes_by_lead)


if __name__ == "__main__":
    main()
