"""
NextTwin Backend API Server
Pure Python - uses only stdlib (http.server, sqlite3, json, hashlib)
Run: python3 server.py
"""
import json
import sqlite3
import hashlib
import uuid
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Robust path setup — works regardless of cwd
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

from db.database import get_connection, init_db, row_to_dict, rows_to_list
from services.prediction_engine import (
    predict_cgpa, predict_placement_readiness,
    predict_skill_growth, simulate_scenario
)

# Dynamic PORT for Railway/Render deployment
PORT = int(os.environ.get("PORT", 8000))

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Content-Type": "application/json"
}

# Approximate letter-grade → percentage mapping (mirrors the frontend's GRADE_TO_MARKS).
# Only used internally so the AI prediction engine — which works on a 0-100 scale —
# has a number to reason with. The student always sees and enters the real grade.
GRADE_TO_MARKS = {
    "O": 95, "A+": 90, "A": 85, "B+": 75, "B": 65,
    "C+": 55, "C": 45, "D": 35, "E": 30, "F": 0,
    "QUALIFIED": 70, "PASS": 70, "NP": 70, "P": 70
}


def grade_to_marks(grade, default=70):
    if not grade:
        return default
    return GRADE_TO_MARKS.get(grade.strip().upper(), default)


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def get_demo_user_id():
    conn = get_connection()
    row = conn.execute("SELECT id FROM users WHERE email = 'demo@nexttwin.ai'").fetchone()
    conn.close()
    return row["id"] if row else None


class NextTwinHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        user_id = params.get("user_id", [None])[0] or get_demo_user_id()

        if path == "/api/health":
            self.send_json({"status": "ok", "service": "NextTwin API", "version": "1.0.0"})
        elif path == "/api/user/profile":
            self._get_profile(user_id)
        elif path == "/api/academic/records":
            self._get_academic_records(user_id)
        elif path == "/api/skills":
            self._get_skills(user_id)
        elif path == "/api/activities":
            self._get_activities(user_id)
        elif path == "/api/career-goals":
            self._get_career_goals(user_id)
        elif path == "/api/predict/cgpa":
            self._predict_cgpa(user_id)
        elif path == "/api/predict/placement":
            self._predict_placement(user_id)
        elif path == "/api/predict/skills":
            self._predict_skills(user_id)
        elif path == "/api/dashboard/summary":
            self._dashboard_summary(user_id)
        else:
            self.send_json({"error": "Route not found", "path": path}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        body = self.read_body()

        if path == "/api/auth/login":
            self._login(body)
        elif path == "/api/auth/register":
            self._register(body)
        elif path == "/api/scenario/simulate":
            self._simulate(body)
        elif path == "/api/skills/add":
            self._add_skill(body)
        elif path == "/api/academic/add":
            self._add_academic(body)
        elif path == "/api/academic/bulk-add":
            self._bulk_add_academic(body)
        elif path == "/api/activities/add":
            self._add_activity(body)
        elif path == "/api/career-goals/add":
            self._add_goal(body)
        elif path == "/api/user/update-profile":
            self._update_profile(body)
        else:
            self.send_json({"error": "Route not found"}, 404)

    def _get_profile(self, user_id):
        conn = get_connection()
        user = row_to_dict(conn.execute("SELECT id, name, email, branch, semester, cgpa FROM users WHERE id=?", (user_id,)).fetchone())
        conn.close()
        if not user:
            self.send_json({"error": "User not found"}, 404)
            return
        self.send_json({"user": user})

    def _get_academic_records(self, user_id):
        conn = get_connection()
        rows = rows_to_list(conn.execute(
            "SELECT * FROM academic_records WHERE user_id=? ORDER BY semester, subject", (user_id,)
        ).fetchall())
        conn.close()
        self.send_json({"records": rows, "count": len(rows)})

    def _get_skills(self, user_id):
        conn = get_connection()
        rows = rows_to_list(conn.execute(
            "SELECT * FROM skills WHERE user_id=? ORDER BY proficiency DESC", (user_id,)
        ).fetchall())
        conn.close()
        self.send_json({"skills": rows, "count": len(rows)})

    def _get_activities(self, user_id):
        conn = get_connection()
        rows = rows_to_list(conn.execute(
            "SELECT * FROM activities WHERE user_id=? ORDER BY date DESC", (user_id,)
        ).fetchall())
        conn.close()
        self.send_json({"activities": rows})

    def _get_career_goals(self, user_id):
        conn = get_connection()
        rows = rows_to_list(conn.execute(
            "SELECT * FROM career_goals WHERE user_id=?", (user_id,)
        ).fetchall())
        conn.close()
        self.send_json({"goals": rows})

    def _predict_cgpa(self, user_id):
        conn = get_connection()
        user = row_to_dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
        records = rows_to_list(conn.execute("SELECT * FROM academic_records WHERE user_id=?", (user_id,)).fetchall())
        conn.close()
        if not user:
            self.send_json({"error": "User not found"}, 404)
            return
        result = predict_cgpa(records, user["cgpa"], user["semester"])
        self.send_json(result)

    def _predict_placement(self, user_id):
        conn = get_connection()
        user = row_to_dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
        skills = rows_to_list(conn.execute("SELECT * FROM skills WHERE user_id=?", (user_id,)).fetchall())
        activities = rows_to_list(conn.execute("SELECT * FROM activities WHERE user_id=?", (user_id,)).fetchall())
        records = rows_to_list(conn.execute("SELECT * FROM academic_records WHERE user_id=?", (user_id,)).fetchall())
        conn.close()
        if not user:
            self.send_json({"error": "User not found"}, 404)
            return
        result = predict_placement_readiness(user, skills, activities, records)
        self.send_json(result)

    def _predict_skills(self, user_id):
        conn = get_connection()
        skills = rows_to_list(conn.execute("SELECT * FROM skills WHERE user_id=?", (user_id,)).fetchall())
        conn.close()
        result = predict_skill_growth(skills)
        self.send_json({"predictions": result})

    def _dashboard_summary(self, user_id):
        conn = get_connection()
        user = row_to_dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
        skills = rows_to_list(conn.execute("SELECT * FROM skills WHERE user_id=?", (user_id,)).fetchall())
        activities = rows_to_list(conn.execute("SELECT * FROM activities WHERE user_id=?", (user_id,)).fetchall())
        records = rows_to_list(conn.execute("SELECT * FROM academic_records WHERE user_id=?", (user_id,)).fetchall())
        goals = rows_to_list(conn.execute("SELECT * FROM career_goals WHERE user_id=?", (user_id,)).fetchall())
        conn.close()

        cgpa_pred = predict_cgpa(records, user["cgpa"] if user else 7.5, user["semester"] if user else 6)
        placement_pred = predict_placement_readiness(user or {}, skills, activities, records)

        self.send_json({
            "user": {k: user[k] for k in ("id","name","email","branch","semester","cgpa")} if user else {},
            "stats": {
                "total_skills": len(skills),
                "total_activities": len(activities),
                "total_subjects": len(records),
                "active_goals": len(goals)
            },
            "cgpa_prediction": cgpa_pred,
            "placement_prediction": placement_pred,
            "top_skills": sorted(skills, key=lambda s: s["proficiency"], reverse=True)[:5],
            "recent_activities": activities[:3],
            "career_goals": goals
        })

    def _simulate(self, body):
        scenario_type = body.get("scenario_type", "add_skill")
        params = body.get("params", {})
        user_id = body.get("user_id") or get_demo_user_id()

        conn = get_connection()
        user = row_to_dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
        skills = rows_to_list(conn.execute("SELECT * FROM skills WHERE user_id=?", (user_id,)).fetchall())
        activities = rows_to_list(conn.execute("SELECT * FROM activities WHERE user_id=?", (user_id,)).fetchall())
        records = rows_to_list(conn.execute("SELECT * FROM academic_records WHERE user_id=?", (user_id,)).fetchall())
        conn.close()

        placement = predict_placement_readiness(user or {}, skills, activities, records)
        user_data = {**(user or {}), "placement_score": placement["score"], "skills": skills}
        result = simulate_scenario(scenario_type, params, user_data)

        conn = get_connection()
        conn.execute(
            "INSERT INTO scenarios (id, user_id, scenario_name, scenario_type, input_params, predicted_outcome) VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4()), user_id, result.get("scenario","Scenario"), scenario_type,
             json.dumps(params), json.dumps(result))
        )
        conn.commit()
        conn.close()
        self.send_json(result)

    def _add_skill(self, body):
        user_id = body.get("user_id") or get_demo_user_id()
        conn = get_connection()
        conn.execute(
            "INSERT INTO skills (id, user_id, skill_name, proficiency, category, hours_practiced) VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4()), user_id, body["skill_name"], body.get("proficiency", 50),
             body.get("category", "General"), body.get("hours", 0))
        )
        conn.commit()
        conn.close()
        self.send_json({"message": "Skill added", "success": True})

    def _add_academic(self, body):
        user_id = body.get("user_id") or get_demo_user_id()
        subject = (body.get("subject") or "").strip()
        grade = (body.get("grade") or "").strip()
        marks = body.get("marks")
        if marks is None:
            marks = grade_to_marks(grade)
        conn = get_connection()
        conn.execute(
            "INSERT INTO academic_records (id, user_id, subject_code, subject, credits, grade, marks, max_marks, semester) VALUES (?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), user_id, body.get("subject_code", ""), subject,
             float(body.get("credits", 0) or 0), grade, int(marks),
             body.get("max_marks", 100), body["semester"])
        )
        conn.commit()
        conn.close()
        self.send_json({"message": "Record added", "success": True})

    def _bulk_add_academic(self, body):
        """Insert multiple academic records at once — used by the College Portal Import panel
        so a student can transcribe several subjects from a screenshot in one submit.
        Accepts the same fields shown on a typical grade sheet: subject_code, subject,
        credits, grade, semester. Marks (used internally by the AI engine) are derived
        from the grade automatically."""
        user_id = body.get("user_id") or get_demo_user_id()
        records = body.get("records", [])
        if not isinstance(records, list) or not records:
            self.send_json({"success": False, "error": "No records provided"}, 400)
            return

        conn = get_connection()
        inserted = 0
        skipped = 0
        for r in records:
            subject = (r.get("subject") or "").strip()
            semester = r.get("semester")
            grade = (r.get("grade") or "").strip()
            marks = r.get("marks")
            if marks is None:
                marks = grade_to_marks(grade)
            if not subject or semester is None:
                skipped += 1
                continue
            try:
                conn.execute(
                    "INSERT INTO academic_records (id, user_id, subject_code, subject, credits, grade, marks, max_marks, semester) VALUES (?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), user_id, r.get("subject_code", ""), subject,
                     float(r.get("credits", 0) or 0), grade, int(marks),
                     int(r.get("max_marks", 100)), int(semester))
                )
                inserted += 1
            except (ValueError, TypeError):
                skipped += 1
        conn.commit()
        conn.close()
        self.send_json({"success": True, "inserted": inserted, "skipped": skipped})

    def _add_activity(self, body):
        user_id = body.get("user_id") or get_demo_user_id()
        conn = get_connection()
        conn.execute(
            "INSERT INTO activities (id, user_id, activity_type, description, impact_score, date) VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4()), user_id, body["activity_type"], body.get("description",""),
             body.get("impact_score", 7), body.get("date", str(datetime.now().date())))
        )
        conn.commit()
        conn.close()
        self.send_json({"message": "Activity added", "success": True})

    def _add_goal(self, body):
        user_id = body.get("user_id") or get_demo_user_id()
        conn = get_connection()
        conn.execute(
            "INSERT INTO career_goals (id, user_id, target_role, target_company, target_salary, target_year) VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4()), user_id, body["target_role"], body.get("target_company",""),
             body.get("target_salary", 0), body.get("target_year", 2025))
        )
        conn.commit()
        conn.close()
        self.send_json({"message": "Goal added", "success": True})

    def _update_profile(self, body):
        user_id = body.get("user_id") or get_demo_user_id()
        fields = []
        values = []
        if "cgpa" in body:
            fields.append("cgpa=?")
            values.append(float(body["cgpa"]))
        if "semester" in body:
            fields.append("semester=?")
            values.append(int(body["semester"]))
        if "branch" in body:
            fields.append("branch=?")
            values.append(body["branch"])
        if not fields:
            self.send_json({"success": False, "error": "Nothing to update"}, 400)
            return
        values.append(user_id)
        conn = get_connection()
        conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=?", values)
        conn.commit()
        user = row_to_dict(conn.execute(
            "SELECT id, name, email, branch, semester, cgpa FROM users WHERE id=?", (user_id,)
        ).fetchone())
        conn.close()
        self.send_json({"success": True, "user": user})

    def _login(self, body):
        email = body.get("email","")
        password = body.get("password","")
        pw_hash = hash_password(password)
        conn = get_connection()
        user = row_to_dict(conn.execute(
            "SELECT id, name, email, branch, semester, cgpa FROM users WHERE email=? AND password_hash=?",
            (email, pw_hash)
        ).fetchone())
        conn.close()
        if user:
            self.send_json({"success": True, "user": user, "token": f"demo-token-{user['id'][:8]}"})
        else:
            self.send_json({"success": False, "error": "Invalid credentials"}, 401)

    def _register(self, body):
        user_id = str(uuid.uuid4())
        pw_hash = hash_password(body.get("password",""))
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO users (id, name, email, password_hash, branch, semester, cgpa) VALUES (?,?,?,?,?,?,?)",
                (user_id, body["name"], body["email"], pw_hash,
                 body.get("branch","CS"), int(body.get("semester",1)), float(body.get("cgpa",0)))
            )
            conn.commit()
            self.send_json({"success": True, "user_id": user_id, "message": "Registered successfully"})
        except sqlite3.IntegrityError:
            conn.rollback()
            self.send_json({"success": False, "error": "Email already exists"}, 409)
        except (KeyError, ValueError):
            conn.rollback()
            self.send_json({"success": False, "error": "Missing or invalid fields"}, 400)
        finally:
            conn.close()  # always release the connection so later writes are never blocked


if __name__ == "__main__":
    print("=" * 50)
    print("  NextTwin API Server")
    print("=" * 50)
    init_db()
    server = HTTPServer(("0.0.0.0", PORT), NextTwinHandler)
    print(f"  Server running at http://localhost:{PORT}")
    print(f"  API Base:          http://localhost:{PORT}/api")
    print(f"  Health Check:      http://localhost:{PORT}/api/health")
    print("=" * 50)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server stopped]")
