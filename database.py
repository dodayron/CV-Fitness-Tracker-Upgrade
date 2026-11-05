import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path("pose_data.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise TEXT NOT NULL,
                reps INTEGER NOT NULL,
                sets INTEGER NOT NULL,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL
            )
        """)
        conn.commit()

def insert_session(exercise, reps, sets, date, start_time, end_time):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (exercise, reps, sets, date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (exercise, reps, sets, date, start_time, end_time))
        conn.commit()

def get_all_sessions():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY date DESC, start_time DESC")
        return cursor.fetchall()

def get_last_30_days_data():
    with get_connection() as conn:
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT date, exercise, SUM(reps) as total_reps
            FROM sessions WHERE date >= ? AND reps > 0
            GROUP BY date, exercise ORDER BY date ASC
        """, (cutoff,))
        daily_exercise = cursor.fetchall()

        cursor.execute("""
            SELECT DISTINCT date FROM sessions
            WHERE date >= ? AND reps > 0 ORDER BY date ASC
        """, (cutoff,))
        active_days = [row[0] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT exercise, SUM(reps) as total_reps, COUNT(*) as session_count
            FROM sessions WHERE date >= ? AND reps > 0
            GROUP BY exercise ORDER BY total_reps DESC
        """, (cutoff,))
        exercise_totals = cursor.fetchall()

        cursor.execute("""
            SELECT date, SUM(reps) as total_reps
            FROM sessions WHERE date >= ? AND reps > 0
            GROUP BY date ORDER BY date ASC
        """, (cutoff,))
        daily_totals = cursor.fetchall()

        return {
            "daily_exercise": daily_exercise,
            "active_days": active_days,
            "exercise_totals": exercise_totals,
            "daily_totals": daily_totals,
        }

def get_streak():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT date FROM sessions WHERE reps > 0 ORDER BY date DESC")
        dates = [row[0] for row in cursor.fetchall()]

    if not dates:
        return 0, 0

    date_objs = sorted(set(datetime.strptime(d, "%Y-%m-%d").date() for d in dates), reverse=True)
    today = datetime.now().date()

    current_streak = 0
    check = today
    for d in date_objs:
        if d == check or d == check - timedelta(days=1):
            current_streak += 1
            check = d
        elif d < check - timedelta(days=1):
            break

    longest = 1
    run = 1
    sorted_asc = sorted(date_objs)
    for i in range(1, len(sorted_asc)):
        if (sorted_asc[i] - sorted_asc[i-1]).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    return current_streak, longest
