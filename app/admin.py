import csv
import io
import random
import sqlite3
import socket
import string
import zipfile
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_socketio import join_room
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from app.db import get_db
from app.extensions import socketio


admin = Blueprint("admin", __name__, url_prefix="/admin")

COMMON_FILE_TYPES = [".py", ".txt", ".pdf", ".docx", ".zip"]
STATUS_LABELS = {
    "upcoming": "Upcoming",
    "ongoing": "Ongoing",
    "due-soon": "Due soon",
    "closed": "Closed",
}


def teacher_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("teacher_logged_in"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def parse_deadline(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def now_local():
    return datetime.now().replace(microsecond=0)


def status_for_deadline(deadline_value):
    deadline = parse_deadline(deadline_value)
    if deadline is None:
        return "closed"

    now = now_local()
    if deadline <= now:
        return "closed"
    if deadline <= now + timedelta(hours=24):
        return "due-soon"
    return "ongoing"


def normalize_file_types(values):
    if "any" in values:
        return "any"
    cleaned = []
    for value in values:
        value = value.strip().lower()
        if value in COMMON_FILE_TYPES and value not in cleaned:
            cleaned.append(value)
    return ",".join(cleaned) if cleaned else "any"


def split_file_types(value):
    if not value or value == "any":
        return ["any"]
    return [part.strip() for part in value.split(",") if part.strip()]


def generate_code():
    db = get_db()
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choice(alphabet) for _ in range(6))
        exists = db.execute("SELECT 1 FROM submissions WHERE code = ?", (code,)).fetchone()
        if not exists:
            return code


def student_file_name(row):
    return Path(row["file_path"]).name


def is_late(student_row, submission_row):
    submitted_at = parse_deadline(student_row["submitted_at"])
    deadline = parse_deadline(submission_row["deadline"])
    return bool(submitted_at and deadline and submitted_at > deadline)


def get_submission_or_404(submission_id):
    row = get_db().execute(
        """
        SELECT submissions.*, classes.name AS class_name
        FROM submissions
        JOIN classes ON classes.id = submissions.class_id
        WHERE submissions.id = ?
        """,
        (submission_id,),
    ).fetchone()
    if row is None:
        abort(404)
    return row


def remove_submission_files(submission_id):
    rows = get_db().execute(
        "SELECT file_path FROM student_submissions WHERE submission_id = ?",
        (submission_id,),
    ).fetchall()
    for row in rows:
        path = Path(row["file_path"])
        if path.exists():
            path.unlink()


def lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "localhost"


def build_student_submission_payload(student_row, submission_row):
    filename = student_file_name(student_row)
    return {
        "id": student_row["id"],
        "last_name": student_row["last_name"],
        "first_name": student_row["first_name"],
        "filename": filename,
        "submitted_at": student_row["submitted_at"],
        "is_late": is_late(student_row, submission_row),
        "download_url": url_for("admin.download_student_file", student_id=student_row["id"]),
    }


def emit_new_submission(submission_id, student_submission_id):
    submission = get_submission_or_404(submission_id)
    student_row = get_db().execute(
        "SELECT * FROM student_submissions WHERE id = ?",
        (student_submission_id,),
    ).fetchone()
    if student_row:
        socketio.emit(
            "new_submission",
            {
                "submission_id": submission_id,
                "student_submission": build_student_submission_payload(student_row, submission),
            },
            room=f"submission-{submission_id}",
        )


@socketio.on("join_submission")
def handle_join_submission(data):
    submission_id = data.get("submission_id") if isinstance(data, dict) else None
    if submission_id:
        join_room(f"submission-{submission_id}")


@admin.route("/")
def index():
    return redirect(url_for("admin.dashboard"))


@admin.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        password_hash = current_app.config["TEACHER_PASSWORD_HASH"]
        if check_password_hash(password_hash, password):
            session["teacher_logged_in"] = True
            return redirect(request.args.get("next") or url_for("admin.dashboard"))
        flash("That password did not match.", "error")
    return render_template("admin/login.html")


@admin.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@admin.route("/dashboard")
@teacher_required
def dashboard():
    db = get_db()
    submissions = db.execute("SELECT deadline FROM submissions").fetchall()
    stats = {"total": len(submissions), "ongoing": 0, "due-soon": 0, "upcoming": 0, "closed": 0}
    for row in submissions:
        stats[status_for_deadline(row["deadline"])] += 1

    recent = db.execute(
        """
        SELECT student_submissions.*, submissions.title, classes.name AS class_name
        FROM student_submissions
        JOIN submissions ON submissions.id = student_submissions.submission_id
        JOIN classes ON classes.id = submissions.class_id
        ORDER BY student_submissions.submitted_at DESC
        LIMIT 10
        """
    ).fetchall()
    return render_template("admin/dashboard.html", stats=stats, recent=recent, lan_ip=lan_ip())


@admin.route("/classes", methods=["GET", "POST"])
@teacher_required
def classes():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        file_types = normalize_file_types(request.form.getlist("file_types"))
        if not name:
            flash("Class name is required.", "error")
        else:
            try:
                db.execute(
                    "INSERT INTO classes (name, default_allowed_file_types) VALUES (?, ?)",
                    (name, file_types),
                )
                db.commit()
                flash("Class added.", "success")
                return redirect(url_for("admin.classes"))
            except sqlite3.IntegrityError:
                flash("A class with that name already exists.", "error")

    rows = db.execute(
        """
        SELECT classes.*, COUNT(submissions.id) AS submission_count
        FROM classes
        LEFT JOIN submissions ON submissions.class_id = classes.id
        GROUP BY classes.id
        ORDER BY classes.name
        """
    ).fetchall()
    return render_template(
        "admin/classes.html",
        classes=rows,
        common_file_types=COMMON_FILE_TYPES,
        split_file_types=split_file_types,
    )


@admin.route("/classes/<int:class_id>/edit", methods=["POST"])
@teacher_required
def edit_class(class_id):
    name = request.form.get("name", "").strip()
    file_types = normalize_file_types(request.form.getlist("file_types"))
    if not name:
        flash("Class name is required.", "error")
        return redirect(url_for("admin.classes"))

    db = get_db()
    db.execute(
        "UPDATE classes SET name = ?, default_allowed_file_types = ? WHERE id = ?",
        (name, file_types, class_id),
    )
    db.commit()
    flash("Class updated.", "success")
    return redirect(url_for("admin.classes"))


@admin.route("/classes/<int:class_id>/delete", methods=["POST"])
@teacher_required
def delete_class(class_id):
    db = get_db()
    count = db.execute(
        "SELECT COUNT(*) AS count FROM submissions WHERE class_id = ?",
        (class_id,),
    ).fetchone()["count"]
    if count:
        flash("This class has submissions tied to it, so it was not deleted.", "error")
    else:
        db.execute("DELETE FROM classes WHERE id = ?", (class_id,))
        db.commit()
        flash("Class deleted.", "success")
    return redirect(url_for("admin.classes"))


@admin.route("/submissions")
@teacher_required
def submissions():
    rows = get_db().execute(
        """
        SELECT submissions.*, classes.name AS class_name,
            COUNT(student_submissions.id) AS student_count
        FROM submissions
        JOIN classes ON classes.id = submissions.class_id
        LEFT JOIN student_submissions ON student_submissions.submission_id = submissions.id
        GROUP BY submissions.id
        ORDER BY submissions.deadline DESC
        """
    ).fetchall()
    return render_template("admin/submissions.html", rows=rows, status_for_deadline=status_for_deadline)


@admin.route("/submissions/new", methods=["GET", "POST"])
@teacher_required
def new_submission():
    db = get_db()
    class_rows = db.execute("SELECT * FROM classes ORDER BY name").fetchall()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        class_id = request.form.get("class_id")
        description = request.form.get("description", "").strip()
        deadline_text = request.form.get("deadline", "")
        deadline = parse_deadline(deadline_text)
        file_types = normalize_file_types(request.form.getlist("file_types"))

        if not title or not class_id or not deadline:
            flash("Title, class, and deadline are required.", "error")
        elif deadline <= now_local():
            flash("Deadline must be in the future.", "error")
        else:
            code = generate_code()
            cursor = db.execute(
                """
                INSERT INTO submissions
                    (title, class_id, description, allowed_file_types, deadline, code)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (title, class_id, description, file_types, deadline.isoformat(timespec="minutes"), code),
            )
            db.commit()
            return redirect(url_for("admin.submission_created", submission_id=cursor.lastrowid))

    return render_template(
        "admin/submission_form.html",
        classes=class_rows,
        common_file_types=COMMON_FILE_TYPES,
    )


@admin.route("/submissions/<int:submission_id>/created")
@teacher_required
def submission_created(submission_id):
    submission = get_submission_or_404(submission_id)
    return render_template("admin/submission_created.html", submission=submission)


@admin.route("/submissions/<int:submission_id>")
@teacher_required
def submission_detail(submission_id):
    db = get_db()
    submission = get_submission_or_404(submission_id)
    students = db.execute(
        """
        SELECT *
        FROM student_submissions
        WHERE submission_id = ?
        ORDER BY submitted_at DESC, last_name, first_name
        """,
        (submission_id,),
    ).fetchall()
    return render_template(
        "admin/submission_detail.html",
        submission=submission,
        students=students,
        status=status_for_deadline(submission["deadline"]),
        is_late=is_late,
        student_file_name=student_file_name,
    )


@admin.route("/submissions/<int:submission_id>/api")
@teacher_required
def submission_detail_api(submission_id):
    db = get_db()
    submission = get_submission_or_404(submission_id)
    students = db.execute(
        """
        SELECT *
        FROM student_submissions
        WHERE submission_id = ?
        ORDER BY submitted_at DESC, last_name, first_name
        """,
        (submission_id,),
    ).fetchall()
    
    students_data = []
    for student in students:
        students_data.append({
            "id": student["id"],
            "last_name": student["last_name"],
            "first_name": student["first_name"],
            "filename": student_file_name(student),
            "submitted_at": student["submitted_at"],
            "is_late": is_late(student, submission),
            "download_url": url_for("admin.download_student_file", student_id=student["id"]),
        })
    
    return jsonify({
        "id": submission["id"],
        "title": submission["title"],
        "class_name": submission["class_name"],
        "description": submission["description"],
        "deadline": submission["deadline"],
        "code": submission["code"],
        "status": status_for_deadline(submission["deadline"]),
        "students": students_data,
        "student_count": len(students_data),
        "download_all_url": url_for("admin.download_all", submission_id=submission_id),
        "export_csv_url": url_for("admin.export_submission", submission_id=submission_id),
    })


@admin.route("/submissions/<int:submission_id>/update", methods=["POST"])
@teacher_required
def update_submission(submission_id):
    submission = get_submission_or_404(submission_id)
    db = get_db()
    
    title = request.form.get("title", "").strip()
    deadline_text = request.form.get("deadline", "")
    description = request.form.get("description", "").strip()
    
    # Parse the deadline
    deadline = parse_deadline(deadline_text)
    
    if not title or not deadline:
        return jsonify({"error": "Title and deadline are required."}), 400
    
    try:
        db.execute(
            """
            UPDATE submissions
            SET title = ?, deadline = ?, description = ?
            WHERE id = ?
            """,
            (title, deadline.isoformat(timespec="minutes"), description, submission_id),
        )
        db.commit()
        return jsonify({
            "success": True,
            "message": "Submission updated successfully.",
            "submission": {
                "id": submission_id,
                "title": title,
                "deadline": deadline.isoformat(timespec="minutes"),
                "description": description,
                "status": status_for_deadline(deadline.isoformat(timespec="minutes")),
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin.route("/student-submissions/<int:student_id>/download")
@teacher_required
def download_student_file(student_id):
    row = get_db().execute(
        "SELECT * FROM student_submissions WHERE id = ?",
        (student_id,),
    ).fetchone()
    if row is None:
        abort(404)
    path = Path(row["file_path"])
    if not path.exists():
        abort(404)
    return send_file(path, as_attachment=True, download_name=path.name)


@admin.route("/submissions/<int:submission_id>/download-all")
@teacher_required
def download_all(submission_id):
    submission = get_submission_or_404(submission_id)
    rows = get_db().execute(
        "SELECT * FROM student_submissions WHERE submission_id = ? ORDER BY last_name, first_name",
        (submission_id,),
    ).fetchall()
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            path = Path(row["file_path"])
            if path.exists():
                archive.write(path, arcname=path.name)
    memory_file.seek(0)
    zip_name = secure_filename(f"{submission['title']}_files.zip") or "submission_files.zip"
    return send_file(memory_file, as_attachment=True, download_name=zip_name, mimetype="application/zip")


@admin.route("/submissions/<int:submission_id>/export.csv")
@teacher_required
def export_submission(submission_id):
    submission = get_submission_or_404(submission_id)
    rows = get_db().execute(
        "SELECT * FROM student_submissions WHERE submission_id = ? ORDER BY last_name, first_name",
        (submission_id,),
    ).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Last name", "First name", "Submitted at", "Filename", "Late"])
    for row in rows:
        writer.writerow(
            [
                row["last_name"],
                row["first_name"],
                row["submitted_at"],
                student_file_name(row),
                "yes" if is_late(row, submission) else "no",
            ]
        )
    filename = secure_filename(f"{submission['title']}_submissions.csv") or "submissions.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin.route("/submissions/<int:submission_id>/delete", methods=["GET", "POST"])
@teacher_required
def delete_submission(submission_id):
    submission = get_submission_or_404(submission_id)
    if request.method == "POST":
        db = get_db()
        remove_submission_files(submission_id)
        db.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
        db.commit()
        flash("Submission and uploaded files deleted.", "success")
        return redirect(url_for("admin.submissions"))
    # If someone navigates directly to the GET URL, redirect to submission detail
    return redirect(url_for("admin.submission_detail", submission_id=submission_id))


def save_uploaded_file(upload, class_id, submission_id, last_name, first_name):
    original = secure_filename(upload.filename or "")
    suffix = Path(original).suffix.lower()
    timestamp = now_local().strftime("%Y%m%d_%H%M%S")
    base_name = secure_filename(f"{last_name}_{first_name}") or "student"
    filename = f"{base_name}_{timestamp}{suffix}"
    folder = Path(current_app.config["UPLOAD_FOLDER"]) / str(class_id) / str(submission_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    upload.save(path)
    return str(path)
