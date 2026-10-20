"""Demo data: 3 sample users, one team and the last 7 days of food + exercise logs.

Used by the "Load demo data" button in the web app, or run directly:
    python demo.py
"""
import random
from datetime import date, timedelta

import db
import calculator as calc

DEMO_USERS = [
    # name, email, gender, age, height, weight, activity, goal, target weight
    ("Aarav (demo)", "aarav@demo.local", "M", 21, 178, 84, "light", "lose", 76),
    ("Diya (demo)", "diya@demo.local", "F", 20, 160, 54, "moderate", "maintain", None),
    ("Kabir (demo)", "kabir@demo.local", "M", 22, 172, 59, "light", "gain", 65),
]

# Typical meals: (meal, [(food name, servings range)])
MEAL_PLANS = {
    "breakfast": [[("Poha", (1, 1.5)), ("Tea with sugar", (1, 1))],
                  [("Idli", (3, 4)), ("Curd", (0.5, 1))],
                  [("Oats (dry)", (1, 1.5)), ("Milk (toned)", (1, 1)), ("Banana", (1, 1))],
                  [("Egg (boiled)", (2, 3)), ("Bread (brown)", (2, 2))]],
    "lunch": [[("Roti (wheat)", (2, 4)), ("Dal (cooked)", (1, 1.5)), ("Mixed veg sabzi", (1, 1))],
              [("Rice (cooked)", (1, 2)), ("Rajma (cooked)", (1, 1)), ("Salad (cucumber/tomato)", (1, 1))],
              [("Rice (cooked)", (1, 1.5)), ("Chicken breast", (1, 1)), ("Curd", (1, 1))]],
    "snack": [[("Samosa", (1, 2))], [("Roasted chana", (1, 1))], [("Apple", (1, 1))],
              [("Biscuits", (1, 2)), ("Tea with sugar", (1, 1))], [("Peanuts (roasted)", (1, 1))]],
    "dinner": [[("Roti (wheat)", (2, 3)), ("Paneer", (1, 1)), ("Palak (cooked)", (1, 1))],
               [("Rice (cooked)", (1, 2)), ("Dal (cooked)", (1, 1)), ("Egg (boiled)", (1, 2))],
               [("Roti (wheat)", (2, 3)), ("Chana (cooked)", (1, 1))]],
}
EXERCISE_CHOICES = [("Brisk walking", (20, 45)), ("Gym (weights)", (30, 60)), ("Cycling (moderate)", (20, 40)),
                    ("Badminton", (30, 60)), ("Yoga", (20, 30)), ("Running (8 km/h)", (15, 30))]


def load_demo(conn, days=7, seed=42):
    rng = random.Random(seed)
    foods = {r["name"]: r for r in conn.execute("SELECT * FROM foods")}
    exercises = {r["name"]: r["exercise_id"] for r in conn.execute("SELECT * FROM exercises")}
    team_row = conn.execute("SELECT team_id FROM teams WHERE name = 'Hostel Fitness Squad'").fetchone()
    team_id = team_row["team_id"] if team_row else db.create_team(conn, "Hostel Fitness Squad")

    user_ids = []
    for name, email, gender, age, h, w, act, goal_type, target_w in DEMO_USERS:
        existing = conn.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:          # already loaded
            user_ids.append(existing["user_id"])
            continue
        uid = db.add_user(conn, name, email, gender, age, h, w, act)
        user = db.get_user(conn, uid)
        db.set_goal(conn, uid, goal_type, calc.daily_calorie_target(user, goal_type),
                    calc.protein_target(user, goal_type), target_w)
        db.join_team(conn, team_id, uid)
        user_ids.append(uid)

        target = db.active_goal(conn, uid)["daily_calorie_target"]
        for d in range(days - 1, -1, -1):
            day = (date.today() - timedelta(days=d)).isoformat()
            is_today = d == 0

            burned = 0
            if rng.random() < 0.65:
                ex_name, (lo, hi) = rng.choice(EXERCISE_CHOICES)
                burned = db.log_exercise(conn, uid, exercises[ex_name], rng.randint(lo, hi), day)["calories_burned"]

            # pick the day's meals
            items = []
            for meal, options in MEAL_PLANS.items():
                if is_today and meal == "dinner":
                    continue                      # today is still in progress
                if meal == "snack" and rng.random() < 0.3:
                    continue
                for food_name, (lo, hi) in rng.choice(options):
                    items.append((meal, foods[food_name], rng.uniform(lo, hi)))

            # scale portions so net calories land near the target (most days on track,
            # some over / under), and today ~70% because dinner isn't logged yet
            aim = target * (0.7 if is_today else rng.choice([0.92, 0.97, 1.0, 1.03, 1.06, 1.18, 0.82])) + burned
            planned = sum(f["calories_per_100g"] * f["serving_g"] / 100 * s for _, f, s in items)
            factor = aim / planned if planned else 1
            for meal, f, s in items:
                grams = round(f["serving_g"] * s * factor / 5) * 5 or 5
                db.log_food(conn, uid, f["food_id"], min(grams, 2000), meal, day)
    return user_ids


if __name__ == "__main__":
    c = db.get_conn()
    db.init_db(c)
    print("Loaded demo users:", load_demo(c))
