const tableBody = document.getElementById("student-submission-rows");

if (tableBody && window.io) {
    const submissionId = Number(tableBody.dataset.submissionId);
    const socket = io();

    socket.on("connect", () => {
        socket.emit("join_submission", { submission_id: submissionId });
    });

    socket.on("new_submission", (payload) => {
        if (!payload || Number(payload.submission_id) !== submissionId) {
            return;
        }

        const row = payload.student_submission;
        if (!row) {
            window.location.reload();
            return;
        }

        tableBody.querySelector(".empty-row")?.remove();
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${escapeHtml(row.last_name)}</td>
            <td>${escapeHtml(row.first_name)}</td>
            <td>${escapeHtml(row.filename)}</td>
            <td>${escapeHtml(row.submitted_at)} ${row.is_late ? '<span class="late-tag">Late</span>' : ""}</td>
            <td><a href="${row.download_url}">Download</a></td>
        `;
        tableBody.prepend(tr);
    });
}

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
    }[char]));
}
