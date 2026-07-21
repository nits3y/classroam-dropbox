import sqlite3
from pathlib import Path

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    default_allowed_file_types TEXT NOT NULL DEFAULT 'any'
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    class_id INTEGER NOT NULL,
    description TEXT,
    allowed_file_types TEXT NOT NULL DEFAULT 'any',
    deadline TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes (id)
);

CREATE TABLE IF NOT EXISTS student_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submission_id) REFERENCES submissions (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_submissions_code ON submissions (code);
CREATE INDEX IF NOT EXISTS idx_submissions_class_id ON submissions (class_id);
CREATE INDEX IF NOT EXISTS idx_student_submissions_submission_id
    ON student_submissions (submission_id);
CREATE INDEX IF NOT EXISTS idx_student_submissions_submitted_at
    ON student_submissions (submitted_at);

-- Exams (formerly Fucursa's exams.json)
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    instructions TEXT,
    time_limit_seconds INTEGER NOT NULL DEFAULT 1800,
    time_limit_enabled INTEGER NOT NULL DEFAULT 1,
    code TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft',       -- draft | active | closed
    max_attempts INTEGER NOT NULL DEFAULT 1,
    start_date TEXT,
    end_date TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes (id)
);

-- Exam questions (formerly Fucursa's questions.json)
CREATE TABLE IF NOT EXISTS exam_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'multiple-choice',
        -- multiple-choice | true-false | short-answer | identification | essay | word-bank
    options TEXT,               -- JSON array, only for multiple-choice or word-bank
    correct_answer TEXT,        -- null for essay (manually graded)
    explanation TEXT,
    points INTEGER NOT NULL DEFAULT 1,
    is_required INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    time_limit_seconds INTEGER, -- per-question time limit in seconds (null = no per-question limit)
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
);

-- Exam attempts (formerly Fucursa's student_responses.json)
CREATE TABLE IF NOT EXISTS exam_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    answers TEXT NOT NULL DEFAULT '{}',     -- JSON: {question_id: answer_text}
    score REAL,
    total_points REAL,
    security_warnings INTEGER NOT NULL DEFAULT 0,
    is_auto_submitted INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'in-progress',  -- in-progress | submitted | graded
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submitted_at TEXT,
    FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_exams_code ON exams (code);
CREATE INDEX IF NOT EXISTS idx_exams_class_id ON exams (class_id);
CREATE INDEX IF NOT EXISTS idx_exam_questions_exam_id ON exam_questions (exam_id);
CREATE INDEX IF NOT EXISTS idx_exam_attempts_exam_id ON exam_attempts (exam_id);
CREATE INDEX IF NOT EXISTS idx_exam_attempts_status ON exam_attempts (status);
"""


def get_db():
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()