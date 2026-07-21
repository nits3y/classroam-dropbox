"""Exam / quiz feature (ported from Fucursa).

This module replaces Fucursa's JSON-file "database" (teachers.json,
exams.json, questions.json, student_responses.json) with SQLite tables
that live in the same database as the rest of Classroom Dropbox
(instance/classroom_dropbox.sqlite3, see app/db.py).

There is no separate "teachers" table: Classroom Dropbox already has a
single shared teacher login (CLASSROOM_TEACHER_PASSWORD_HASH) guarding
everything under teacher_required(), so exams are just scoped to a
class the same way `submissions` already are.
"""

import json
import random
import string
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_socketio import join_room

from app.db import get_db
from app.extensions import socketio

exams_bp = Blueprint("exams", __name__, url_prefix="/exams")
public_exams_bp = Blueprint("public_exams", __name__)
admin_exams_bp = Blueprint("admin_exams", __name__, url_prefix="/admin/exams")

QUESTION_TYPES = {
    "multiple-choice",
    "true-false",
    "short-answer",
    "identification",
    "essay",
    "word-bank",
}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def teacher_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("teacher_logged_in"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def now_local():
    return datetime.now().replace(microsecond=0)


def normalize_code(value):
    return (value or "").strip().upper()


def generate_exam_code():
    db = get_db()
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choice(alphabet) for _ in range(6))
        exists = db.execute("SELECT 1 FROM exams WHERE code = ?", (code,)).fetchone()
        if not exists:
            return code


def get_default_exam_class_id():
    db = get_db()
    existing = db.execute("SELECT id FROM classes ORDER BY id LIMIT 1").fetchone()
    if existing:
        return existing["id"]
    cursor = db.execute(
        "INSERT INTO classes (name, default_allowed_file_types) VALUES (?, ?)",
        ("General", "any"),
    )
    db.commit()
    return cursor.lastrowid


def dump_answers(answers_dict):
    return json.dumps(answers_dict or {})


def load_answers(answers_text):
    try:
        return json.loads(answers_text or "{}")
    except (TypeError, ValueError):
        return {}


def dump_options(options_list):
    return json.dumps(options_list) if options_list else None


def load_options(options_text):
    if not options_text:
        return []
    try:
        return json.loads(options_text)
    except (TypeError, ValueError):
        return []


def extract_import_questions_payload(parsed):
    if isinstance(parsed, list):
        return parsed, None

    if isinstance(parsed, dict):
        questions_payload = parsed.get("questions")
        if isinstance(questions_payload, list):
            return questions_payload, None
        return None, "JSON payload must include a questions array."

    return None, "JSON payload must be an array of questions or an object with a questions array."


def normalize_imported_questions(parsed):
    questions_payload, payload_error = extract_import_questions_payload(parsed)
    if payload_error:
        return [], [payload_error]

    items = questions_payload if isinstance(questions_payload, list) else [questions_payload]
    type_map = {
        "Multiple Choice": "multiple-choice",
        "True/False": "true-false",
        "Short Answer": "short-answer",
        "Identification": "identification",
        "Essay": "essay",
        "Word Bank": "word-bank",
    }
    normalized = []
    errors = []

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"Item {index}: must be a question object")
            continue

        missing = [
            field
            for field in ("questionType", "questionText", "points")
            if item.get(field) in (None, "")
        ]
        if missing:
            errors.append(f"Item {index}: missing {', '.join(missing)}")
            continue

        q_type_raw = (item.get("questionType") or "").strip()
        q_type = type_map.get(q_type_raw)
        if not q_type or q_type not in QUESTION_TYPES:
            errors.append(f"Item {index}: invalid questionType '{q_type_raw}'")
            continue

        question_text = (item.get("questionText") or "").strip()
        if not question_text:
            errors.append(f"Item {index}: missing questionText")
            continue

        try:
            points = int(item.get("points"))
        except (TypeError, ValueError):
            errors.append(f"Item {index}: points must be a number")
            continue

        if q_type == "word-bank":
            options_list = item.get("wordBank")
            correct_answers = item.get("correctAnswer")
            if not isinstance(options_list, list):
                errors.append(f"Item {index}: Word Bank questions require a wordBank array")
                continue
            if not isinstance(correct_answers, list) or not correct_answers:
                errors.append(f"Item {index}: Word Bank questions require a non-empty correctAnswer array")
                continue
            correct_answer = json.dumps(correct_answers)
        elif q_type == "multiple-choice":
            options_list = item.get("answerOptions")
            if not isinstance(options_list, list):
                errors.append(f"Item {index}: Multiple Choice questions require an answerOptions array")
                continue
            correct_answer = (item.get("correctAnswer") or "").strip()
            if not correct_answer:
                errors.append(f"Item {index}: Multiple Choice questions require a non-empty correctAnswer")
                continue
        else:
            options_list = None
            correct_answer = (item.get("correctAnswer") or "").strip()

        time_limit_seconds = item.get("timeLimitSeconds")
        if time_limit_seconds is not None:
            try:
                time_limit_seconds = int(time_limit_seconds)
            except (TypeError, ValueError):
                errors.append(f"Item {index}: timeLimitSeconds must be a number")
                continue

        normalized.append({
            "question": question_text,
            "q_type": q_type,
            "options": options_list,
            "correct_answer": correct_answer,
            "points": points,
            "explanation": (item.get("explanation") or "").strip(),
            "time_limit_seconds": time_limit_seconds,
        })

    return normalized, errors


def import_questions_for_exam(exam_id, parsed, starting_sort_order=0):
    questions, errors = normalize_imported_questions(parsed)
    sort_order = starting_sort_order
    for question in questions:
        ExamStore.create_question(
            exam_id=exam_id,
            question=question["question"],
            q_type=question["q_type"],
            options=question["options"],
            correct_answer=question["correct_answer"],
            points=question["points"],
            explanation=question["explanation"],
            sort_order=sort_order,
            time_limit_seconds=question["time_limit_seconds"],
        )
        sort_order += 1
    return len(questions), errors


# ---------------------------------------------------------------------------
# Data-access layer (drop-in replacement for Fucursa's Database class)
# ---------------------------------------------------------------------------

class ExamStore:
    """SQLite equivalent of Fucursa's src/lib/database.ts Database class.

    Methods intentionally mirror the original names/shape (get/create/
    update/delete per entity) so the porting mapping stays obvious:
        Database.getExams()          -> ExamStore.get_exams()
        Database.getExamById(id)     -> ExamStore.get_exam(id)
        Database.createExam(data)    -> ExamStore.create_exam(...)
        etc.
    """

    # -- Exams --------------------------------------------------------

    @staticmethod
    def get_exams(class_id=None):
        db = get_db()
        if class_id is not None:
            return db.execute(
                "SELECT * FROM exams WHERE class_id = ? ORDER BY created_at DESC",
                (class_id,),
            ).fetchall()
        return db.execute("SELECT * FROM exams ORDER BY created_at DESC").fetchall()

    @staticmethod
    def get_exam(exam_id):
        return get_db().execute("SELECT * FROM exams WHERE id = ?", (exam_id,)).fetchone()

    @staticmethod
    def get_exam_by_code(code):
        return get_db().execute("SELECT * FROM exams WHERE code = ?", (code,)).fetchone()

    @staticmethod
    def create_exam(class_id, title, description="", instructions="",
                     time_limit_seconds=1800, time_limit_enabled=True,
                     max_attempts=1, status="draft"):
        db = get_db()
        code = generate_exam_code()
        now = now_local().isoformat(timespec="seconds")
        cursor = db.execute(
            """
            INSERT INTO exams
                (class_id, title, description, instructions, time_limit_seconds,
                 time_limit_enabled, code, status, max_attempts, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (class_id, title, description, instructions, time_limit_seconds,
             int(bool(time_limit_enabled)), code, status, max_attempts, now, now),
        )
        db.commit()
        return ExamStore.get_exam(cursor.lastrowid)

    @staticmethod
    def update_exam(exam_id, **fields):
        if not fields:
            return ExamStore.get_exam(exam_id)
        fields["updated_at"] = now_local().isoformat(timespec="seconds")
        columns = ", ".join(f"{key} = ?" for key in fields)
        db = get_db()
        db.execute(f"UPDATE exams SET {columns} WHERE id = ?", (*fields.values(), exam_id))
        db.commit()
        return ExamStore.get_exam(exam_id)

    @staticmethod
    def delete_exam(exam_id):
        db = get_db()
        db.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
        db.commit()
        return True

    # -- Questions ------------------------------------------------------

    @staticmethod
    def get_questions(exam_id):
        rows = get_db().execute(
            "SELECT * FROM exam_questions WHERE exam_id = ? ORDER BY sort_order, id",
            (exam_id,),
        ).fetchall()
        return rows

    @staticmethod
    def get_question(question_id):
        return get_db().execute(
            "SELECT * FROM exam_questions WHERE id = ?", (question_id,)
        ).fetchone()

    @staticmethod
    def create_question(exam_id, question, q_type, options=None, correct_answer=None,
                         points=1, explanation="", is_required=True, sort_order=0,
                         time_limit_seconds=None):
        if q_type not in QUESTION_TYPES:
            raise ValueError(f"Unknown question type: {q_type}")
        db = get_db()
        now = now_local().isoformat(timespec="seconds")
        cursor = db.execute(
            """
            INSERT INTO exam_questions
                (exam_id, question, type, options, correct_answer, explanation,
                 points, is_required, sort_order, time_limit_seconds, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (exam_id, question, q_type, dump_options(options), correct_answer,
             explanation, points, int(bool(is_required)), sort_order,
             time_limit_seconds, now, now),
        )
        db.commit()
        return ExamStore.get_question(cursor.lastrowid)

    @staticmethod
    def update_question(question_id, **fields):
        if "options" in fields:
            fields["options"] = dump_options(fields["options"])
        if not fields:
            return ExamStore.get_question(question_id)
        fields["updated_at"] = now_local().isoformat(timespec="seconds")
        columns = ", ".join(f"{key} = ?" for key in fields)
        db = get_db()
        db.execute(
            f"UPDATE exam_questions SET {columns} WHERE id = ?",
            (*fields.values(), question_id),
        )
        db.commit()
        return ExamStore.get_question(question_id)

    @staticmethod
    def delete_question(question_id):
        db = get_db()
        db.execute("DELETE FROM exam_questions WHERE id = ?", (question_id,))
        db.commit()
        return True

    # -- Attempts (formerly "student responses") -------------------------

    @staticmethod
    def get_attempts(exam_id):
        return get_db().execute(
            "SELECT * FROM exam_attempts WHERE exam_id = ? ORDER BY submitted_at DESC, started_at DESC",
            (exam_id,),
        ).fetchall()

    @staticmethod
    def get_attempt(attempt_id):
        return get_db().execute(
            "SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,)
        ).fetchone()

    @staticmethod
    def count_attempts(exam_id, last_name, first_name):
        row = get_db().execute(
            """
            SELECT COUNT(*) AS n FROM exam_attempts
            WHERE exam_id = ? AND last_name = ? AND first_name = ?
              AND excluded_from_attempt_count = 0
            """,
            (exam_id, last_name, first_name),
        ).fetchone()
        return row["n"] if row else 0

    @staticmethod
    def is_locked_out(exam_id, last_name, first_name):
        row = get_db().execute(
            """
            SELECT COUNT(*) AS n FROM exam_attempts
            WHERE exam_id = ? AND last_name = ? AND first_name = ?
              AND is_locked_out = 1
              AND excluded_from_attempt_count = 0
            """,
            (exam_id, last_name, first_name),
        ).fetchone()
        return bool(row and row["n"])

    @staticmethod
    def start_attempt(exam_id, last_name, first_name):
        db = get_db()
        now = now_local().isoformat(timespec="seconds")
        cursor = db.execute(
            """
            INSERT INTO exam_attempts
                (exam_id, last_name, first_name, answers, started_at, status)
            VALUES (?, ?, ?, '{}', ?, 'in-progress')
            """,
            (exam_id, last_name, first_name, now),
        )
        db.commit()
        return ExamStore.get_attempt(cursor.lastrowid)

    @staticmethod
    def save_answer(attempt_id, question_id, answer_text):
        attempt = ExamStore.get_attempt(attempt_id)
        if attempt is None:
            return None
        answers = load_answers(attempt["answers"])
        answers[str(question_id)] = answer_text
        db = get_db()
        db.execute(
            "UPDATE exam_attempts SET answers = ? WHERE id = ?",
            (dump_answers(answers), attempt_id),
        )
        db.commit()
        return ExamStore.get_attempt(attempt_id)

    @staticmethod
    def flag_warning(attempt_id):
        db = get_db()
        db.execute(
            "UPDATE exam_attempts SET security_warnings = security_warnings + 1 WHERE id = ?",
            (attempt_id,),
        )
        db.commit()

        attempt = ExamStore.get_attempt(attempt_id)
        if attempt is None:
            return None

        exam = ExamStore.get_exam(attempt["exam_id"])
        max_warnings = exam["max_security_warnings"] if exam and exam["max_security_warnings"] else 3

        if attempt["status"] == "in-progress" and attempt["security_warnings"] >= max_warnings:
            ExamStore.submit_attempt(attempt_id, is_auto_submitted=True)
            db.execute(
                "UPDATE exam_attempts SET is_locked_out = 1 WHERE id = ?",
                (attempt_id,),
            )
            db.commit()
            attempt = ExamStore.get_attempt(attempt_id)

        return attempt

    @staticmethod
    def submit_attempt(attempt_id, is_auto_submitted=False):
        attempt = ExamStore.get_attempt(attempt_id)
        if attempt is None:
            return None
        questions = ExamStore.get_questions(attempt["exam_id"])
        answers = load_answers(attempt["answers"])

        score = 0
        total_points = 0
        needs_manual_grading = False
        for question in questions:
            total_points += question["points"]
            if question["type"] == "essay":
                needs_manual_grading = True
                continue
            if question["type"] == "word-bank":
                try:
                    given_list = json.loads((answers.get(str(question["id"])) or "[]"))
                    correct_list = json.loads((question["correct_answer"] or "[]"))
                    if len(given_list) == len(correct_list) and all(
                        g.strip().lower() == c.strip().lower() for g, c in zip(given_list, correct_list)
                    ):
                        score += question["points"]
                except (json.JSONDecodeError, TypeError, AttributeError):
                    pass
            else:
                given = (answers.get(str(question["id"])) or "").strip().lower()
                correct = (question["correct_answer"] or "").strip().lower()
                if correct and given == correct:
                    score += question["points"]

        db = get_db()
        now = now_local().isoformat(timespec="seconds")
        status = "submitted" if needs_manual_grading else "graded"
        db.execute(
            """
            UPDATE exam_attempts
            SET score = ?, total_points = ?, is_auto_submitted = ?,
                status = ?, submitted_at = ?
            WHERE id = ?
            """,
            (score, total_points, int(bool(is_auto_submitted)), status, now, attempt_id),
        )
        db.commit()
        return ExamStore.get_attempt(attempt_id)

    @staticmethod
    def grade_attempt(attempt_id, score):
        db = get_db()
        db.execute(
            "UPDATE exam_attempts SET score = ?, status = 'graded' WHERE id = ?",
            (score, attempt_id),
        )
        db.commit()
        return ExamStore.get_attempt(attempt_id)


def emit_attempt_update(exam_id, attempt_id):
    attempt = ExamStore.get_attempt(attempt_id)
    if attempt:
        socketio.emit(
            "exam_attempt_update",
            {
                "exam_id": exam_id,
                "attempt": {
                    "id": attempt["id"],
                    "last_name": attempt["last_name"],
                    "first_name": attempt["first_name"],
                    "status": attempt["status"],
                    "security_warnings": attempt["security_warnings"],
                    "score": attempt["score"],
                    "total_points": attempt["total_points"],
                    "submitted_at": attempt["submitted_at"],
                },
            },
            room=f"exam-{exam_id}",
        )


@socketio.on("join_exam_room")
def handle_join_exam_room(data):
    exam_id = data.get("exam_id") if isinstance(data, dict) else None
    if exam_id:
        join_room(f"exam-{exam_id}")


# ---------------------------------------------------------------------------
# Student-facing routes
# ---------------------------------------------------------------------------

@exams_bp.route("/join", methods=["POST"])
def join_exam():
    code = normalize_code(request.form.get("code"))
    exam = ExamStore.get_exam_by_code(code) if code else None
    if exam is None or exam["status"] != "active":
        flash("No active exam was found for that code.", "error")
        return redirect(url_for("main.code_entry"))
    return redirect(url_for("exams.take_exam", code=code))


@exams_bp.route("/<code>", methods=["GET", "POST"])
def take_exam(code):
    code = normalize_code(code)
    exam = ExamStore.get_exam_by_code(code)
    if exam is None or exam["status"] != "active":
        flash("No active exam was found for that code.", "error")
        return redirect(url_for("main.code_entry"))

    questions = ExamStore.get_questions(exam["id"])
    attempt_id = session.get(f"exam_attempt_{exam['id']}")
    attempt = ExamStore.get_attempt(attempt_id) if attempt_id else None

    if attempt and attempt["status"] != "in-progress":
        if attempt["is_locked_out"]:
            return redirect(url_for("exams.exam_locked", code=code))
        return redirect(url_for("exams.exam_success", code=code))

    if request.method == "POST":
        if attempt is None:
            last_name = request.form.get("last_name", "").strip()
            first_name = request.form.get("first_name", "").strip()
            if not last_name or not first_name:
                flash("Enter both your first and last name.", "error")
                return render_template("exams/take_exam.html", exam=exam, questions=questions, attempt=None)

            if ExamStore.is_locked_out(exam["id"], last_name, first_name):
                flash(
                    "Your exam was locked due to repeated security warnings. Ask your teacher to grant you a new attempt.",
                    "error",
                )
                return render_template("exams/take_exam.html", exam=exam, questions=questions, attempt=None)

            if ExamStore.count_attempts(exam["id"], last_name, first_name) >= exam["max_attempts"]:
                flash("You have already used your allowed attempts for this exam.", "error")
                return render_template("exams/take_exam.html", exam=exam, questions=questions, attempt=None)

            attempt = ExamStore.start_attempt(exam["id"], last_name, first_name)
            session[f"exam_attempt_{exam['id']}"] = attempt["id"]
            return render_template(
                "exams/take_exam.html", exam=exam, questions=questions, attempt=attempt
            )

        # Already-started attempt: this POST is the final submit.
        for question in questions:
            answer = request.form.get(f"question_{question['id']}", "")
            ExamStore.save_answer(attempt["id"], question["id"], answer)

        is_auto_submitted = request.form.get("auto_submitted") == "1"
        ExamStore.submit_attempt(attempt["id"], is_auto_submitted=is_auto_submitted)
        emit_attempt_update(exam["id"], attempt["id"])
        session.pop(f"exam_attempt_{exam['id']}", None)
        return redirect(url_for("exams.exam_success", code=code))

    return render_template("exams/take_exam.html", exam=exam, questions=questions, attempt=attempt)


@exams_bp.route("/<code>/warning", methods=["POST"])
def flag_warning(code):
    """Called by the client-side anti-cheat guard (tab switch, exited fullscreen)."""
    code = normalize_code(code)
    exam = ExamStore.get_exam_by_code(code)
    if exam is None:
        abort(404)
    attempt_id = session.get(f"exam_attempt_{exam['id']}")
    if not attempt_id:
        abort(400)
    attempt = ExamStore.flag_warning(attempt_id)
    emit_attempt_update(exam["id"], attempt_id)

    max_warnings = exam["max_security_warnings"] if exam and exam["max_security_warnings"] else 4
    warnings_left = max(0, max_warnings - attempt["security_warnings"])
    response = {
        "security_warnings": attempt["security_warnings"],
        "warnings_left": warnings_left,
        "locked": attempt["is_locked_out"] == 1,
        "locked_url": url_for("exams.exam_locked", code=code),
    }
    return response


@exams_bp.route("/<code>/locked")
def exam_locked(code):
    code = normalize_code(code)
    exam = ExamStore.get_exam_by_code(code)
    if exam is None:
        abort(404)
    attempt_id = session.get(f"exam_attempt_{exam['id']}")
    attempt = ExamStore.get_attempt(attempt_id) if attempt_id else None
    if attempt is None or not attempt["is_locked_out"]:
        flash("Exam session is not locked out.", "error")
        return redirect(url_for("exams.take_exam", code=code))
    return render_template("exams/exam_locked.html", exam=exam, attempt=attempt)


@exams_bp.route("/<code>/success")
def exam_success(code):
    code = normalize_code(code)
    exam = ExamStore.get_exam_by_code(code)
    if exam is None:
        abort(404)
    return render_template("exams/exam_success.html", exam=exam)


# ---------------------------------------------------------------------------
# Teacher-facing routes
# ---------------------------------------------------------------------------

@admin_exams_bp.route("/")
@teacher_required
def list_exams():
    exams = ExamStore.get_exams()
    classes = get_db().execute("SELECT * FROM classes ORDER BY name").fetchall()
    return render_template("admin/exams.html", exams=exams, classes=classes)


@admin_exams_bp.route("/new", methods=["POST"])
@teacher_required
def create_exam():
    exam_mode = request.form.get("exam_mode", "manual")
    json_raw = request.form.get("questions_json", "").strip()
    parsed_questions = None
    json_payload = None
    class_id = get_default_exam_class_id()

    if exam_mode == "json":
        if not json_raw:
            flash("Paste JSON questions before importing.", "error")
            return redirect(url_for("admin_exams.list_exams"))
        try:
            json_payload = json.loads(json_raw)
        except json.JSONDecodeError:
            flash("Invalid JSON format. Please verify your syntax.", "error")
            return redirect(url_for("admin_exams.list_exams"))

        questions_payload, payload_error = extract_import_questions_payload(json_payload)
        if payload_error:
            flash(payload_error, "error")
            return redirect(url_for("admin_exams.list_exams"))

        title = request.form.get("json_title", "").strip() or f"Imported Exam {now_local().strftime('%Y-%m-%d %H:%M')}"
        description = request.form.get("json_description", "").strip()
        instructions = request.form.get("json_instructions", "").strip()
        time_limit_enabled = True
        minutes = 30
        per_q_enabled = False
        per_q_seconds = 30
        max_attempts = 1

        normalized_questions, import_errors = normalize_imported_questions(questions_payload)
        if import_errors:
            flash(import_errors[0], "error")
            return redirect(url_for("admin_exams.list_exams"))
        parsed_questions = normalized_questions
    else:
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        instructions = request.form.get("instructions", "").strip()
        time_limit_enabled = request.form.get("time_limit_enabled") == "1"
        minutes = request.form.get("time_limit_minutes", type=int) or 30
        per_q_enabled = request.form.get("per_question_time_enabled") == "1"
        per_q_seconds = request.form.get("per_question_time_seconds", type=int) or 30
        max_attempts = request.form.get("max_attempts", type=int) or 1

    if not title:
        flash("Enter an exam title.", "error")
        return redirect(url_for("admin_exams.list_exams"))

    time_limit_seconds = minutes * 60 if time_limit_enabled else 0

    exam = ExamStore.create_exam(
        class_id=class_id,
        title=title,
        description=description,
        instructions=instructions,
        time_limit_seconds=time_limit_seconds,
        time_limit_enabled=time_limit_enabled,
        max_attempts=max_attempts,
    )

    imported = 0
    if parsed_questions:
        for sort_order, question in enumerate(parsed_questions):
            ExamStore.create_question(
                exam_id=exam["id"],
                question=question["question"],
                q_type=question["q_type"],
                options=question["options"],
                correct_answer=question["correct_answer"],
                points=question["points"],
                explanation=question["explanation"],
                sort_order=sort_order,
                time_limit_seconds=question["time_limit_seconds"],
            )
            imported += 1
        flash(f"Created exam with {imported} imported question(s).", "success")

    # If per-question time is enabled, set a default on all existing questions
    if per_q_enabled and per_q_seconds:
        db = get_db()
        db.execute(
            "UPDATE exam_questions SET time_limit_seconds = ? WHERE exam_id = ? AND time_limit_seconds IS NULL",
            (per_q_seconds, exam["id"]),
        )
        db.commit()

    return redirect(url_for("admin_exams.manage_questions", exam_id=exam["id"]))


@admin_exams_bp.route("/<int:exam_id>/questions", methods=["GET", "POST"])
@teacher_required
def manage_questions(exam_id):
    exam = ExamStore.get_exam(exam_id)
    if exam is None:
        abort(404)

    if request.method == "POST":
        # Check if this is a JSON import
        input_mode = request.form.get("input_mode", "form")

        if input_mode == "json":
            json_raw = request.form.get("json_input", "").strip()
            if not json_raw:
                flash("Paste JSON content before submitting.", "error")
                return redirect(url_for("admin_exams.manage_questions", exam_id=exam_id))
            try:
                parsed = json.loads(json_raw)
            except json.JSONDecodeError as e:
                flash(f"Invalid JSON: {e}", "error")
                return redirect(url_for("admin_exams.manage_questions", exam_id=exam_id))

            sort_order = len(ExamStore.get_questions(exam_id))
            imported, errors = import_questions_for_exam(exam_id, parsed, sort_order)
            for error in errors:
                flash(error, "error")

            if imported == 1:
                flash("Imported 1 question from JSON.", "success")
            else:
                flash(f"Imported {imported} questions from JSON.", "success")
            return redirect(url_for("admin_exams.manage_questions", exam_id=exam_id))

        # Manual form submission
        q_type = request.form.get("type", "multiple-choice")
        options = [
            opt.strip() for opt in request.form.getlist("options") if opt.strip()
        ] if q_type == "multiple-choice" else None
        time_limit_seconds = request.form.get("time_limit_seconds", type=int)
        ExamStore.create_question(
            exam_id=exam_id,
            question=request.form.get("question", "").strip(),
            q_type=q_type,
            options=options,
            correct_answer=request.form.get("correct_answer", "").strip() or None,
            points=request.form.get("points", type=int) or 1,
            explanation=request.form.get("explanation", "").strip(),
            sort_order=len(ExamStore.get_questions(exam_id)),
            time_limit_seconds=time_limit_seconds,
        )
        return redirect(url_for("admin_exams.manage_questions", exam_id=exam_id))

    questions = ExamStore.get_questions(exam_id)
    return render_template("admin/exam_questions.html", exam=exam, questions=questions)


@admin_exams_bp.route("/questions/<int:question_id>/delete", methods=["POST"])
@teacher_required
def delete_question(question_id):
    question = ExamStore.get_question(question_id)
    if question is None:
        abort(404)
    exam_id = question["exam_id"]
    ExamStore.delete_question(question_id)
    return redirect(url_for("admin_exams.manage_questions", exam_id=exam_id))


@admin_exams_bp.route("/<int:exam_id>/activate", methods=["POST"])
@teacher_required
def activate_exam(exam_id):
    ExamStore.update_exam(exam_id, status="active")
    return redirect(url_for("admin_exams.list_exams"))


@admin_exams_bp.route("/<int:exam_id>/close", methods=["POST"])
@teacher_required
def close_exam(exam_id):
    ExamStore.update_exam(exam_id, status="closed")
    return redirect(url_for("admin_exams.list_exams"))


@admin_exams_bp.route("/<int:exam_id>/attempts")
@teacher_required
def view_attempts(exam_id):
    exam = ExamStore.get_exam(exam_id)
    if exam is None:
        abort(404)
    attempts = ExamStore.get_attempts(exam_id)
    return render_template("admin/exam_attempts.html", exam=exam, attempts=attempts)


@admin_exams_bp.route("/attempts/<int:attempt_id>/grade", methods=["POST"])
@teacher_required
def grade_attempt(attempt_id):
    score = request.form.get("score", type=float)
    attempt = ExamStore.get_attempt(attempt_id)
    if attempt is None:
        abort(404)
    if score is not None:
        ExamStore.grade_attempt(attempt_id, score)
    return redirect(url_for("admin_exams.view_attempts", exam_id=attempt["exam_id"]))


@admin_exams_bp.route("/attempts/<int:attempt_id>/allow-retake", methods=["POST"])
@teacher_required
def allow_retake(attempt_id):
    attempt = ExamStore.get_attempt(attempt_id)
    if attempt is None:
        abort(404)
    if not attempt["is_locked_out"]:
        flash("This attempt is not locked out.", "error")
        return redirect(url_for("admin_exams.view_attempts", exam_id=attempt["exam_id"]))

    db = get_db()
    db.execute(
        "UPDATE exam_attempts SET is_locked_out = 0, excluded_from_attempt_count = 1 WHERE id = ?",
        (attempt_id,),
    )
    db.commit()
    flash("Retake granted. The locked attempt will no longer block a new attempt.", "success")
    return redirect(url_for("admin_exams.view_attempts", exam_id=attempt["exam_id"]))


@admin_exams_bp.route("/<int:exam_id>/delete", methods=["POST"])
@teacher_required
def delete_exam(exam_id):
    ExamStore.delete_exam(exam_id)
    return redirect(url_for("admin_exams.list_exams"))
