"""Phase 5a — Goal calculations (BMR, TDEE, daily targets)."""

ACTIVITY_FACTOR = {
    "sedentary": 1.2,     # desk job, little movement
    "light": 1.375,       # light activity 1-3 days/week
    "moderate": 1.55,     # 3-5 days/week
    "active": 1.725,      # 6-7 days/week
    "very_active": 1.9,   # physical job / athlete
}

GOAL_ADJUSTMENT = {"lose": -500, "maintain": 0, "gain": 300}   # kcal/day
PROTEIN_PER_KG = {"lose": 1.6, "maintain": 1.2, "gain": 1.8}   # g per kg body weight
KCAL_PER_KG_FAT = 7700


def bmr(gender, weight_kg, height_cm, age):
    """Mifflin-St Jeor equation — calories burned at complete rest."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender == "M" else base - 161


def tdee(user):
    """Total daily energy expenditure = BMR x activity factor."""
    return bmr(user["gender"], user["weight_kg"], user["height_cm"], user["age"]) * ACTIVITY_FACTOR[user["activity_level"]]


def daily_calorie_target(user, goal_type):
    target = tdee(user) + GOAL_ADJUSTMENT[goal_type]
    safe_floor = 1500 if user["gender"] == "M" else 1200   # never go below a safe minimum
    return int(round(max(target, safe_floor)))


def protein_target(user, goal_type):
    return int(round(user["weight_kg"] * PROTEIN_PER_KG[goal_type]))


def bmi(user):
    h = user["height_cm"] / 100
    value = user["weight_kg"] / (h * h)
    if value < 18.5:
        label = "Underweight"
    elif value < 25:
        label = "Normal"
    elif value < 30:
        label = "Overweight"
    else:
        label = "Obese"
    return round(value, 1), label
