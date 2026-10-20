"""Phase 6 — Charts (matplotlib). Each function saves a PNG and returns its path."""
from datetime import date, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # works without a display; images are saved to charts/
import matplotlib.pyplot as plt

import db

CHART_DIR = Path(__file__).parent / "charts"


def weekly_calorie_chart(conn, user_id, end_day=None):
    end = date.fromisoformat(end_day) if end_day else date.today()
    days = [(end - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    rows = {r["log_date"]: r for r in db.weekly_summary(conn, user_id, end.isoformat())}
    goal = db.active_goal(conn, user_id)
    user = db.get_user(conn, user_id)

    intake = [rows[d]["calories_in"] if d in rows else 0 for d in days]
    burned = [rows[d]["calories_out"] if d in rows else 0 for d in days]
    net = [i - b for i, b in zip(intake, burned)]
    labels = [date.fromisoformat(d).strftime("%a %d") for d in days]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(days))
    ax.bar([i - 0.2 for i in x], intake, width=0.4, label="Calories in", color="#4C9F70")
    ax.bar([i + 0.2 for i in x], burned, width=0.4, label="Calories burned", color="#E07A5F")
    ax.plot(list(x), net, marker="o", color="#3D405B", label="Net calories")
    if goal:
        ax.axhline(goal["daily_calorie_target"], linestyle="--", color="#F2CC8F", linewidth=2,
                   label=f"Target ({goal['daily_calorie_target']} kcal)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("kcal")
    ax.set_title(f"{user['name']} — last 7 days")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    CHART_DIR.mkdir(exist_ok=True)
    path = CHART_DIR / f"weekly_calories_user{user_id}.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def weight_chart(conn, user_id):
    hist = db.weight_history(conn, user_id)
    goal = db.active_goal(conn, user_id)
    user = db.get_user(conn, user_id)
    if not hist:
        return None

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(range(len(hist)), [h["weight_kg"] for h in hist], marker="o", color="#3D405B", label="Weight")
    ax.set_xticks(range(len(hist)))
    ax.set_xticklabels([h["recorded_on"] for h in hist], rotation=30, fontsize=8)
    if goal and goal["target_weight_kg"]:
        ax.axhline(goal["target_weight_kg"], linestyle="--", color="#4C9F70",
                   label=f"Target ({goal['target_weight_kg']} kg)")
    ax.set_ylabel("kg")
    ax.set_title(f"{user['name']} — weight progress")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()

    CHART_DIR.mkdir(exist_ok=True)
    path = CHART_DIR / f"weight_user{user_id}.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def team_chart(conn, team_id):
    rows = db.team_leaderboard(conn, team_id)
    if not rows:
        return None
    names = [r["member"] for r in rows]
    on_track = [r["days_on_track"] or 0 for r in rows]
    logged = [r["days_logged"] or 0 for r in rows]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(names, logged, color="#D9D9D9", label="Days logged")
    ax.barh(names, on_track, color="#4C9F70", label="Days on track")
    ax.set_xlim(0, 7)
    ax.invert_yaxis()
    ax.set_xlabel("days (last 7)")
    ax.set_title(f"Team leaderboard — {rows[0]['team_name']}")
    ax.legend(fontsize=8)
    fig.tight_layout()

    CHART_DIR.mkdir(exist_ok=True)
    path = CHART_DIR / f"team{team_id}_leaderboard.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path
