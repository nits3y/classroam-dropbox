# Classroom Dropbox — App Overview

## App Purpose
Classroom Dropbox is a Flask web app that provides:
- a teacher-facing admin dashboard for creating, editing, and managing assignment submissions
- a student-facing submission flow for uploading files and/or pasting text snippets using a shared submission code
- real-time student submission updates via Socket.IO
- file storage organized by class and submission
- preview/download capabilities for student-submitted files

## Architecture
### Backend
- `run.py`: application entrypoint. Creates Flask app and starts Socket.IO server on a local port.
- `app/__init__.py`: app factory. Configures secret key, upload folder, database location, file size limit, teacher password, and LibreOffice path. Registers `main` and `admin` blueprints and initializes the database.
- `app/db.py`: SQLite setup and teardown. Creates the schema for `classes`, `submissions`, and `student_submissions`.
- `app/routes.py`: public student-facing routes.
- `app/admin.py`: admin blueprint and helper functions for teacher workflows, submission lifecycle, file handling, previews, exports, and Socket.IO.
- `app/extensions.py`: initializes Flask extensions such as Socket.IO.

### Frontend
- `app/templates/base.html`: base layout and global stylesheet.
- `app/static/css/style.css`: main app styling for forms, cards, buttons, modals, admin sidebar, tables, badges, and responsive behavior.
- `app/static/js/student_submission.js`: student-side form behavior for files, text snippets, submission confirmation, validation, and modal handling.
- `app/static/js/submission-modal.js`: admin submission modal logic, open/close, data loading, and realtime refresh hooks.
- `app/static/js/admin.js`: admin UI helpers for clickable rows and clipboard buttons.
- `app/static/js/file-preview.js`: file preview handler, likely used by the admin preview modal.
- `app/static/js/highlight.min.js`, `socket.io.min.js`: third-party assets for syntax highlighting and realtime websockets.

## Database Model
- `classes`: teacher-defined course groups with default allowed file types.
- `submissions`: assignments created by teachers. Fields include title, class, description, deadline, allowed file types, generated access code, and creation timestamp.
- `student_submissions`: uploaded student files or pasted text references, linked to a submission, with student name, stored file path, and submitted timestamp.

## Main Flows
### Teacher/admin flow
1. Login at `/admin/login`.
2. Dashboard at `/admin/dashboard`: overview stats and recent submissions.
3. Class management at `/admin/classes`:
   - create classes
   - select default allowed file types
   - edit or delete classes (only if no submissions exist)
4. Submissions list at `/admin/submissions`:
   - create a new assignment
   - view assignment status, student counts, and access codes
   - open per-submission modal and preview student submissions
5. Assignment creation at `/admin/submissions/new`:
   - validate title, class, deadline, file types
   - generate a unique 6-character code
   - save submission record
6. Assignment detail and student preview:
   - view submission info
   - download single student files or all files as ZIP
   - export roster/submission metadata as CSV
   - preview text/code files inline
   - convert Office files to PDF using LibreOffice if available
7. Real-time updates via Socket.IO: each submission has a room, and new student uploads emit updates to admin clients.

### Student flow
1. Access root `/` to enter a teacher-provided code.
2. `POST /join` validates the code and redirects to `/submissions/<code>`.
3. Student submission page shows assignment details, deadline, allowed types, and description.
4. Student submits:
   - required first and last name
   - one or more file uploads
   - optional plain-text snippets if allowed
   - client-side validation ensures at least one file or snippet and that text snippets are not blank
5. On success, student is redirected to `/submissions/<code>/success`.
6. Back-end validates file type restrictions, saves uploaded files to `uploads/<class_id>/<submission_id>/`, and saves pasted snippets as text files in the same storage hierarchy.

## UI Summary
### Student UI
- `code_entry.html`: code entry landing page.
- `student_submission.html`: clean card layout showing assignment name, class, deadline, allowed upload types, optional description, and submission form.
- Uses `student_submission.js` to dynamically add file inputs, snippet blocks, confirm submission modal, and validation.
- Submission form supports multi-file uploads and multi-snippet paste.

### Admin UI
- `admin/base_admin.html`: sidebar navigation, responsive mobile behavior, and topbar.
- `admin/dashboard.html`: stats card grid and recent submissions summary.
- `admin/classes.html`: class management with default allowed file type controls.
- `admin/submissions.html`: submission list table, create submission modal, and detailed submission modal.
- `submission-modal.js` handles opening the admin modal, fetching submission details via `/admin/submissions/<id>/api`, and rendering student rows.
- Admin has copy-to-clipboard buttons, clickable rows, and sidebar collapse behavior.

## File handling
- `save_uploaded_file()`: sanitizes student names and filenames, timestamps submissions, stores under class/submission folders.
- `save_pasted_text()`: converts pasted snippets into `.txt` files and stores them similarly.
- `download_student_file()` serves individual student files as attachments.
- `download_all()` archives submission files into a ZIP for download.
- `preview_student_file()` returns text content JSON for text/code files or serves images/PDFs directly, with Office conversion through LibreOffice.

## Key backend behaviors
- `normalize_file_types()`: stores checked file types as `any` or comma-separated list.
- `status_for_deadline()`: resolves assignment status to `upcoming`, `ongoing`, `due-soon`, or `closed`.
- `generate_code()`: creates a unique 6-character uppercase alphanumeric code used by students.
- `teacher_required()`: protects admin routes with session authentication.
- `emit_new_submission()`: sends real-time updates via Socket.IO when a student submits.
- `allowed_extensions()` and `validate_student_upload()`: enforce file type restrictions when students upload.

## Notes on current state
- The app is mostly classic Flask + Jinja2 + vanilla JS.
- The student-facing site is a single card-based form experience.
- The admin side uses a sidebar dashboard layout with modals for assignment creation and details.
- Database is SQLite with simple relational tables.
- File uploads are stored locally under `uploads/` with class/submission segmentation.
- There is support for both file uploads and pasted text submissions.

## Files that drive core behavior
- `run.py`: launch and port selection.
- `app/__init__.py`: app factory and config.
- `app/db.py`: SQLite schema and connection.
- `app/routes.py`: public student routes and submission handling.
- `app/admin.py`: teacher admin routes, file handling, exports, previews, and helper utilities.
- `app/templates/student_submission.html`: student submission form UI.
- `app/templates/admin/submissions.html`: create submission modal and submission table.
- `app/static/js/student_submission.js`: student dynamic form behavior.
- `app/static/js/submission-modal.js`: admin modal details and open/close logic.
- `app/static/css/style.css`: visual styling for the entire app.

## Summary
This app is a lightweight classroom file dropbox with:
- teacher-managed assignment creation and class grouping
- student code-based submission access
- file-type controls and deadline enforcement
- local upload storage and admin download/export capabilities
- live update support through Socket.IO

If you want, I can also write a shorter “context.md” summary focused only on developer-facing architecture and file responsibilities. 