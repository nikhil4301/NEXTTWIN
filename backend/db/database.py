"""
NextTwin - SQLite Database Manager
Uses Python's built-in sqlite3 module
"""
import sqlite3
import os
import uuid
import hashlib
import json
from datetime import datetime

# Use absolute paths based on this file's location — works from any cwd
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# On a host with a persistent disk/volume, set NEXTTWIN_DB to a path on that volume (e.g. /data/nexttwin.db)
DB_PATH = os.environ.get("NEXTTWIN_DB") or os.path.join(_THIS_DIR, "nexttwin.db")
SCHEMA_PATH = os.path.join(_THIS_DIR, "schema.sql")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_column(cur, table, column, coltype):
    """Add a column to an existing table if it's missing, without touching existing data."""
    cols = [r["name"] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db():
    """Initialize database with schema and seed data."""
    conn = get_connection()
    cur = conn.cursor()

    with open(SCHEMA_PATH, "r") as f:
        cur.executescript(f.read())

    # Migrate older databases created before subject_code/credits/grade existed
    _ensure_column(cur, "academic_records", "subject_code", "TEXT")
    _ensure_column(cur, "academic_records", "credits", "REAL DEFAULT 0")
    _ensure_column(cur, "academic_records", "grade", "TEXT")

    # Seed a demo user if not present
    existing = cur.execute("SELECT id FROM users WHERE email = 'demo@nexttwin.ai'").fetchone()
    if not existing:
        user_id = str(uuid.uuid4())
        pw_hash = hashlib.sha256("demo1234".encode()).hexdigest()
        cur.execute("""INSERT INTO users (id, name, email, password_hash, branch, semester, cgpa)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (user_id, "Arjun Sharma", "demo@nexttwin.ai", pw_hash, "Computer Science", 6, 8.4))

        # Academic records
        def _grade_for(marks):
            if marks >= 90: return "A+"
            if marks >= 80: return "A"
            if marks >= 75: return "B+"
            if marks >= 65: return "B"
            if marks >= 55: return "C+"
            if marks >= 45: return "C"
            return "D"

        subjects = [
            ("21CSH301", "Data Structures", 88, 5, 4),
            ("21CSH302", "Algorithms", 82, 5, 4),
            ("21CSH303", "DBMS", 91, 5, 3),
            ("21CSH304", "OS", 78, 5, 4),
            ("21CSH305", "CN", 85, 5, 3),
            ("21CSH401", "Machine Learning", 92, 6, 4),
            ("21CSH402", "Web Development", 87, 6, 3),
            ("21CSH403", "Cloud Computing", 79, 6, 3),
            ("21CSH404", "Cyber Security", 83, 6, 3),
            ("21CSH405", "AI", 90, 6, 4),
        ]
        for code, subj, marks, sem, credits in subjects:
            cur.execute("""INSERT INTO academic_records (id, user_id, subject_code, subject, credits, grade, marks, semester)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (str(uuid.uuid4()), user_id, code, subj, credits, _grade_for(marks), marks, sem))

        # Skills
        skills_data = [
            ("Python", 85, "Programming", 320),
            ("JavaScript", 70, "Programming", 180),
            ("SQL", 78, "Database", 150),
            ("Machine Learning", 65, "AI/ML", 200),
            ("React", 60, "Frontend", 120),
            ("Data Structures", 80, "CS Fundamentals", 250),
            ("System Design", 45, "Architecture", 60),
            ("Communication", 72, "Soft Skills", 40),
        ]
        for name, prof, cat, hrs in skills_data:
            cur.execute("""INSERT INTO skills (id, user_id, skill_name, proficiency, category, hours_practiced)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (str(uuid.uuid4()), user_id, name, prof, cat, hrs))

        # Career goals
        cur.execute("""INSERT INTO career_goals (id, user_id, target_role, target_company, target_salary, target_year)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), user_id, "ML Engineer", "Google", 1800000, 2025))

        # Activities
        activities_data = [
            ("hackathon", "Won Smart India Hackathon 2024", 9.0, "2024-03-15"),
            ("internship", "Internship at TCS – Data Analytics", 8.5, "2024-05-01"),
            ("certification", "AWS Cloud Practitioner Certified", 7.0, "2024-07-20"),
            ("project", "Built an NLP Sentiment Analyzer", 8.0, "2024-08-10"),
            ("course", "Completed Deep Learning Specialization", 7.5, "2024-09-01"),
        ]
        for atype, desc, impact, date in activities_data:
            cur.execute("""INSERT INTO activities (id, user_id, activity_type, description, impact_score, date)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (str(uuid.uuid4()), user_id, atype, desc, impact, date))

    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")
    return True


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows):
    return [dict(r) for r in rows]
