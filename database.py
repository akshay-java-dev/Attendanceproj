
import os
import sqlite3
from pathlib import Path
from datetime import datetime
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "smartattend.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_no TEXT UNIQUE NOT NULL,
            email TEXT DEFAULT '',
            department TEXT DEFAULT '',
            photo_path TEXT DEFAULT '',
            face_embedding TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            attendance_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Present',
            FOREIGN KEY(student_id) REFERENCES students(id)
                ON DELETE CASCADE,
            UNIQUE(student_id, attendance_date)
        );
        """)

        # Create the initial admin only when no admin exists.
        # Set SMARTATTEND_ADMIN_USER and SMARTATTEND_ADMIN_PASSWORD
        # in your environment before the first run to customize it.
        username = os.environ.get("SMARTATTEND_ADMIN_USER", "admin")
        password = os.environ.get("SMARTATTEND_ADMIN_PASSWORD", "admin123")

        existing = conn.execute(
            "SELECT id FROM admins WHERE username = ?", (username,)
        ).fetchone()

        if not existing:
            conn.execute(
                "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password))
            )


def get_dashboard_stats():
    with get_connection() as conn:
        total_students = conn.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        total_attendance = conn.execute(
            "SELECT COUNT(*) FROM attendance"
        ).fetchone()[0]

        today_attendance = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE attendance_date = ?",
            (datetime.now().strftime("%Y-%m-%d"),)
        ).fetchone()[0]

    return total_students, total_attendance, today_attendance


def list_students(search=""):
    with get_connection() as conn:
        pattern = f"%{search.strip()}%"
        return conn.execute("""
            SELECT id, name, roll_no, email, department, created_at
            FROM students
            WHERE name LIKE ? OR roll_no LIKE ?
                  OR email LIKE ? OR department LIKE ?
            ORDER BY name COLLATE NOCASE
        """, (pattern, pattern, pattern, pattern)).fetchall()


def get_student(student_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM students WHERE id = ?", (student_id,)
        ).fetchone()


def save_student(name, roll_no, email, department, photo_path, embedding,
                 student_id=None):
    with get_connection() as conn:
        if student_id:
            conn.execute("""
                UPDATE students
                SET name=?, roll_no=?, email=?, department=?,
                    photo_path=?, face_embedding=?
                WHERE id=?
            """, (name, roll_no, email, department, photo_path,
                  embedding, student_id))
        else:
            conn.execute("""
                INSERT INTO students
                    (name, roll_no, email, department, photo_path,
                     face_embedding, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, roll_no, email, department, photo_path,
                  embedding, datetime.now().isoformat(timespec="seconds")))


def delete_student(student_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))


def get_registered_faces():
    with get_connection() as conn:
        return conn.execute("""
            SELECT id, name, roll_no, face_embedding
            FROM students
            WHERE face_embedding IS NOT NULL AND face_embedding != ''
        """).fetchall()


def mark_attendance(student_id):
    now = datetime.now()
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO attendance
                (student_id, attendance_date, attendance_time, status)
            VALUES (?, ?, ?, 'Present')
        """, (
            student_id,
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S")
        ))
        return cursor.rowcount == 1


def list_attendance(search=""):
    with get_connection() as conn:
        pattern = f"%{search.strip()}%"
        return conn.execute("""
            SELECT a.id, s.name, s.roll_no, s.department,
                   a.attendance_date, a.attendance_time, a.status
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            WHERE s.name LIKE ? OR s.roll_no LIKE ?
                  OR a.attendance_date LIKE ?
            ORDER BY a.attendance_date DESC, a.attendance_time DESC
        """, (pattern, pattern, pattern)).fetchall()


def delete_attendance(attendance_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM attendance WHERE id = ?", (attendance_id,)
        )


def get_admin(username):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM admins WHERE username = ?", (username,)
        ).fetchone()
