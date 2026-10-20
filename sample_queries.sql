-- =====================================================================
-- Sample queries for viva / interviews
-- Open with:  sqlite3 calorie_tracker.db   then   .read sample_queries.sql
-- =====================================================================
.headers on
.mode column

-- 1. INNER JOIN: everything user 1 ate today with food names
SELECT fl.meal, f.name, fl.quantity_g, fl.calories
FROM food_logs fl
JOIN foods f ON f.food_id = fl.food_id
WHERE fl.user_id = 1 AND fl.log_date = date('now', 'localtime');

-- 2. VIEW: daily summary (intake, burn, net, target, status)
SELECT log_date, name, calories_in, calories_out, net_calories, target_calories, status
FROM v_daily_summary
ORDER BY log_date DESC, name;

-- 3. GROUP BY + HAVING: users averaging over their target this week
SELECT name, ROUND(AVG(net_calories)) AS avg_net, MAX(target_calories) AS target
FROM v_daily_summary
WHERE log_date >= date('now', 'localtime', '-6 days')
GROUP BY user_id
HAVING AVG(net_calories) > MAX(target_calories);

-- 4. Subquery: foods with above-average protein per 100 g
SELECT name, protein_g
FROM foods
WHERE protein_g > (SELECT AVG(protein_g) FROM foods)
ORDER BY protein_g DESC;

-- 5. Top 5 most-eaten foods across all users
SELECT f.name, COUNT(*) AS times_logged, ROUND(SUM(fl.calories)) AS total_kcal
FROM food_logs fl
JOIN foods f ON f.food_id = fl.food_id
GROUP BY f.food_id
ORDER BY times_logged DESC
LIMIT 5;

-- 6. Calories by meal type (where do calories come from?)
SELECT meal, ROUND(SUM(calories)) AS kcal,
       ROUND(100.0 * SUM(calories) / (SELECT SUM(calories) FROM food_logs), 1) AS pct
FROM food_logs
GROUP BY meal
ORDER BY kcal DESC;

-- 7. LEFT JOIN: users who have NOT logged anything today
SELECT u.name
FROM users u
LEFT JOIN food_logs fl
       ON fl.user_id = u.user_id AND fl.log_date = date('now', 'localtime')
WHERE fl.log_id IS NULL;

-- 8. Team leaderboard view
SELECT team_name, member, days_logged, days_on_track, avg_net_calories, active_minutes
FROM v_team_weekly
ORDER BY team_name, days_on_track DESC;

-- 9. Window function: running total of calories through the day
SELECT fl.log_date, fl.meal, f.name, fl.calories,
       SUM(fl.calories) OVER (PARTITION BY fl.user_id, fl.log_date ORDER BY fl.log_id) AS running_total
FROM food_logs fl JOIN foods f ON f.food_id = fl.food_id
WHERE fl.user_id = 1
ORDER BY fl.log_date, fl.log_id;

-- 10. Weight change since registration (uses trigger-filled weight_history)
SELECT u.name,
       (SELECT weight_kg FROM weight_history w WHERE w.user_id = u.user_id ORDER BY id ASC  LIMIT 1) AS start_kg,
       u.weight_kg AS current_kg,
       ROUND(u.weight_kg - (SELECT weight_kg FROM weight_history w WHERE w.user_id = u.user_id ORDER BY id LIMIT 1), 1) AS change_kg
FROM users u;

-- 11. Trigger demo: this fails with "Cannot log food for a future date"
-- INSERT INTO food_logs(user_id, food_id, log_date, meal, quantity_g) VALUES (1, 1, '2099-01-01', 'lunch', 80);

-- 12. Constraint demo: this fails the CHECK (quantity_g > 0)
-- INSERT INTO food_logs(user_id, food_id, meal, quantity_g) VALUES (1, 1, 'lunch', -50);
