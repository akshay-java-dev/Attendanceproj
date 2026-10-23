import os
import base64
import json
import secrets
import csv
import io
import time
from collections import deque
from threading import Lock
from pathlib import Path
from functools import wraps
from datetime import datetime

import cv2
import numpy as np
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, Response, abort, make_response
)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

import database as db


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
MODEL_DIR = BASE_DIR / "models"

UPLOAD_DIR.mkdir(exist_ok=True)
(MODEL_DIR / "unused").parent.mkdir(exist_ok=True)

DETECTOR_PATH = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
RECOGNIZER_PATH = MODEL_DIR / "face_recognition_sface_2021dec.onnx"

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SMARTATTEND_SECRET_KEY", secrets.token_hex(32)
)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Enable this when serving over HTTPS:
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("SMARTATTEND_HTTPS", "0") == "1"
)

db.create_tables()

_detector = None
_recognizer = None

# Events consumed by the separate camera kiosk popup.
attendance_events = deque(maxlen=50)
attendance_lock = Lock()
attendance_event_id = 0


def get_models():
    global _detector, _recognizer

    if _detector is None:
        if not DETECTOR_PATH.is_file() or not RECOGNIZER_PATH.is_file():
            raise RuntimeError(
                "Face models missing. Download both ONNX files into models/."
            )

        _detector = cv2.FaceDetectorYN.create(
            str(DETECTOR_PATH), "", (320, 320),
            0.85, 0.3, 5000
        )
        _recognizer = cv2.FaceRecognizerSF.create(
            str(RECOGNIZER_PATH), ""
        )

    return _detector, _recognizer


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def valid_image(file):
    return (
        file and file.filename
        and Path(file.filename).suffix.lower() in {".jpg", ".jpeg", ".png"}
    )


def extract_embedding(image_bytes):
    detector, recognizer = get_models()

    image = cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR
    )
    if image is None:
        raise ValueError("The uploaded file is not a valid image.")

    height, width = image.shape[:2]
    detector.setInputSize((width, height))
    _, faces = detector.detect(image)

    if faces is None or len(faces) == 0:
        raise ValueError("No face detected. Upload a clear front-facing photo.")

    if len(faces) > 1:
        raise ValueError("Upload a photo containing only one person.")

    face = faces[0]
    if face[2] < 70 or face[3] < 70:
        raise ValueError("The face is too small. Upload a closer photo.")

    aligned = recognizer.alignCrop(image, face)
    feature = recognizer.feature(aligned).flatten().astype(np.float32)
    feature /= max(float(np.linalg.norm(feature)), 1e-12)

    return feature


def get_match(feature):
    best_student = None
    best_score = -1.0

    for student in db.get_registered_faces():
        try:
            saved = np.asarray(
                json.loads(student["face_embedding"]), dtype=np.float32
            ).flatten()

            if saved.shape != feature.shape:
                continue

            score = float(np.dot(saved, feature))
            if score > best_score:
                best_score = score
                best_student = student
        except (ValueError, TypeError, json.JSONDecodeError):
            continue

    # Conservative initial threshold. Test and calibrate before real use.
    if best_student and best_score >= 0.40:
        return best_student, best_score

    return None, best_score


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_error):
    flash("Image too large. Maximum upload size is 5 MB.", "error")
    return redirect(request.referrer or url_for("students"))


@app.route("/")
def index():
    if session.get("admin_logged_in"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = db.get_admin(username)

        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_logged_in"] = True
            session["admin_username"] = admin["username"]

            target = request.args.get("next", "")
            if not target.startswith("/") or target.startswith("//"):
                target = url_for("dashboard")

            return redirect(target)

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@admin_required
def dashboard():
    total_students, total_attendance, today_attendance = db.get_dashboard_stats()
    return render_template(
        "dashboard.html",
        admin_username=session.get("admin_username", "Admin"),
        total_students=total_students,
        total_attendance=total_attendance,
        today_attendance=today_attendance
    )


@app.route("/students")
@admin_required
def students():
    search = request.args.get("q", "")
    return render_template(
        "students.html",
        students=db.list_students(search),
        search=search,
        admin_username=session.get("admin_username", "Admin")
    )


@app.route("/add-student", methods=["GET", "POST"])
@admin_required
def add_student():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll_no = request.form.get("roll_no", "").strip()
        email = request.form.get("email", "").strip()
        department = request.form.get("department", "").strip()
        photo = request.files.get("photo")
        captured_photo = request.form.get("captured_photo", "").strip()

        if not name or not roll_no or not department:
            flash("Name, roll number, and department are required.", "error")
            return redirect(url_for("add_student"))

        # The admin can either upload an image or capture one from the webcam.
        raw = None
        suffix = ".jpg"
        try:
            if captured_photo:
                # Accept only a browser-generated JPEG/PNG data URL.
                header, separator, encoded = captured_photo.partition(",")
                if not separator or header not in (
                    "data:image/jpeg;base64", "data:image/png;base64"
                ):
                    raise ValueError("Captured photo format is invalid. Please capture again.")
                raw = base64.b64decode(encoded, validate=True)
                suffix = ".png" if header == "data:image/png;base64" else ".jpg"
            elif photo and photo.filename:
                if not valid_image(photo):
                    raise ValueError("Upload a JPG or PNG face photo, or capture one from the camera.")
                raw = photo.read()
                suffix = Path(secure_filename(photo.filename)).suffix.lower()
            else:
                raise ValueError("Please upload a face photo or capture one using the camera.")

            if not raw:
                raise ValueError("The photo is empty. Please capture or upload it again.")
            if len(raw) > 5 * 1024 * 1024:
                raise ValueError("Image too large. Maximum image size is 5 MB.")

            embedding = extract_embedding(raw)
            filename = secrets.token_hex(16) + suffix
            destination = UPLOAD_DIR / filename
            destination.write_bytes(raw)

            try:
                db.save_student(
                    name, roll_no, email, department,
                    filename, json.dumps(embedding.tolist())
                )
            except Exception:
                destination.unlink(missing_ok=True)
                raise

            flash("Student registered successfully. Their face is ready for kiosk recognition.", "success")
            return redirect(url_for("students"))

        except (ValueError, RuntimeError) as exc:
            flash(str(exc), "error")
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                flash("That roll number already exists.", "error")
            else:
                app.logger.exception("Student registration failed")
                flash("Registration failed. Check the server log.", "error")

        return redirect(url_for("add_student"))

    return render_template("add_student.html", student=None, mode="add")


@app.route("/edit-student/<int:student_id>", methods=["GET", "POST"])
@admin_required
def edit_student(student_id):
    student = db.get_student(student_id)
    if not student:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll_no = request.form.get("roll_no", "").strip()
        email = request.form.get("email", "").strip()
        department = request.form.get("department", "").strip()
        photo = request.files.get("photo")

        if not name or not roll_no:
            flash("Name and roll number are required.", "error")
            return redirect(url_for("edit_student", student_id=student_id))

        photo_path = student["photo_path"]
        embedding_json = student["face_embedding"]
        new_path = None

        try:
            if photo and photo.filename:
                if not valid_image(photo):
                    raise ValueError("Upload a JPG or PNG face photo.")

                raw = photo.read()
                feature = extract_embedding(raw)
                filename = secrets.token_hex(16) + Path(
                    secure_filename(photo.filename)
                ).suffix.lower()
                new_path = UPLOAD_DIR / filename
                new_path.write_bytes(raw)
                photo_path = filename
                embedding_json = json.dumps(feature.tolist())

            db.save_student(
                name, roll_no, email, department,
                photo_path, embedding_json, student_id
            )

            if new_path and student["photo_path"]:
                (UPLOAD_DIR / student["photo_path"]).unlink(missing_ok=True)

            flash("Student updated successfully.", "success")
            return redirect(url_for("students"))

        except ValueError as exc:
            if new_path:
                new_path.unlink(missing_ok=True)
            flash(str(exc), "error")
        except Exception as exc:
            if new_path:
                new_path.unlink(missing_ok=True)
            if "UNIQUE constraint failed" in str(exc):
                flash("That roll number already exists.", "error")
            else:
                app.logger.exception("Student update failed")
                flash("Update failed. Check the server log.", "error")

        return redirect(url_for("edit_student", student_id=student_id))

    return render_template("student_form.html", student=student, mode="edit")


@app.route("/delete-student/<int:student_id>", methods=["POST"])
@admin_required
def delete_student(student_id):
    student = db.get_student(student_id)
    if student:
        db.delete_student(student_id)
        if student["photo_path"]:
            (UPLOAD_DIR / student["photo_path"]).unlink(missing_ok=True)
        flash("Student and attendance history deleted.", "success")
    return redirect(url_for("students"))


@app.route("/attendance")
@admin_required
def attendance():
    search = request.args.get("q", "")
    return render_template(
        "attendance.html",
        records=db.list_attendance(search),
        search=search,
        admin_username=session.get("admin_username", "Admin")
    )


@app.route("/delete-attendance/<int:attendance_id>", methods=["POST"])
@admin_required
def remove_attendance(attendance_id):
    db.delete_attendance(attendance_id)
    flash("Attendance record deleted.", "success")
    return redirect(url_for("attendance"))


@app.route("/reports/export.csv")
@admin_required
def export_report():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Roll Number", "Department",
        "Date", "Time", "Status"
    ])

    for record in db.list_attendance():
        writer.writerow([
            record["name"], record["roll_no"], record["department"],
            record["attendance_date"], record["attendance_time"],
            record["status"]
        ])

    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = (
        "attachment; filename=smartattend_report.csv"
    )
    return response


@app.route("/camera")
@admin_required
def camera():
    return render_template("camera.html")

# Separate camera-only attendance screen
@app.route("/kiosk")
def kiosk():
    return render_template("kiosk.html")


# Camera stream for the standalone kiosk
@app.route("/kiosk-video-feed")
def kiosk_video_feed():
    return Response(
        generate_camera_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

def generate_camera_frames():
    camera_device = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not camera_device.isOpened():
        camera_device.release()
        return

    last_marked = {}
    last_scan = 0.0

    try:
        detector, recognizer = get_models()

        while True:
            ok, frame = camera_device.read()
            if not ok:
                break

            height, width = frame.shape[:2]
            detector.setInputSize((width, height))

            # Limit expensive recognition work to roughly 4 times/second.
            now_tick = time.monotonic()
            if now_tick - last_scan >= 0.25:
                last_scan = now_tick
                _, faces = detector.detect(frame)

                if faces is not None:
                    for face in faces:
                        x, y, w, h = face[:4].astype(int)
                        aligned = recognizer.alignCrop(frame, face)
                        feature = recognizer.feature(aligned).flatten().astype(
                            np.float32
                        )
                        feature /= max(float(np.linalg.norm(feature)), 1e-12)

                        match, score = get_match(feature)
                        label = "Unknown"

                        if match:
                            label = match["name"]
                            student_id = int(match["id"])
                            current_date = datetime.now().strftime("%Y-%m-%d")

                            # Avoid repeated DB writes while a face remains
                            # visible. SQLite also enforces one record per day.
                            key = (student_id, current_date)
                            if key not in last_marked:
                                # Save attendance first, then publish a kiosk notification.
                                try:
                                    db.mark_attendance(student_id)
                                    last_marked[key] = now_tick
                                    global attendance_event_id
                                    with attendance_lock:
                                        attendance_event_id += 1
                                        attendance_events.append({
                                            "id": attendance_event_id,
                                            "student": str(match["name"]),
                                            "roll_no": str(match["roll_no"]),
                                            "message": "Attendance marked successfully!"
                                        })
                                except Exception:
                                    app.logger.exception("Could not mark attendance for student %s", student_id)

                        color = (40, 190, 100) if match else (40, 80, 230)
                        cv2.rectangle(
                            frame, (x, y), (x + w, y + h), color, 2
                        )
                        cv2.putText(
                            frame, label, (x, max(y - 10, 25)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2
                        )

            ok, buffer = cv2.imencode(".jpg", frame)
            if not ok:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes() + b"\r\n"
            )
    finally:
        camera_device.release()


@app.route("/kiosk-events")
def kiosk_events():
    """Return newly generated attendance notifications to the camera kiosk."""
    since = request.args.get("since", 0, type=int)
    with attendance_lock:
        events = [event for event in attendance_events if event["id"] > since]
        latest_id = attendance_event_id
    return {"events": events, "latest_id": latest_id}


@app.route("/video-feed")
@admin_required
def video_feed():
    return Response(
        generate_camera_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.errorhandler(404)
def not_found(error):
    app.logger.warning("404 error: %s", request.path)
    return render_template(
        "404.html",
        missing_path=request.path
    ), 404

if __name__ == "__main__":
    print("Starting SmartAttend...")
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)

