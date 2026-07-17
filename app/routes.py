from pathlib import Path

from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from app.admin import emit_new_submission, now_local, parse_deadline, save_uploaded_file, status_for_deadline
from app.db import get_db

main = Blueprint("main", __name__)


def normalize_code(value):
    return (value or "").strip().upper()


def get_submission_by_code(code):
    return get_db().execute(
        """
        SELECT submissions.*, classes.name AS class_name
        FROM submissions
        JOIN classes ON classes.id = submissions.class_id
        WHERE submissions.code = ?
        """,
        (code,),
    ).fetchone()


def allowed_extensions(value):
    if not value or value == "any":
        return None
    return {part.strip().lower() for part in value.split(",") if part.strip()}


def file_extension(filename):
    return Path(secure_filename(filename or "")).suffix.lower()


def validate_student_upload(submission, upload):
    if not upload or not upload.filename:
        return "Choose a file to upload."

    allowed = allowed_extensions(submission["allowed_file_types"])
    extension = file_extension(upload.filename)
    if allowed is not None and extension not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        return f"That file type is not allowed. Use: {allowed_text}."
    return None


@main.route("/")
def code_entry():
    return render_template("code_entry.html")


@main.route("/join", methods=["POST"])
def join_submission():
    code = normalize_code(request.form.get("code"))
    if not code:
        return render_template("code_entry.html", error="Enter the code your teacher gave you.")

    submission = get_submission_by_code(code)
    if submission is None:
        return render_template("code_entry.html", error="No submission was found for that code.")

    return redirect(url_for("main.student_submission", code=code))


@main.route("/submissions/<code>", methods=["GET", "POST"])
def student_submission(code):
    code = normalize_code(code)
    submission = get_submission_by_code(code)
    if submission is None:
        return render_template("code_entry.html", error="No submission was found for that code.")

    status = status_for_deadline(submission["deadline"])
    if request.method == "POST":
        last_name = request.form.get("last_name", "").strip()
        first_name = request.form.get("first_name", "").strip()
        upload = request.files.get("file")

        if status == "closed":
            flash("This submission is closed.", "error")
        elif not last_name or not first_name:
            flash("Enter both your first and last name.", "error")
        else:
            upload_error = validate_student_upload(submission, upload)
            if upload_error:
                flash(upload_error, "error")
            else:
                saved_path = save_uploaded_file(
                    upload,
                    submission["class_id"],
                    submission["id"],
                    last_name,
                    first_name,
                )
                submitted_at = now_local().isoformat(timespec="seconds")
                db = get_db()
                cursor = db.execute(
                    """
                    INSERT INTO student_submissions
                        (submission_id, last_name, first_name, file_path, submitted_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (submission["id"], last_name, first_name, saved_path, submitted_at),
                )
                db.commit()
                emit_new_submission(submission["id"], cursor.lastrowid)
                return redirect(url_for("main.submission_success", code=code))

    deadline = parse_deadline(submission["deadline"])
    allowed = allowed_extensions(submission["allowed_file_types"])
    accept = "" if allowed is None else ",".join(sorted(allowed))
    return render_template(
        "student_submission.html",
        submission=submission,
        status=status,
        deadline=deadline,
        accept=accept,
        allowed_label="Any file type" if allowed is None else ", ".join(sorted(allowed)),
    )


@main.route("/submissions/<code>/success")
def submission_success(code):
    code = normalize_code(code)
    submission = get_submission_by_code(code)
    if submission is None:
        return render_template("code_entry.html", error="No submission was found for that code.")
    return render_template("submission_success.html", submission=submission)
