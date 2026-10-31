"""Student Management System: Flask REST API + SQLite."""
import csv
import io
import re
import sqlite3
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

DB_PATH = Path(__file__).with_name("students.db")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
app = Flask(__name__)


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enrollment TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT,
                course TEXT NOT NULL, semester INTEGER NOT NULL,
                cgpa REAL NOT NULL, attendance REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
        )


def validate(d):
    """Return (clean_data, error). Server-side validation for every field."""
    try:
        out = {
            "enrollment": str(d.get("enrollment", "")).strip()[:20],
            "name": str(d.get("name", "")).strip()[:80],
            "email": str(d.get("email", "")).strip()[:100],
            "phone": str(d.get("phone", "")).strip()[:15],
            "course": str(d.get("course", "")).strip()[:60],
            "semester": int(d.get("semester")),
            "cgpa": float(d.get("cgpa")),
            "attendance": float(d.get("attendance")),
        }
    except (TypeError, ValueError):
        return None, "Semester, CGPA and attendance must be numbers"
    if not (out["enrollment"] and out["name"] and out["course"]):
        return None, "Enrollment no., name and course are required"
    if not EMAIL_RE.match(out["email"]):
        return None, "Enter a valid email address"
    if out["phone"] and not re.fullmatch(r"[0-9+\- ]{7,15}", out["phone"]):
        return None, "Phone number looks invalid"
    if not 1 <= out["semester"] <= 12:
        return None, "Semester must be between 1 and 12"
    if not 0 <= out["cgpa"] <= 10:
        return None, "CGPA must be between 0 and 10"
    if not 0 <= out["attendance"] <= 100:
        return None, "Attendance must be between 0 and 100"
    return out, None


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/students")
def list_students():
    q = request.args.get("q", "").strip()
    course = request.args.get("course", "").strip()
    sort = {"cgpa": "cgpa DESC", "attendance": "attendance DESC", "newest": "id DESC"}.get(
        request.args.get("sort"), "name COLLATE NOCASE")
    sql, args = "SELECT * FROM students WHERE 1=1", []
    if q:
        sql += " AND (name LIKE ? OR enrollment LIKE ? OR email LIKE ?)"
        args += [f"%{q}%"] * 3
    if course:
        sql += " AND course=?"
        args.append(course)
    with db() as c:
        rows = [dict(r) for r in c.execute(f"{sql} ORDER BY {sort}", args)]
        s = c.execute("SELECT COUNT(*) n, AVG(cgpa) g, AVG(attendance) a, "
                      "COALESCE(SUM(attendance<75),0) low FROM students").fetchone()
        courses = [dict(r) for r in c.execute(
            "SELECT course, COUNT(*) count FROM students GROUP BY course ORDER BY count DESC, course")]
    return jsonify(students=rows, courses=courses,
                   stats={"total": s["n"], "avg_cgpa": round(s["g"] or 0, 2),
                          "avg_attendance": round(s["a"] or 0, 1), "low_attendance": s["low"]})


@app.post("/api/students")
def add_student():
    data, err = validate(request.get_json(silent=True) or {})
    if err:
        return jsonify(error=err), 400
    try:
        with db() as c:
            cur = c.execute(
                "INSERT INTO students (enrollment,name,email,phone,course,semester,cgpa,attendance) "
                "VALUES (:enrollment,:name,:email,:phone,:course,:semester,:cgpa,:attendance)", data)
    except sqlite3.IntegrityError:
        return jsonify(error="A student with this enrollment number already exists"), 409
    return jsonify(id=cur.lastrowid), 201


@app.put("/api/students/<int:sid>")
def update_student(sid):
    data, err = validate(request.get_json(silent=True) or {})
    if err:
        return jsonify(error=err), 400
    try:
        with db() as c:
            cur = c.execute(
                "UPDATE students SET enrollment=:enrollment,name=:name,email=:email,phone=:phone,"
                "course=:course,semester=:semester,cgpa=:cgpa,attendance=:attendance WHERE id=:id",
                {**data, "id": sid})
    except sqlite3.IntegrityError:
        return jsonify(error="A student with this enrollment number already exists"), 409
    return (jsonify(ok=True), 200) if cur.rowcount else (jsonify(error="Student not found"), 404)


@app.delete("/api/students/<int:sid>")
def delete_student(sid):
    with db() as c:
        c.execute("DELETE FROM students WHERE id=?", (sid,))
    return jsonify(ok=True)


@app.get("/api/export")
def export_csv():
    def safe(v):  # block spreadsheet formula injection
        v = str(v)
        return "'" + v if v[:1] in "=+-@" else v
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Enrollment", "Name", "Email", "Phone", "Course", "Semester", "CGPA", "Attendance %"])
    with db() as c:
        for r in c.execute("SELECT * FROM students ORDER BY name COLLATE NOCASE"):
            w.writerow([safe(x) for x in (r["enrollment"], r["name"], r["email"], r["phone"],
                                          r["course"], r["semester"], r["cgpa"], r["attendance"])])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=students.csv"})


init_db()
if __name__ == "__main__":
    app.run(debug=True)
