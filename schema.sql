-- =====================================================================
-- Calorie Tracking System — Database Schema (SQLite)
-- Phase 2: Tables + constraints (normalized to 3NF)
-- Phase 3: Triggers + views
-- =====================================================================
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- PHASE 2 — TABLES
-- ---------------------------------------------------------------------

-- A person using the app
CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL,
    email          TEXT    NOT NULL UNIQUE,
    gender         TEXT    NOT NULL CHECK (gender IN ('M', 'F')),
    age            INTEGER NOT NULL CHECK (age BETWEEN 10 AND 100),
    height_cm      REAL    NOT NULL CHECK (height_cm BETWEEN 100 AND 250),
    weight_kg      REAL    NOT NULL CHECK (weight_kg BETWEEN 25 AND 300),
    activity_level TEXT    NOT NULL DEFAULT 'light'
                   CHECK (activity_level IN ('sedentary','light','moderate','active','very_active')),
    created_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- A group of users (friends, hostel, gym batch) tracking together
CREATE TABLE IF NOT EXISTS teams (
    team_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Many-to-many: users <-> teams
CREATE TABLE IF NOT EXISTS team_members (
    team_id   INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    user_id   INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    joined_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id, user_id)
);

-- A user's fitness goal (only one active at a time — enforced by trigger)
CREATE TABLE IF NOT EXISTS goals (
    goal_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id              INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    goal_type            TEXT    NOT NULL CHECK (goal_type IN ('lose', 'maintain', 'gain')),
    target_weight_kg     REAL    CHECK (target_weight_kg IS NULL OR target_weight_kg BETWEEN 25 AND 300),
    daily_calorie_target INTEGER NOT NULL CHECK (daily_calorie_target BETWEEN 1000 AND 5000),
    protein_target_g     INTEGER NOT NULL CHECK (protein_target_g > 0),
    start_date           TEXT    NOT NULL DEFAULT (date('now', 'localtime')),
    is_active            INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

-- Food master data (nutrition per 100 g)
CREATE TABLE IF NOT EXISTS foods (
    food_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL UNIQUE,
    category          TEXT NOT NULL,
    serving_g         REAL NOT NULL CHECK (serving_g > 0),
    calories_per_100g REAL NOT NULL CHECK (calories_per_100g >= 0),
    protein_g         REAL NOT NULL CHECK (protein_g >= 0),
    carbs_g           REAL NOT NULL CHECK (carbs_g >= 0),
    fat_g             REAL NOT NULL CHECK (fat_g >= 0)
);

-- What a user ate (nutrition columns are filled by a trigger)
CREATE TABLE IF NOT EXISTS food_logs (
    log_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    food_id    INTEGER NOT NULL REFERENCES foods(food_id),
    log_date   TEXT    NOT NULL DEFAULT (date('now', 'localtime')),
    meal       TEXT    NOT NULL CHECK (meal IN ('breakfast', 'lunch', 'dinner', 'snack')),
    quantity_g REAL    NOT NULL CHECK (quantity_g > 0 AND quantity_g <= 2000),
    calories   REAL,
    protein_g  REAL,
    carbs_g    REAL,
    fat_g      REAL
);

-- Exercise master data (MET = metabolic equivalent of task)
CREATE TABLE IF NOT EXISTS exercises (
    exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    met_value   REAL NOT NULL CHECK (met_value > 0)
);

-- What exercise a user did (calories_burned filled by a trigger)
CREATE TABLE IF NOT EXISTS exercise_logs (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    exercise_id     INTEGER NOT NULL REFERENCES exercises(exercise_id),
    log_date        TEXT    NOT NULL DEFAULT (date('now', 'localtime')),
    duration_min    REAL    NOT NULL CHECK (duration_min > 0 AND duration_min <= 600),
    calories_burned REAL
);

-- Weight history (filled automatically by triggers)
CREATE TABLE IF NOT EXISTS weight_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    weight_kg   REAL    NOT NULL,
    recorded_on TEXT    NOT NULL DEFAULT (date('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_food_logs_user_date     ON food_logs(user_id, log_date);
CREATE INDEX IF NOT EXISTS idx_exercise_logs_user_date ON exercise_logs(user_id, log_date);

-- ---------------------------------------------------------------------
-- PHASE 3 — TRIGGERS
-- ---------------------------------------------------------------------

-- 1. Block logging food for a future date
CREATE TRIGGER IF NOT EXISTS trg_food_no_future
BEFORE INSERT ON food_logs
WHEN NEW.log_date > date('now', 'localtime')
BEGIN
    SELECT RAISE(ABORT, 'Cannot log food for a future date');
END;

-- 2. Auto-calculate nutrition when food is logged
CREATE TRIGGER IF NOT EXISTS trg_food_log_nutrition
AFTER INSERT ON food_logs
BEGIN
    UPDATE food_logs SET
        calories  = ROUND((SELECT calories_per_100g FROM foods WHERE food_id = NEW.food_id) * NEW.quantity_g / 100.0, 1),
        protein_g = ROUND((SELECT protein_g         FROM foods WHERE food_id = NEW.food_id) * NEW.quantity_g / 100.0, 1),
        carbs_g   = ROUND((SELECT carbs_g           FROM foods WHERE food_id = NEW.food_id) * NEW.quantity_g / 100.0, 1),
        fat_g     = ROUND((SELECT fat_g             FROM foods WHERE food_id = NEW.food_id) * NEW.quantity_g / 100.0, 1)
    WHERE log_id = NEW.log_id;
END;

-- 3. Recalculate nutrition if quantity is edited
CREATE TRIGGER IF NOT EXISTS trg_food_log_qty_update
AFTER UPDATE OF quantity_g ON food_logs
BEGIN
    UPDATE food_logs SET
        calories  = ROUND((SELECT calories_per_100g FROM foods WHERE food_id = NEW.food_id) * NEW.quantity_g / 100.0, 1),
        protein_g = ROUND((SELECT protein_g         FROM foods WHERE food_id = NEW.food_id) * NEW.quantity_g / 100.0, 1),
        carbs_g   = ROUND((SELECT carbs_g           FROM foods WHERE food_id = NEW.food_id) * NEW.quantity_g / 100.0, 1),
        fat_g     = ROUND((SELECT fat_g             FROM foods WHERE food_id = NEW.food_id) * NEW.quantity_g / 100.0, 1)
    WHERE log_id = NEW.log_id;
END;

-- 4. Auto-calculate calories burned:  MET x weight(kg) x hours
CREATE TRIGGER IF NOT EXISTS trg_exercise_calories
AFTER INSERT ON exercise_logs
BEGIN
    UPDATE exercise_logs SET calories_burned = ROUND(
        (SELECT met_value FROM exercises WHERE exercise_id = NEW.exercise_id)
      * (SELECT weight_kg FROM users     WHERE user_id     = NEW.user_id)
      * NEW.duration_min / 60.0, 1)
    WHERE log_id = NEW.log_id;
END;

-- 5. Record starting weight on registration
CREATE TRIGGER IF NOT EXISTS trg_user_initial_weight
AFTER INSERT ON users
BEGIN
    INSERT INTO weight_history(user_id, weight_kg) VALUES (NEW.user_id, NEW.weight_kg);
END;

-- 6. Record every weight change
CREATE TRIGGER IF NOT EXISTS trg_user_weight_change
AFTER UPDATE OF weight_kg ON users
WHEN OLD.weight_kg <> NEW.weight_kg
BEGIN
    INSERT INTO weight_history(user_id, weight_kg) VALUES (NEW.user_id, NEW.weight_kg);
END;

-- 7. Only one active goal per user: a new goal deactivates the old ones
CREATE TRIGGER IF NOT EXISTS trg_single_active_goal
AFTER INSERT ON goals
WHEN NEW.is_active = 1
BEGIN
    UPDATE goals SET is_active = 0
    WHERE user_id = NEW.user_id AND goal_id <> NEW.goal_id;
END;

-- ---------------------------------------------------------------------
-- PHASE 3 — VIEWS
-- ---------------------------------------------------------------------

-- Daily food totals per user
CREATE VIEW IF NOT EXISTS v_daily_intake AS
SELECT user_id, log_date,
       ROUND(SUM(calories), 1)  AS calories_in,
       ROUND(SUM(protein_g), 1) AS protein_g,
       ROUND(SUM(carbs_g), 1)   AS carbs_g,
       ROUND(SUM(fat_g), 1)     AS fat_g
FROM food_logs
GROUP BY user_id, log_date;

-- Daily exercise totals per user
CREATE VIEW IF NOT EXISTS v_daily_burn AS
SELECT user_id, log_date,
       ROUND(SUM(calories_burned), 1) AS calories_out,
       ROUND(SUM(duration_min))       AS active_minutes
FROM exercise_logs
GROUP BY user_id, log_date;

-- One row per user per day: intake, burn, net, target, status
CREATE VIEW IF NOT EXISTS v_daily_summary AS
WITH days AS (
    SELECT user_id, log_date FROM food_logs
    UNION
    SELECT user_id, log_date FROM exercise_logs
),
base AS (
    SELECT d.user_id, u.name, d.log_date,
           COALESCE(i.calories_in, 0)    AS calories_in,
           COALESCE(i.protein_g, 0)      AS protein_g,
           COALESCE(i.carbs_g, 0)        AS carbs_g,
           COALESCE(i.fat_g, 0)          AS fat_g,
           COALESCE(b.calories_out, 0)   AS calories_out,
           COALESCE(b.active_minutes, 0) AS active_minutes,
           g.daily_calorie_target        AS target_calories,
           g.protein_target_g            AS protein_target_g
    FROM days d
    JOIN users u            ON u.user_id = d.user_id
    LEFT JOIN v_daily_intake i ON i.user_id = d.user_id AND i.log_date = d.log_date
    LEFT JOIN v_daily_burn   b ON b.user_id = d.user_id AND b.log_date = d.log_date
    LEFT JOIN goals g          ON g.user_id = d.user_id AND g.is_active = 1
)
SELECT *,
       ROUND(calories_in - calories_out, 1)                   AS net_calories,
       ROUND(target_calories - (calories_in - calories_out), 1) AS remaining_calories,
       CASE
           WHEN target_calories IS NULL THEN 'no goal'
           WHEN ABS((calories_in - calories_out) - target_calories) <= target_calories * 0.10 THEN 'on track'
           WHEN (calories_in - calories_out) > target_calories THEN 'over'
           ELSE 'under'
       END AS status
FROM base;

-- Team leaderboard for the last 7 days
CREATE VIEW IF NOT EXISTS v_team_weekly AS
SELECT t.team_id, t.name AS team_name,
       u.user_id, u.name AS member,
       COUNT(s.log_date)                                      AS days_logged,
       SUM(CASE WHEN s.status = 'on track' THEN 1 ELSE 0 END) AS days_on_track,
       ROUND(AVG(s.net_calories))                             AS avg_net_calories,
       MAX(s.target_calories)                                 AS target_calories,
       ROUND(SUM(s.active_minutes))                           AS active_minutes
FROM teams t
JOIN team_members tm ON tm.team_id = t.team_id
JOIN users u         ON u.user_id  = tm.user_id
LEFT JOIN v_daily_summary s
       ON s.user_id = u.user_id
      AND s.log_date >= date('now', 'localtime', '-6 days')
GROUP BY t.team_id, u.user_id;
