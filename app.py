from flask import Flask, render_template, jsonify, request
from database import get_all_sessions, init_db, get_last_30_days_data, get_streak
from datetime import datetime, timedelta

app = Flask(__name__)
init_db()

@app.route("/")
def index():
    sessions = get_all_sessions()
    grouped = {}
    for s in sessions:
        date = s[4]
        if date not in grouped:
            grouped[date] = []
        grouped[date].append(s)
    classic = request.args.get("classic") == "1"
    template = "index_o.html" if classic else "index.html"
    return render_template(template, sessions=sessions, grouped=grouped)

@app.route("/analytics")
def analytics():
    return render_template("analytics.html")

@app.route("/api/analytics-data")
def analytics_data():
    data = get_last_30_days_data()
    current_streak, longest_streak = get_streak()

    today = datetime.now().date()
    date_range = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]

    daily_totals_dict = {row[0]: row[1] for row in data["daily_totals"]}

    exercise_names = list(set(row[1] for row in data["daily_exercise"]))
    exercise_daily = {}
    for ex in exercise_names:
        exercise_daily[ex] = {d: 0 for d in date_range}
    for row in data["daily_exercise"]:
        date, exercise, reps = row
        if exercise in exercise_daily and date in exercise_daily[exercise]:
            exercise_daily[exercise][date] = reps

    total_reps_30 = sum(row[1] for row in data["exercise_totals"])
    active_days_count = len(data["active_days"])

    return jsonify({
        "date_range": date_range,
        "daily_totals": [daily_totals_dict.get(d, 0) for d in date_range],
        "exercise_daily": exercise_daily,
        "exercise_totals": [{"name": r[0], "reps": r[1]} for r in data["exercise_totals"]],
        "active_days": data["active_days"],
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_reps_30": total_reps_30,
        "active_days_count": active_days_count,
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
