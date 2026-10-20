"""Phase 5b — Rule-based recommendation engine.

Looks at today's log + the last 7 days and returns practical tips that move the
user toward their goal (lose / maintain / gain).
"""
from datetime import date

import db
from calculator import tdee, KCAL_PER_KG_FAT


JUNK_FOODS = ("Samosa", "Biscuits", "Maggi noodles", "Cold drink", "Tea with sugar")


def suggest_foods(conn, max_kcal, mode="lean", limit=3):
    """Healthy foods whose one serving fits in the remaining calories.

    mode="lean"  -> most protein per calorie (for lose / maintain / protein gaps)
    mode="dense" -> most calories + protein per serving (for gaining weight)
    """
    order = {
        "lean": "protein_g / NULLIF(calories_per_100g, 0) DESC",
        "dense": "(calories_per_100g + protein_g * 10) * serving_g DESC",
    }[mode]
    placeholders = ",".join("?" * len(JUNK_FOODS))
    return conn.execute(f"""
        SELECT name, serving_g,
               ROUND(calories_per_100g * serving_g / 100) AS kcal,
               ROUND(protein_g * serving_g / 100, 1)     AS protein
        FROM foods
        WHERE calories_per_100g * serving_g / 100 <= ?
          AND name NOT IN ({placeholders})
        ORDER BY {order}
        LIMIT ?
    """, (max_kcal, *JUNK_FOODS, limit)).fetchall()


def burn_options(conn, excess_kcal, weight_kg, limit=3):
    """How many minutes of each exercise would burn the excess calories."""
    rows = conn.execute(
        "SELECT name, met_value FROM exercises WHERE name IN "
        "('Brisk walking','Cycling (moderate)','Skipping rope','Running (8 km/h)','Badminton') "
        "ORDER BY met_value").fetchall()
    out = []
    for r in rows[:limit]:
        kcal_per_min = r["met_value"] * weight_kg / 60
        out.append((r["name"], int(round(excess_kcal / kcal_per_min))))
    return out


def recommendations(conn, user_id, day=None):
    day = day or date.today().isoformat()
    user = db.get_user(conn, user_id)
    goal = db.active_goal(conn, user_id)
    recs = []

    if goal is None:
        return ["No goal set yet. Set a goal (lose / maintain / gain) to get personalised recommendations."]

    target, protein_target = goal["daily_calorie_target"], goal["protein_target_g"]
    s = db.daily_summary(conn, user_id, day)

    # ---- 1. Today's calories ----
    if s is None:
        recs.append(f"Nothing logged for {day}. Your target is {target} kcal and {protein_target} g protein.")
        recs.append("Start with a protein-rich breakfast, e.g. "
                    + ", ".join(f"{f['name']} ({f['kcal']:.0f} kcal)" for f in suggest_foods(conn, 400)) + ".")
    else:
        remaining = s["remaining_calories"]
        meals = {r["meal"] for r in db.food_log_for_day(conn, user_id, day)}
        day_is_over = "dinner" in meals or day < date.today().isoformat()
        if remaining > 150:
            mode = "dense" if goal["goal_type"] == "gain" else "lean"
            foods = suggest_foods(conn, remaining, mode)
            recs.append(f"You have {remaining:.0f} kcal left today. Good options that fit: "
                        + ", ".join(f"{f['name']} {f['serving_g']:.0f} g ({f['kcal']:.0f} kcal, {f['protein']} g protein)"
                                    for f in foods) + ".")
            if day_is_over and remaining > 0.35 * target:
                recs.append("You're far below your target. Eating too little slows metabolism and loses muscle "
                            "— don't skip your next meal.")
        elif remaining < -150:
            excess = -remaining
            opts = burn_options(conn, excess, user["weight_kg"])
            recs.append(f"You are {excess:.0f} kcal over your target. To balance it: "
                        + " OR ".join(f"{name} for ~{mins} min" for name, mins in opts) + ".")
            if goal["goal_type"] == "lose":
                recs.append("Tomorrow, swap one fried/packaged snack for fruit, sprouts or roasted chana.")
        else:
            recs.append(f"Great — you are on track today ({s['net_calories']:.0f} / {target} kcal net).")

        # ---- 2. Protein ----
        gap = protein_target - s["protein_g"]
        if gap > 10:
            rich = suggest_foods(conn, max(gap * 12, 150), "lean")
            recs.append(f"Protein is {s['protein_g']:.0f}/{protein_target} g — {gap:.0f} g short. Add: "
                        + ", ".join(f"{f['name']} (+{f['protein']} g)" for f in rich) + ".")

        # ---- 3. Macro balance ----
        p, c, f = s["protein_g"] * 4, s["carbs_g"] * 4, s["fat_g"] * 9
        total = p + c + f
        if total > 0:
            if f / total > 0.35:
                recs.append(f"Fat is {f / total:.0%} of your calories (aim for under 35%). Cut back on fried food and extra oil.")
            if c / total > 0.60:
                recs.append(f"Carbs are {c / total:.0%} of your calories. Replace part of the rice/roti with dal, paneer or eggs.")

        # ---- 4. Meal pattern ----
        if "breakfast" not in meals:
            recs.append("No breakfast logged. Skipping it often leads to overeating later in the day.")
        if s["active_minutes"] == 0:
            recs.append("No exercise logged today — even a 30-minute brisk walk helps.")

    # ---- 5. Weekly trend & projection ----
    week = db.weekly_summary(conn, user_id, day)
    if len(week) >= 3:
        avg_net = sum(r["net_calories"] for r in week) / len(week)
        maintenance = tdee(user)
        kg_per_week = (avg_net - maintenance) * 7 / KCAL_PER_KG_FAT
        on_track_days = sum(1 for r in week if r["status"] == "on track")
        recs.append(f"Last {len(week)} logged days: on track {on_track_days} days, average {avg_net:.0f} kcal net. "
                    f"Projected change: {kg_per_week:+.2f} kg/week.")

        gt = goal["goal_type"]
        if gt == "lose" and kg_per_week >= 0:
            recs.append("At this rate you won't lose weight. Bring your daily intake closer to your target.")
        elif gt == "lose" and kg_per_week < -1.0:
            recs.append("You are losing faster than 1 kg/week — that's too aggressive. Eat a little more.")
        elif gt == "gain" and kg_per_week <= 0:
            recs.append("You are not in a surplus. Add a calorie-dense snack (peanuts, banana + milk) daily.")
        elif gt == "maintain" and abs(kg_per_week) > 0.25:
            recs.append("Your intake is drifting away from maintenance. Aim closer to your target.")

        if goal["target_weight_kg"] and abs(kg_per_week) > 0.05:
            diff = goal["target_weight_kg"] - user["weight_kg"]
            if diff * kg_per_week > 0:   # moving in the right direction
                recs.append(f"At this pace you'll reach {goal['target_weight_kg']} kg in about "
                            f"{abs(diff / kg_per_week):.0f} weeks.")
    else:
        recs.append("Log at least 3 days to see your weekly trend and weight projection.")

    return recs
