import sqlite3
from pathlib import Path #module to handle file paths easily

DB_PATH = Path("pose_data.db") #defines the database file

def get_connection(): #function to make life easier
    return sqlite3.connect(DB_PATH) 
    
def init_db(): #initialise db
    with get_connection() as conn: #with closes connection automatically
        cursor = conn.cursor() # curosr is like sql command handle
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
    conn.commit() #writes change to storage
    
def insert_session(exercise, reps, sets, date, start_time, end_time): #a single write
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions
            (exercise, reps, sets, date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (exercise, reps, sets, date, start_time, end_time)) # ?s prevent SQL injection
        conn.commit() #writes, avoid data loss on power fail
        
def get_all_sessions(): #display func
    with get_connection() as conn: # Fixed: added parentheses to function call
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY date DESC, start_time DESC") #returns most recent sessions first
        return cursor.fetchall() #returns list
