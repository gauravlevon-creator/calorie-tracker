"""Calorie Tracking System — terminal app (Phase 4 + 6).

Run:  python app.py
"""
import sqlite3
from datetime import date

import db
import calculator as calc
from recommend import recommendations

MEALS = ["breakfast", "lunch", "dinner", "snack"]
ACTIVITY = list(calc.ACTIVITY_FACTOR)


# ---------------- input helpers ----------------
def ask(prompt, cast=str, default=None, choices=None):
    while True:
        hint = f" [{default}]" if default is not None else ""
        raw = input(f"{prompt}{hint}: ").strip()
        if not raw and default is not None:
            return default
        try:
            value = cast(raw)
        except ValueError:
            print("  Invalid value, try again.")
            continue
        if choices and value not in choices:
            print(f"  Choose one of: {', '.join(map(str, choices))}")
            continue
        return value


def ask_date():
    return ask("Date (YYYY-MM-DD)", str, date.today().isoformat())


def line(char="-", n=60):
    print(char * n)


# ---------------- screens ----------------
def register(conn):
    print("\n== Register new user ==")
    name = ask("Name")
    email = ask("Email")
    gender = ask("Gender (M/F)", str.upper, choices=["M", "F"])
    age = ask("Age", int)
    height = ask("Height (cm)", float)
    weight = ask("Weight (kg)", float)
    print("Activity level: " + ", ".join(ACTIVITY))
    activity = ask("Activity level", str, "light", ACTIVITY)
    uid = db.add_user(conn, name, email, gender, age, height, weight, activity)
    print(f"Registered {name} (user id {uid}).")
    set_goal(conn, uid)
    return uid


def choose_user(conn):
    users = db.list_users(conn)
    if not users:
        print("No users yet — let's register one.")
        return register(conn)
    print("\nUsers:")
    for u in users:
        print(f"  {u['user_id']:>3}. {u['name']} ({u['email']})")
    print("    0. Register new user")
    uid = ask("Select user id", int)
    if uid == 0:
        return register(conn)
    if not db.get_user(conn, uid):
        print("No such user.")
        return choose_user(conn)
    return uid


def set_goal(conn, uid):
    user = db.get_user(conn, uid)
    value, label = calc.bmi(user)
    print(f"\n== Set goal ==  BMI {value} ({label}), maintenance ≈ {calc.tdee(user):.0f} kcal/day")
    goal_type = ask("Goal (lose/maintain/gain)", str.lower, choices=["lose", "maintain", "gain"])
    target_w = ask("Target weight in kg (Enter to skip)", str, "")
    target_w = float(target_w) if target_w else None
    kcal = calc.daily_calorie_target(user, goal_type)
    protein = calc.protein_target(user, goal_type)
    kcal = ask("Daily calorie target", int, kcal)
    db.set_goal(conn, uid, goal_type, kcal, protein, target_w)
    print(f"Goal saved: {goal_type}, {kcal} kcal/day, {protein} g protein/day.")


def log_food(conn, uid):
    print("\n== Log food ==")
    results = db.search_foods(conn, ask("Search food (e.g. roti, egg, dal)"))
    if not results:
        print("No matching food.")
        return
    for f in results:
        print(f"  {f['food_id']:>3}. {f['name']:<28} {f['calories_per_100g']:.0f} kcal/100g, serving {f['serving_g']:.0f} g")
    fid = ask("Food id", int, choices=[f["food_id"] for f in results])
    food = db.get_food(conn, fid)
    servings = ask(f"Servings (1 serving = {food['serving_g']:.0f} g)", float, 1.0)
    meal = ask("Meal (breakfast/lunch/dinner/snack)", str.lower, choices=MEALS)
    try:
        row = db.log_food(conn, uid, fid, servings * food["serving_g"], meal, ask_date())
        print(f"Logged {food['name']}: {row['calories']:.0f} kcal, {row['protein_g']} g protein.")
    except sqlite3.IntegrityError as e:
        print(f"Not saved: {e}")


def log_exercise(conn, uid):
    print("\n== Log exercise ==")
    exs = db.list_exercises(conn)
    for e in exs:
        print(f"  {e['exercise_id']:>3}. {e['name']} (MET {e['met_value']})")
    eid = ask("Exercise id", int, choices=[e["exercise_id"] for e in exs])
    mins = ask("Duration (minutes)", float)
    try:
        row = db.log_exercise(conn, uid, eid, mins, ask_date())
        print(f"Logged: {row['calories_burned']:.0f} kcal burned.")
    except sqlite3.IntegrityError as e:
        print(f"Not saved: {e}")


def show_day(conn, uid, day=None):
    day = day or ask_date()
    print(f"\n== Summary for {day} ==")
    line()
    for r in db.food_log_for_day(conn, uid, day):
        print(f"  {r['meal']:<10} {r['name']:<26} {r['quantity_g']:>5.0f} g {r['calories']:>6.0f} kcal")
    for r in db.exercise_log_for_day(conn, uid, day):
        print(f"  {'exercise':<10} {r['name']:<26} {r['duration_min']:>5.0f} m {-r['calories_burned']:>6.0f} kcal")
    s = db.daily_summary(conn, uid, day)
    if s:
        line()
        print(f"  In {s['calories_in']:.0f} - Burned {s['calories_out']:.0f} = Net {s['net_calories']:.0f} kcal"
              f"  | Target {s['target_calories']}  | Status: {s['status'].upper()}")
        print(f"  Protein {s['protein_g']:.0f} g  Carbs {s['carbs_g']:.0f} g  Fat {s['fat_g']:.0f} g")
    print("\nRecommendations:")
    for i, r in enumerate(recommendations(conn, uid, day), 1):
        print(f"  {i}. {r}")


def show_week(conn, uid):
    rows = db.weekly_summary(conn, uid)
    print("\n== Last 7 days ==")
    print(f"  {'Date':<12}{'In':>7}{'Out':>7}{'Net':>7}{'Target':>8}{'Protein':>9}  Status")
    line()
    for r in rows:
        print(f"  {r['log_date']:<12}{r['calories_in']:>7.0f}{r['calories_out']:>7.0f}{r['net_calories']:>7.0f}"
              f"{r['target_calories'] or 0:>8}{r['protein_g']:>8.0f}g  {r['status']}")
    if not rows:
        print("  Nothing logged this week.")


def teams_menu(conn, uid):
    print("\n== Teams ==")
    mine = db.user_teams(conn, uid)
    print("Your teams: " + (", ".join(t["name"] for t in mine) if mine else "none"))
    print("  1. Create team   2. Join team   3. Leaderboard   0. Back")
    choice = ask("Choice", int, 0)
    if choice == 1:
        try:
            tid = db.create_team(conn, ask("Team name"))
            db.join_team(conn, tid, uid)
            print("Team created and joined.")
        except sqlite3.IntegrityError:
            print("A team with that name already exists.")
    elif choice == 2:
        teams = db.list_teams(conn)
        for t in teams:
            print(f"  {t['team_id']:>3}. {t['name']} ({t['members']} members)")
        if teams:
            db.join_team(conn, ask("Team id", int, choices=[t["team_id"] for t in teams]), uid)
            print("Joined.")
    elif choice == 3:
        if not mine:
            print("Join a team first.")
            return
        tid = mine[0]["team_id"] if len(mine) == 1 else ask("Team id", int, choices=[t["team_id"] for t in mine])
        rows = db.team_leaderboard(conn, tid)
        print(f"\n  {'#':<3}{'Member':<18}{'Logged':>7}{'OnTrack':>8}{'AvgNet':>8}{'Target':>8}{'ActiveMin':>10}")
        line()
        for i, r in enumerate(rows, 1):
            print(f"  {i:<3}{r['member']:<18}{r['days_logged']:>7}{r['days_on_track']:>8}"
                  f"{r['avg_net_calories'] or 0:>8.0f}{r['target_calories'] or 0:>8}{r['active_minutes'] or 0:>10.0f}")


def charts_menu(conn, uid):
    import charts
    print("\n  1. Weekly calories   2. Weight progress   3. Team leaderboard")
    c = ask("Choice", int, 1, [1, 2, 3])
    if c == 1:
        path = charts.weekly_calorie_chart(conn, uid)
    elif c == 2:
        path = charts.weight_chart(conn, uid)
    else:
        mine = db.user_teams(conn, uid)
        path = charts.team_chart(conn, mine[0]["team_id"]) if mine else None
    print(f"Chart saved to {path}" if path else "Not enough data for this chart.")


def update_weight(conn, uid):
    w = ask("New weight (kg)", float)
    db.update_weight(conn, uid, w)
    print("Weight updated (history recorded). Consider resetting your goal so targets match your new weight.")


# ---------------- main loop ----------------
def main():
    conn = db.get_conn()
    db.init_db(conn)
    print("=" * 60 + "\n   CALORIE TRACKING SYSTEM\n" + "=" * 60)
    uid = choose_user(conn)

    actions = {
        1: ("Log food", log_food),
        2: ("Log exercise", log_exercise),
        3: ("Daily summary + recommendations", show_day),
        4: ("Weekly report", show_week),
        5: ("Set / change goal", set_goal),
        6: ("Update weight", update_weight),
        7: ("Teams (groups)", teams_menu),
        8: ("Charts", charts_menu),
    }
    while True:
        user = db.get_user(conn, uid)
        print(f"\n--- {user['name']} ---")
        for k, (label, _) in actions.items():
            print(f"  {k}. {label}")
        print("  9. Switch user\n  0. Exit")
        choice = ask("Choice", int)
        if choice == 0:
            break
        if choice == 9:
            uid = choose_user(conn)
        elif choice in actions:
            actions[choice][1](conn, uid)
    conn.close()
    print("Goodbye!")


if __name__ == "__main__":
    main()
