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
