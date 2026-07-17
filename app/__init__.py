import os
from pathlib import Path

from flask import Flask
from werkzeug.security import generate_password_hash

from app.extensions import socketio


def create_app():
    app = Flask(__name__)
    base_dir = Path(__file__).resolve().parent.parent
    app.config.update(
        SECRET_KEY=os.environ.get("CLASSROOM_SECRET_KEY", os.urandom(24).hex()),
        DATABASE=os.environ.get(
            "CLASSROOM_DATABASE",
            str(base_dir / "instance" / "classroom_dropbox.sqlite3"),
        ),
        UPLOAD_FOLDER=os.environ.get("CLASSROOM_UPLOAD_FOLDER", str(base_dir / "uploads")),
        MAX_CONTENT_LENGTH=25 * 1024 * 1024,
        TEACHER_PASSWORD_HASH=os.environ.get(
            "CLASSROOM_TEACHER_PASSWORD_HASH",
            generate_password_hash(os.environ.get("CLASSROOM_TEACHER_PASSWORD", "teacher")),
        ),
    )

    from app.admin import admin
    from app.db import init_app as init_db
    from app.routes import main

    app.register_blueprint(main)
    app.register_blueprint(admin)
    init_db(app)
    socketio.init_app(app)

    return app
