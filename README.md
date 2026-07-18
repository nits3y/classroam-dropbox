# Classroom Dropbox — LibreOffice Offline Preview Setup

This project can convert Microsoft Office files (.docx, .pptx, .xlsx) to PDF for in-browser preview using LibreOffice in headless mode. This conversion happens entirely on the teacher's Windows laptop and works offline once LibreOffice is installed.

Installation notes (PREREQUISITE — do this manually):

- Download and install LibreOffice from https://libreoffice.org (free).
- Typical Windows install path for `soffice.exe` is:

  `C:\Program Files\LibreOffice\program\soffice.exe`

- Configure the app to point to `soffice.exe` if your LibreOffice is installed to a non-default location. You can set the environment variable `CLASSROOM_LIBREOFFICE_PATH` before starting the app, or edit the configuration in `create_app()` if you maintain a custom deployment.

Behavior and fallback:

- On first "View" of a `.docx`, `.pptx`, or `.xlsx` file, the app will invoke LibreOffice headlessly to convert the document to PDF and cache the resulting PDF next to the original file. Subsequent previews use the cached PDF.
- If LibreOffice is not installed, the configured path is wrong, or conversion fails (including timeout), the app will NOT crash. Instead, the preview modal shows a friendly message: "Preview isn't available for this file (LibreOffice not found or conversion failed) — download to view instead." The Download button remains available so you can open the file locally.
- LibreOffice availability is checked once at app startup; a console message will indicate whether office preview support is enabled.

Notes for teachers:

- Make sure to run the app after installing LibreOffice so the availability check runs at startup.
- If you prefer to place converted PDFs in a different location, adapt the conversion helper in `app/admin.py` to change the cache location.

This file complements the project's README and documents the manual step required to enable Office-to-PDF previews.
# Classroom Dropbox

Teacher-facing Flask app for collecting classroom file submissions on a local school LAN.

## Run

```powershell
.\venv\Scripts\python.exe run.py
```

The console prints both the teacher admin URL and the current LAN student URL. The LAN IP is detected at startup because a teacher laptop may receive a different DHCP address on different days.

For development, the default teacher password is `teacher`. For real use, set a hashed password instead of relying on the development default:

```powershell
.\venv\Scripts\python.exe -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-password-here'))"
$env:CLASSROOM_TEACHER_PASSWORD_HASH='paste-generated-hash-here'
```

## Local classroom notes

- The app uses SQLite through Python's built-in `sqlite3` module. The schema is small and local-only, so this avoids extra ORM setup while still giving durable file-backed writes.
- Data is stored at `instance/classroom_dropbox.sqlite3` by default. If the Flask process crashes or the laptop restarts, committed SQLite rows remain on disk; only an upload in progress at that exact moment is at risk.
- Uploaded files are stored outside `static/` under `uploads/<class_id>/<submission_id>/`.
- `MAX_CONTENT_LENGTH` is set to 25MB to avoid accidental oversized uploads hanging the laptop.
- Flask-SocketIO is configured for `eventlet` so the app can handle concurrent LAN clients better than Flask's built-in development server.
- Keep `debug=True` only while developing. For class, turn debug off so the reloader does not drop active connections.
- Runtime assets are local only. The Socket.IO browser client is stored in `app/static/js/socket.io.min.js` so teacher live updates do not need a CDN during class.

## Schema

- `classes`: class name and default allowed file types.
- `submissions`: teacher-created assignment metadata, generated short code, deadline, and class link.
- `student_submissions`: uploaded file path and student name for each submission.

Indexes are added for submission code lookups, class filtering, student-submission joins, and recent-submission sorting.
