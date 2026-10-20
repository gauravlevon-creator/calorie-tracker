"""Phase 4 — Data access layer: connection, setup and all CRUD queries."""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from seed_data import FOODS, EXERCISES

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "calorie_tracker.db"


def get_conn(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    """Create tables/triggers/views and load master data (safe to run repeatedly)."""
    conn.executescript((BASE_DIR / "schema.sql").read_text())
    conn.executemany(
        "INSERT OR IGNORE INTO foods(name, category, serving_g, calories_per_100g, protein_g, carbs_g, fat_g) "
        "VALUES (?,?,?,?,?,?,?)", FOODS)
    conn.executemany("INSERT OR IGNORE INTO exercises(name, met_value) VALUES (?,?)", EXERCISES)
    conn.commit()


# ---------------- Users ----------------
def add_user(conn, name, email, gender, age, height_cm, weight_kg, activity_level="light"):
    cur = conn.execute(
        "INSERT INTO users(name, email, gender, age, height_cm, weight_kg, activity_level) VALUES (?,?,?,?,?,?,?)",
        (name, email, gender, age, height_cm, weight_kg, activity_level))
    conn.commit()
    return cur.lastrowid


def get_user(conn, user_id):
    return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def list_users(conn):
    return conn.execute("SELECT user_id, name, email FROM users ORDER BY user_id").fetchall()


def update_weight(conn, user_id, weight_kg):
    conn.execute("UPDATE users SET weight_kg = ? WHERE user_id = ?", (weight_kg, user_id))
    conn.commit()


def weight_history(conn, user_id):
    return conn.execute(
        "SELECT recorded_on, weight_kg FROM weight_history WHERE user_id = ? ORDER BY id", (user_id,)).fetchall()


# ---------------- Goals ----------------
def set_goal(conn, user_id, goal_type, calorie_target, protein_target, target_weight=None):
    cur = conn.execute(
        "INSERT INTO goals(user_id, goal_type, target_weight_kg, daily_calorie_target, protein_target_g) "
        "VALUES (?,?,?,?,?)", (user_id, goal_type, target_weight, calorie_target, protein_target))
    conn.commit()
    return cur.lastrowid


def active_goal(conn, user_id):
    return conn.execute("SELECT * FROM goals WHERE user_id = ? AND is_active = 1", (user_id,)).fetchone()


# ---------------- Food & exercise ----------------
def search_foods(conn, text):
    return conn.execute(
        "SELECT food_id, name, serving_g, calories_per_100g FROM foods WHERE name LIKE ? ORDER BY name",
        (f"%{text}%",)).fetchall()


def get_food(conn, food_id):
    return conn.execute("SELECT * FROM foods WHERE food_id = ?", (food_id,)).fetchone()


def list_exercises(conn):
    return conn.execute("SELECT * FROM exercises ORDER BY name").fetchall()


def log_food(conn, user_id, food_id, quantity_g, meal, log_date=None):
    log_date = log_date or date.today().isoformat()
    cur = conn.execute(
        "INSERT INTO food_logs(user_id, food_id, log_date, meal, quantity_g) VALUES (?,?,?,?,?)",
        (user_id, food_id, log_date, meal, quantity_g))
    conn.commit()
    return conn.execute("SELECT * FROM food_logs WHERE log_id = ?", (cur.lastrowid,)).fetchone()


def log_exercise(conn, user_id, exercise_id, duration_min, log_date=None):
    log_date = log_date or date.today().isoformat()
    cur = conn.execute(
        "INSERT INTO exercise_logs(user_id, exercise_id, log_date, duration_min) VALUES (?,?,?,?)",
        (user_id, exercise_id, log_date, duration_min))
    conn.commit()
    return conn.execute("SELECT * FROM exercise_logs WHERE log_id = ?", (cur.lastrowid,)).fetchone()


def food_log_for_day(conn, user_id, day):
    # JOIN between logs and food master data
    return conn.execute("""
        SELECT fl.meal, f.name, fl.quantity_g, fl.calories, fl.protein_g
        FROM food_logs fl JOIN foods f ON f.food_id = fl.food_id
        WHERE fl.user_id = ? AND fl.log_date = ?
        ORDER BY CASE fl.meal WHEN 'breakfast' THEN 1 WHEN 'lunch' THEN 2
                              WHEN 'snack' THEN 3 ELSE 4 END
    """, (user_id, day)).fetchall()


def exercise_log_for_day(conn, user_id, day):
    return conn.execute("""
        SELECT e.name, el.duration_min, el.calories_burned
        FROM exercise_logs el JOIN exercises e ON e.exercise_id = el.exercise_id
        WHERE el.user_id = ? AND el.log_date = ?
    """, (user_id, day)).fetchall()


# ---------------- Reports (use views) ----------------
def daily_summary(conn, user_id, day):
    return conn.execute(
        "SELECT * FROM v_daily_summary WHERE user_id = ? AND log_date = ?", (user_id, day)).fetchone()


def weekly_summary(conn, user_id, end_day=None, days=7):
    end = date.fromisoformat(end_day) if end_day else date.today()
    start = end - timedelta(days=days - 1)
    return conn.execute(
        "SELECT * FROM v_daily_summary WHERE user_id = ? AND log_date BETWEEN ? AND ? ORDER BY log_date",
        (user_id, start.isoformat(), end.isoformat())).fetchall()


# ---------------- Teams (groups) ----------------
def create_team(conn, name):
    cur = conn.execute("INSERT INTO teams(name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid


def list_teams(conn):
    return conn.execute("""
        SELECT t.team_id, t.name, COUNT(tm.user_id) AS members
        FROM teams t LEFT JOIN team_members tm ON tm.team_id = t.team_id
        GROUP BY t.team_id ORDER BY t.name
    """).fetchall()


def join_team(conn, team_id, user_id):
    conn.execute("INSERT OR IGNORE INTO team_members(team_id, user_id) VALUES (?,?)", (team_id, user_id))
    conn.commit()


def user_teams(conn, user_id):
    return conn.execute("""
        SELECT t.team_id, t.name FROM teams t
        JOIN team_members tm ON tm.team_id = t.team_id WHERE tm.user_id = ?
    """, (user_id,)).fetchall()


def team_leaderboard(conn, team_id):
    return conn.execute("""
        SELECT * FROM v_team_weekly WHERE team_id = ?
        ORDER BY days_on_track DESC, days_logged DESC, active_minutes DESC
    """, (team_id,)).fetchall()
