"""Persistent local job records and a passive Tk queue view for GENESIS."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk

from genesis.database import session


STATUSES = {"queued", "running", "completed", "failed"}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobStore:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def create(self, operation, *, detail=None, workflow=None):
        if not str(operation).strip():
            raise ValueError("A job operation is required.")
        now = utc_now()
        with session(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO jobs
                    (operation, status, progress, detail, workflow, created_at, updated_at)
                VALUES (?, 'queued', 0, ?, ?, ?, ?)
                """,
                (str(operation), detail, workflow, now, now),
            )
            return int(cursor.lastrowid)

    def update(self, job_id, *, status=None, progress=None, detail=None,
               error=None, outputs=None):
        if status is not None and status not in STATUSES:
            raise ValueError(f"Unsupported job status: {status}")
        fields, values = ["updated_at = ?"], [utc_now()]
        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if progress is not None:
            progress = max(0.0, min(100.0, float(progress)))
            fields.append("progress = ?")
            values.append(progress)
        if detail is not None:
            fields.append("detail = ?")
            values.append(str(detail))
        if error is not None:
            fields.append("error = ?")
            values.append(str(error))
        if outputs is not None:
            fields.append("outputs = ?")
            values.append(json.dumps([str(Path(path)) for path in outputs]))
        values.append(int(job_id))
        with session(self.db_path) as connection:
            cursor = connection.execute(
                f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?",
                values,
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown job: {job_id}")

    def recent(self, limit=20):
        limit = max(1, min(200, int(limit)))
        with session(self.db_path) as connection:
            return [dict(row) for row in connection.execute(
                """
                SELECT id, operation, status, progress, detail, workflow,
                       outputs, error, created_at, updated_at
                FROM jobs ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            )]


class JobQueueView(ttk.LabelFrame):
    """Read-only recent-job list; execution remains owned by each workflow."""
    def __init__(self, parent, store, limit=8):
        super().__init__(parent, text="JOB QUEUE · recent local activity")
        self.store, self.limit = store, limit
        self.tree = ttk.Treeview(
            self,
            columns=("status", "progress", "operation", "updated"),
            show="headings",
            height=4,
        )
        for column, label, width in (
            ("status", "Status", 90),
            ("progress", "Progress", 75),
            ("operation", "Operation", 190),
            ("updated", "Updated", 190),
        ):
            self.tree.heading(column, text=label)
            self.tree.column(column, width=width, stretch=column == "operation")
        self.tree.pack(fill="x", expand=True, padx=7, pady=(7, 3))
        ttk.Button(self, text="Refresh jobs", command=self.refresh).pack(
            anchor="e", padx=7, pady=(2, 7)
        )
        self.refresh()

    def refresh(self):
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        for job in self.store.recent(self.limit):
            self.tree.insert(
                "",
                "end",
                iid=str(job["id"]),
                values=(
                    job["status"].title(),
                    f'{float(job["progress"] or 0):.0f}%',
                    job["operation"],
                    job["updated_at"] or "",
                ),
            )
