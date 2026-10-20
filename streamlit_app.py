"""Calorie Tracking System — Streamlit web frontend.

Uses the same SQLite database and the same db.py / calculator.py / recommend.py
as the terminal app, so data entered in either one shows up in both.

Run:  streamlit run streamlit_app.py
"""
import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

import db
import calculator as calc
from recommend import recommendations

st.set_page_config(page_title="Calorie Tracker", page_icon="🥗", layout="wide")

MEALS = ["breakfast", "lunch", "dinner", "snack"]
GOALS = ["lose", "maintain", "gain"]
ACTIVITY = list(calc.ACTIVITY_FACTOR)


def get_conn():
    conn = db.get_conn()
    db.init_db(conn)
    return conn


conn = get_conn()


# ======================================================================
# Sidebar: user selection, registration, goal
# ======================================================================
def register_form():
    with st.form("register", clear_on_submit=True):
        name = st.text_input("Name")
        email = st.text_input("Email")
        c1, c2 = st.columns(2)
        gender = c1.selectbox("Gender", ["M", "F"])
        age = c2.number_input("Age", 10, 100, 21)
        height = c1.number_input("Height (cm)", 100.0, 250.0, 170.0, step=1.0)
        weight = c2.number_input("Weight (kg)", 25.0, 300.0, 70.0, step=0.5)
        activity = st.selectbox("Activity level", ACTIVITY, index=1)
        if st.form_submit_button("Register", type="primary"):
            if not name.strip() or not email.strip():
                st.error("Name and email are required.")
                return
            try:
                uid = db.add_user(conn, name.strip(), email.strip(), gender, age, height, weight, activity)
                st.session_state.user_id = uid
                st.success(f"Welcome, {name}! Now set your goal.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("That email is already registered.")


def goal_form(user):
    with st.form("goal"):
        goal_type = st.selectbox("Goal", GOALS)
        target_w = st.number_input("Target weight (kg, 0 = skip)", 0.0, 300.0, 0.0, step=0.5)
        st.caption("Calorie and protein targets are calculated from your body details and goal.")
        if st.form_submit_button("Save goal", type="primary"):
            kcal = calc.daily_calorie_target(user, goal_type)
            protein = calc.protein_target(user, goal_type)
            db.set_goal(conn, user["user_id"], goal_type, kcal, protein, target_w or None)
            st.success(f"Goal saved: {kcal} kcal / {protein} g protein per day")
            st.rerun()


with st.sidebar:
    st.title("🥗 Calorie Tracker")
    users = db.list_users(conn)

    if users:
        ids = [u["user_id"] for u in users]
        labels = {u["user_id"]: f"{u['name']} ({u['email']})" for u in users}
        current = st.session_state.get("user_id", ids[0])
        if current not in ids:
            current = ids[0]
        st.session_state.user_id = st.selectbox(
            "User", ids, index=ids.index(current), format_func=lambda i: labels[i])

    with st.expander("➕ Register new user", expanded=not users):
        register_form()

    if not users:
        st.info("Register a user to get started.")
        st.stop()

    user = db.get_user(conn, st.session_state.user_id)
    goal = db.active_goal(conn, user["user_id"])

    st.divider()
    bmi_value, bmi_label = calc.bmi(user)
    c1, c2 = st.columns(2)
    c1.metric("BMI", bmi_value, bmi_label, delta_color="off")
    c2.metric("Maintenance", f"{calc.tdee(user):.0f} kcal")
    if goal:
        target_txt = f", target {goal['target_weight_kg']:.0f} kg" if goal["target_weight_kg"] else ""
        st.markdown(f"**Goal:** {goal['goal_type'].title()}{target_txt}  \n"
                    f"**Daily:** {goal['daily_calorie_target']} kcal · {goal['protein_target_g']} g protein")
    else:
        st.warning("No goal set yet.")

    with st.expander("🎯 Set / change goal", expanded=goal is None):
        goal_form(user)

uid = user["user_id"]

# ======================================================================
# Main tabs
# ======================================================================
tab_dash, tab_log, tab_week, tab_team, tab_profile = st.tabs(
    ["📊 Dashboard", "📝 Log", "📈 Weekly", "👥 Team", "⚖️ Weight"])

# ---------------- Dashboard ----------------
with tab_dash:
    day = st.date_input("Date", date.today(), max_value=date.today(), key="dash_day").isoformat()
    s = db.daily_summary(conn, uid, day)

    target = goal["daily_calorie_target"] if goal else None
    cin = s["calories_in"] if s else 0
    cout = s["calories_out"] if s else 0
    net = s["net_calories"] if s else 0
    protein = s["protein_g"] if s else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Calories in", f"{cin:.0f}")
    m2.metric("Burned", f"{cout:.0f}")
    m3.metric("Net", f"{net:.0f}", f"of {target}" if target else None, delta_color="off")
    if target:
        remaining = target - net
        m4.metric("Remaining", f"{remaining:.0f}",
                  "over target" if remaining < 0 else "left", delta_color="inverse" if remaining < 0 else "normal")
        m5.metric("Protein", f"{protein:.0f} g", f"of {goal['protein_target_g']} g", delta_color="off")
        st.progress(min(max(net / target, 0), 1.0),
                    text=f"Status: **{s['status'].upper() if s else 'NOTHING LOGGED'}**")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("💡 Recommendations")
        for r in recommendations(conn, uid, day):
            st.markdown(f"- {r}")

    with right:
        if s and (s["protein_g"] + s["carbs_g"] + s["fat_g"]) > 0:
            st.subheader("Macros (kcal)")
            macros = pd.DataFrame({
                "kcal": [s["protein_g"] * 4, s["carbs_g"] * 4, s["fat_g"] * 9]},
                index=["Protein", "Carbs", "Fat"])
            st.bar_chart(macros, horizontal=True, height=180)

    st.subheader("Today's log")
    food = db.food_log_for_day(conn, uid, day)
    ex = db.exercise_log_for_day(conn, uid, day)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Food**")
        if food:
            st.dataframe(pd.DataFrame([dict(r) for r in food]).rename(columns={
                "meal": "Meal", "name": "Food", "quantity_g": "Qty (g)", "calories": "kcal", "protein_g": "Protein (g)"}),
                hide_index=True, width="stretch")
        else:
            st.caption("No food logged.")
    with c2:
        st.markdown("**Exercise**")
        if ex:
            st.dataframe(pd.DataFrame([dict(r) for r in ex]).rename(columns={
                "name": "Exercise", "duration_min": "Minutes", "calories_burned": "kcal burned"}),
                hide_index=True, width="stretch")
        else:
            st.caption("No exercise logged.")

# ---------------- Log food / exercise ----------------
with tab_log:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("🍽️ Log food")
        foods = conn.execute("SELECT * FROM foods ORDER BY category, name").fetchall()
        food_map = {f["food_id"]: f for f in foods}
        with st.form("log_food", clear_on_submit=True):
            fid = st.selectbox(
                "Food", list(food_map),
                format_func=lambda i: f"{food_map[i]['name']} — {food_map[i]['calories_per_100g']:.0f} kcal/100g "
                                      f"(serving {food_map[i]['serving_g']:.0f} g)")
            servings = st.number_input("Servings", 0.25, 20.0, 1.0, step=0.25)
            meal = st.selectbox("Meal", MEALS)
            fday = st.date_input("Date", date.today(), max_value=date.today(), key="food_day")
            if st.form_submit_button("Add food", type="primary"):
                f = food_map[fid]
                try:
                    row = db.log_food(conn, uid, fid, servings * f["serving_g"], meal, fday.isoformat())
                    st.success(f"Logged {f['name']}: {row['calories']:.0f} kcal, {row['protein_g']} g protein")
                except sqlite3.IntegrityError as e:
                    st.error(f"Not saved: {e}")

    with c2:
        st.subheader("🏃 Log exercise")
        exs = db.list_exercises(conn)
        ex_map = {e["exercise_id"]: e for e in exs}
        with st.form("log_ex", clear_on_submit=True):
            eid = st.selectbox("Exercise", list(ex_map),
                               format_func=lambda i: f"{ex_map[i]['name']} (MET {ex_map[i]['met_value']})")
            mins = st.number_input("Duration (minutes)", 1, 600, 30)
            eday = st.date_input("Date", date.today(), max_value=date.today(), key="ex_day")
            if st.form_submit_button("Add exercise", type="primary"):
                try:
                    row = db.log_exercise(conn, uid, eid, mins, eday.isoformat())
                    st.success(f"Logged {ex_map[eid]['name']}: {row['calories_burned']:.0f} kcal burned")
                except sqlite3.IntegrityError as e:
                    st.error(f"Not saved: {e}")

# ---------------- Weekly ----------------
with tab_week:
    rows = db.weekly_summary(conn, uid)
    if not rows:
        st.info("Nothing logged in the last 7 days.")
    else:
        df = pd.DataFrame([dict(r) for r in rows])
        chart = df.set_index("log_date")[["calories_in", "calories_out", "net_calories"]].rename(columns={
            "calories_in": "Calories in", "calories_out": "Burned", "net_calories": "Net"})
        if goal:
            chart["Target"] = goal["daily_calorie_target"]
        st.subheader("Last 7 days")
        st.line_chart(chart, height=320)

        on_track = int((df["status"] == "on track").sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("Days logged", len(df))
        c2.metric("Days on track", on_track)
        c3.metric("Avg net calories", f"{df['net_calories'].mean():.0f}")

        st.dataframe(
            df[["log_date", "calories_in", "calories_out", "net_calories", "target_calories",
                "protein_g", "active_minutes", "status"]].rename(columns={
                "log_date": "Date", "calories_in": "In", "calories_out": "Burned", "net_calories": "Net",
                "target_calories": "Target", "protein_g": "Protein (g)", "active_minutes": "Active min",
                "status": "Status"}),
            hide_index=True, width="stretch")

# ---------------- Team ----------------
with tab_team:
    mine = db.user_teams(conn, uid)
    c1, c2 = st.columns(2)
    with c1:
        with st.form("create_team", clear_on_submit=True):
            st.markdown("**Create a team**")
            tname = st.text_input("Team name")
            if st.form_submit_button("Create & join") and tname.strip():
                try:
                    tid = db.create_team(conn, tname.strip())
                    db.join_team(conn, tid, uid)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("A team with that name already exists.")
    with c2:
        others = [t for t in db.list_teams(conn) if t["team_id"] not in {m["team_id"] for m in mine}]
        with st.form("join_team"):
            st.markdown("**Join a team**")
            if others:
                tmap = {t["team_id"]: f"{t['name']} ({t['members']} members)" for t in others}
                jid = st.selectbox("Team", list(tmap), format_func=lambda i: tmap[i])
            else:
                jid = None
                st.caption("No other teams to join.")
            if st.form_submit_button("Join") and jid:
                db.join_team(conn, jid, uid)
                st.rerun()

    if not mine:
        st.info("Create or join a team to see the leaderboard.")
    else:
        tsel = st.selectbox("Leaderboard for", [t["team_id"] for t in mine],
                            format_func=lambda i: next(t["name"] for t in mine if t["team_id"] == i))
        board = pd.DataFrame([dict(r) for r in db.team_leaderboard(conn, tsel)])
        board.insert(0, "Rank", range(1, len(board) + 1))
        st.subheader("🏆 Last 7 days")
        st.dataframe(
            board[["Rank", "member", "days_logged", "days_on_track", "avg_net_calories",
                   "target_calories", "active_minutes"]].rename(columns={
                "member": "Member", "days_logged": "Days logged", "days_on_track": "Days on track",
                "avg_net_calories": "Avg net kcal", "target_calories": "Target", "active_minutes": "Active min"}),
            hide_index=True, width="stretch")
        st.bar_chart(board.set_index("member")[["days_on_track"]].rename(columns={"days_on_track": "Days on track"}),
                     height=250)

# ---------------- Weight ----------------
with tab_profile:
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("weight"):
            st.markdown("**Update weight**")
            new_w = st.number_input("Weight (kg)", 25.0, 300.0, float(user["weight_kg"]), step=0.1)
            if st.form_submit_button("Save", type="primary"):
                db.update_weight(conn, uid, new_w)
                st.success("Saved. Re-save your goal so the targets use your new weight.")
                st.rerun()
    with c2:
        hist = db.weight_history(conn, uid)
        if hist:
            wdf = pd.DataFrame([dict(h) for h in hist])
            wdf.index = [f"{d} #{i + 1}" for i, d in enumerate(wdf["recorded_on"])]
            chart = wdf[["weight_kg"]].rename(columns={"weight_kg": "Weight (kg)"})
            if goal and goal["target_weight_kg"]:
                chart["Target"] = goal["target_weight_kg"]
            st.line_chart(chart, height=300)

conn.close()
