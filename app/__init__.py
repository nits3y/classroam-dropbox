import os
from pathlib import Path

from flask import Flask
from werkzeug.security import generate_password_hash

from app.extensions import socketio, limiter


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
        # Path to LibreOffice `soffice.exe` for converting Office files to PDF on Windows.
        # Can be overridden via the CLASSROOM_LIBREOFFICE_PATH environment variable.
        LIBREOFFICE_PATH=os.environ.get(
            "CLASSROOM_LIBREOFFICE_PATH",
            "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
        ),
        # Conversion timeout for LibreOffice in seconds
        LIBREOFFICE_CONVERT_TIMEOUT=int(os.environ.get("CLASSROOM_LIBREOFFICE_CONVERT_TIMEOUT", "25")),
    )

    from app.admin import admin, _init_libreoffice_config
    from app.db import init_app as init_db
    from app.routes import main

    app.register_blueprint(main)
    app.register_blueprint(admin)
    init_db(app)
    limiter.init_app(app)
    socketio.init_app(app)

    # One-time LibreOffice availability check, run now that config/blueprints are ready.
    with app.app_context():
        _init_libreoffice_config()

    return app