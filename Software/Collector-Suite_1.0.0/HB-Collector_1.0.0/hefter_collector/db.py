from __future__ import annotations

import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .identity_registry import IdentityRegistry


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS students(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  class_id TEXT NOT NULL,
  list_position INTEGER NOT NULL,
  student_code TEXT NOT NULL,
  name TEXT NOT NULL,
  token TEXT NOT NULL UNIQUE,
  active INTEGER NOT NULL DEFAULT 1,
  UNIQUE(class_id, list_position),
  UNIQUE(class_id, student_code)
);
CREATE TABLE IF NOT EXISTS sessions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  access_token TEXT NOT NULL UNIQUE,
  session_code TEXT NOT NULL,
  workspace_id TEXT NOT NULL,
  class_id TEXT NOT NULL,
  period TEXT NOT NULL,
  title TEXT NOT NULL,
  phase TEXT NOT NULL DEFAULT 'setup',
  teacher_review_opened INTEGER NOT NULL DEFAULT 0,
  archived INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS session_roster(
  session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  student_id INTEGER NOT NULL REFERENCES students(id),
  list_position INTEGER NOT NULL,
  student_code TEXT NOT NULL,
  name TEXT NOT NULL,
  PRIMARY KEY(session_id, student_id)
);
CREATE TABLE IF NOT EXISTS assignments(
  session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  reviewer_id INTEGER NOT NULL,
  subject_id INTEGER NOT NULL,
  PRIMARY KEY(session_id, reviewer_id),
  UNIQUE(session_id, subject_id)
);
CREATE TABLE IF NOT EXISTS peer_exclusions(
  session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  student_a_id INTEGER NOT NULL,
  student_b_id INTEGER NOT NULL,
  PRIMARY KEY(session_id, student_a_id, student_b_id),
  CHECK(student_a_id < student_b_id)
);
CREATE TABLE IF NOT EXISTS ratings(
  session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  subject_id INTEGER NOT NULL,
  rater_id INTEGER,
  role TEXT NOT NULL,
  values_json TEXT NOT NULL,
  total INTEGER NOT NULL,
  submitted_at TEXT NOT NULL,
  PRIMARY KEY(session_id, subject_id, role)
);
"""


class Database:
    def __init__(
        self,
        path: Path,
        workspace_id: str = "default",
        identity_file: Path | None = None,
        migration_backup_dir: Path | None = None,
    ):
        self.path = Path(path)
        self.workspace_id = str(workspace_id)
        self.last_migration_backup: Path | None = None
        self.identities = IdentityRegistry(
            identity_file or self.path.parent / "collector_identities.sqlite3",
            strict=identity_file is not None,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self._requires_migration():
            self.last_migration_backup = self._backup_before_migration(
                migration_backup_dir or self.path.parent / "Sicherungen"
            )
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)")}
            if "teacher_review_opened" not in columns:
                conn.execute(
                    "ALTER TABLE sessions ADD COLUMN teacher_review_opened INTEGER NOT NULL DEFAULT 0"
                )
            if "workspace_id" not in columns:
                conn.execute(
                    "ALTER TABLE sessions ADD COLUMN workspace_id TEXT NOT NULL DEFAULT 'legacy'"
                )
                conn.execute(
                    "UPDATE sessions SET workspace_id=? WHERE workspace_id='legacy'",
                    (self.workspace_id,),
                )
            if "archived" not in columns:
                conn.execute(
                    "ALTER TABLE sessions ADD COLUMN archived INTEGER NOT NULL DEFAULT 0"
                )
            if "access_token" not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN access_token TEXT")
                for row in conn.execute("SELECT id FROM sessions"):
                    conn.execute(
                        "UPDATE sessions SET access_token=? WHERE id=?",
                        (secrets.token_urlsafe(24), row["id"]),
                    )
                conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS sessions_access_token "
                    "ON sessions(access_token)"
                )
            if "session_code" not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN session_code TEXT")
                for row in conn.execute("SELECT id FROM sessions"):
                    conn.execute("UPDATE sessions SET session_code=? WHERE id=?", (self._new_session_code(), row["id"]))
            conn.execute("PRAGMA user_version=8")
        self._allow_repeated_sessions()

    def _requires_migration(self) -> bool:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return False
        with sqlite3.connect(self.path) as conn:
            has_sessions = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sessions'"
            ).fetchone()
            version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        return bool(has_sessions and version < 8)

    @staticmethod
    def _new_session_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    def _backup_before_migration(self, backup_dir: Path) -> Path:
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target = backup_dir / f"HB-Datenbank_vor_Update_{stamp}.sqlite3"
        with sqlite3.connect(self.path) as source, sqlite3.connect(target) as destination:
            source.backup(destination)
        return target

    def _allow_repeated_sessions(self):
        """Entfernt die frühere Eindeutigkeitsregel für Klasse und Zeitraum."""
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            unique_pair_index = None
            for index in conn.execute("PRAGMA index_list(sessions)"):
                if not index["unique"]:
                    continue
                columns = [
                    row["name"]
                    for row in conn.execute(f"PRAGMA index_info('{index['name']}')")
                ]
                if columns == ["class_id", "period"]:
                    unique_pair_index = index["name"]
                    break
            if not unique_pair_index:
                return

            conn.execute("PRAGMA foreign_keys=OFF")
            conn.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE sessions_new(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  access_token TEXT NOT NULL UNIQUE,
                  session_code TEXT NOT NULL,
                  workspace_id TEXT NOT NULL,
                  class_id TEXT NOT NULL,
                  period TEXT NOT NULL,
                  title TEXT NOT NULL,
                  phase TEXT NOT NULL DEFAULT 'setup',
                  teacher_review_opened INTEGER NOT NULL DEFAULT 0,
                  archived INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT NOT NULL
                );
                INSERT INTO sessions_new(
                  id, access_token, session_code, workspace_id, class_id, period, title, phase,
                  teacher_review_opened, archived, created_at
                )
                SELECT
                  id, access_token, session_code, workspace_id, class_id, period, title, phase,
                  teacher_review_opened, archived, created_at
                FROM sessions;
                DROP TABLE sessions;
                ALTER TABLE sessions_new RENAME TO sessions;
                COMMIT;
                """
            )
            conn.execute("PRAGMA foreign_keys=ON")
            problems = conn.execute("PRAGMA foreign_key_check").fetchall()
            if problems:
                raise RuntimeError("Datenbankmigration hat ungültige Verweise erzeugt.")
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def import_students(self, rows: list[dict]) -> int:
        if not rows:
            raise ValueError("Die Liste enthält keine Schülerinnen oder Schüler.")
        seen: set[tuple[str, int]] = set()
        with self.connect() as conn:
            for raw in rows:
                class_id = str(raw["class_id"]).strip()
                number = int(raw["list_position"])
                code = str(raw.get("student_code") or f"{class_id}-{number:02d}").strip()
                name = str(raw["name"]).strip()
                if not class_id or not name or number < 1:
                    raise ValueError("Klasse, Listenplatz und Name müssen ausgefüllt sein.")
                key = (class_id.casefold(), number)
                if key in seen:
                    raise ValueError(f"Listenplatz doppelt: {class_id}, Nr. {number}")
                seen.add(key)
                existing = conn.execute(
                    "SELECT id,token FROM students WHERE class_id=? AND list_position=?",
                    (class_id, number),
                ).fetchone()
                token = self.identities.resolve(
                    code,
                    name=name,
                    class_id=class_id,
                    existing_token=str(existing["token"]) if existing else None,
                    source="HB-Collector",
                )
                if existing:
                    conn.execute(
                        "UPDATE students SET student_code=?, name=?, token=?, active=1 WHERE id=?",
                        (code, name, token, existing["id"]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO students(class_id,list_position,student_code,name,token) VALUES(?,?,?,?,?)",
                        (class_id, number, code, name, token),
                    )
        return len(rows)

    def import_ods_roster(self, class_id: str, ods_students) -> int:
        identities = self.identities.roster_for_class(class_id)
        if not identities:
            raise ValueError(
                f"Klasse {class_id} fehlt im gemeinsamen QR-Register."
            )
        by_position = {int(item["list_position"]): item for item in identities}
        rows = []
        for student in ods_students:
            position = int(student.list_position)
            identity = by_position.get(position)
            if not identity:
                raise ValueError(
                    f"Listenplatz {position} aus Hefterbewertung.ods fehlt im QR-Register."
                )
            if str(identity["name"]).strip() != str(student.name).strip():
                raise ValueError(
                    f"Name bei Listenplatz {position} stimmt nicht überein "
                    f"({student.name!r} in Hefterbewertung.ods, {identity['name']!r} im QR-Register)."
                )
            if student.student_code and str(identity["student_key"]).strip() != str(student.student_code).strip():
                raise ValueError(
                    f"Schüler-ID bei Listenplatz {position} stimmt nicht mit dem QR-Register überein "
                    f"({student.student_code!r} statt {identity['student_key']!r})."
                )
            rows.append(
                {
                    "class_id": class_id.strip(),
                    "list_position": position,
                    "student_code": identity["student_key"],
                    "name": student.name,
                }
            )
        return self.import_students(rows)

    def classes(self):
        with self.connect() as conn:
            return conn.execute(
                "SELECT class_id, COUNT(*) count FROM students WHERE active=1 GROUP BY class_id ORDER BY class_id"
            ).fetchall()

    def students(self, class_id: str):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM students WHERE class_id=? AND active=1 ORDER BY list_position",
                (class_id,),
            ).fetchall()

    def student_by_token(self, token: str):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM students WHERE token=? AND active=1", (token,)).fetchone()

    def create_session(self, class_id: str, period: str, title: str) -> int:
        roster = self.students(class_id)
        if len(roster) < 3:
            raise ValueError("Die Klasse benötigt mindestens drei aktive Personen.")
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO sessions(access_token,session_code,workspace_id,class_id,period,title,created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    secrets.token_urlsafe(24),
                    self._new_session_code(),
                    self.workspace_id,
                    class_id,
                    period,
                    title,
                    now(),
                ),
            )
            session_id = int(cur.lastrowid)
            conn.executemany(
                "INSERT INTO session_roster(session_id,student_id,list_position,student_code,name) VALUES(?,?,?,?,?)",
                [(session_id, s["id"], s["list_position"], s["student_code"], s["name"]) for s in roster],
            )
            return session_id

    def sessions(self, *, archived: bool = False):
        with self.connect() as conn:
            return conn.execute(
                """SELECT s.*,
                   (SELECT COUNT(*) FROM session_roster r WHERE r.session_id=s.id) roster_count,
                   (SELECT COUNT(*) FROM ratings x WHERE x.session_id=s.id AND x.role='self') self_count,
                   (SELECT COUNT(*) FROM ratings x WHERE x.session_id=s.id AND x.role='peer') peer_count,
                   (SELECT COUNT(*) FROM ratings x WHERE x.session_id=s.id AND x.role='teacher') teacher_count
                   FROM sessions s
                   WHERE s.workspace_id=? AND s.archived=?
                   ORDER BY s.id DESC""",
                (self.workspace_id, int(archived)),
            ).fetchall()

    def session(self, session_id: int):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM sessions WHERE id=? AND workspace_id=?",
                (session_id, self.workspace_id),
            ).fetchone()

    def session_by_access_token(self, access_token: str):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM sessions WHERE access_token=? AND workspace_id=?",
                (access_token, self.workspace_id),
            ).fetchone()

    def student_in_session(self, session_id: int, student_id: int) -> bool:
        with self.connect() as conn:
            return (
                conn.execute(
                    "SELECT 1 FROM session_roster WHERE session_id=? AND student_id=?",
                    (session_id, student_id),
                ).fetchone()
                is not None
            )

    def repeat_session(self, session_id: int) -> int:
        source = self.session(session_id)
        if not source:
            raise ValueError("Die Bewertung wurde nicht gefunden.")
        if source["phase"] != "closed":
            raise ValueError("Nur abgeschlossene Bewertungen können wiederholt werden.")
        exclusions = [
            (int(row["student_a_no"]), int(row["student_b_no"]))
            for row in self.exclusions(session_id)
        ]
        repeated = self.create_session(source["class_id"], source["period"], source["title"])
        for first, second in exclusions:
            self.add_exclusion(repeated, first, second)
        return repeated

    def archive_session(self, session_id: int) -> None:
        source = self.session(session_id)
        if not source:
            raise ValueError("Die Bewertung wurde nicht gefunden.")
        if source["phase"] != "closed":
            raise ValueError("Nur abgeschlossene Bewertungen können archiviert werden.")
        with self.connect() as conn:
            conn.execute(
                "UPDATE sessions SET archived=1 WHERE id=? AND workspace_id=?",
                (session_id, self.workspace_id),
            )

    def restore_session(self, session_id: int) -> None:
        source = self.session(session_id)
        if not source or not source["archived"]:
            raise ValueError("Die archivierte Bewertung wurde nicht gefunden.")
        with self.connect() as conn:
            conn.execute(
                "UPDATE sessions SET archived=0 WHERE id=? AND workspace_id=?",
                (session_id, self.workspace_id),
            )

    def delete_archived_session(self, session_id: int) -> None:
        source = self.session(session_id)
        if not source or not source["archived"]:
            raise ValueError("Nur archivierte Bewertungen können gelöscht werden.")
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM sessions WHERE id=? AND workspace_id=? AND archived=1",
                (session_id, self.workspace_id),
            )

    def backup_to(self, target: Path) -> Path:
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as source, sqlite3.connect(target) as destination:
            source.backup(destination)
        return target

    def roster(self, session_id: int):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM session_roster WHERE session_id=? ORDER BY list_position", (session_id,)
            ).fetchall()

    def roster_student_by_position(self, session_id: int, list_position: int):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM session_roster WHERE session_id=? AND list_position=?",
                (session_id, list_position),
            ).fetchone()

    def set_phase(self, session_id: int, phase: str):
        if phase not in {
            "setup", "self", "self_closed", "peer", "peer_closed",
            "teacher", "teacher_closed", "closed",
        }:
            raise ValueError("Ungültige Phase.")
        with self.connect() as conn:
            conn.execute("UPDATE sessions SET phase=? WHERE id=?", (phase, session_id))

    def mark_teacher_review_opened(self, session_id: int):
        with self.connect() as conn:
            conn.execute(
                "UPDATE sessions SET teacher_review_opened=1 WHERE id=?",
                (session_id,),
            )

    def save_assignments(self, session_id: int, mapping: dict[int, int]):
        excluded = self.exclusion_pairs(session_id)
        conflict = next(
            (
                (reviewer, subject)
                for reviewer, subject in mapping.items()
                if frozenset((reviewer, subject)) in excluded
            ),
            None,
        )
        if conflict:
            raise ValueError("Die Zuordnung enthält ein ausgeschlossenes Schülerpaar.")
        with self.connect() as conn:
            conn.execute("DELETE FROM assignments WHERE session_id=?", (session_id,))
            conn.executemany(
                "INSERT INTO assignments(session_id,reviewer_id,subject_id) VALUES(?,?,?)",
                [(session_id, reviewer, subject) for reviewer, subject in mapping.items()],
            )

    def exclusions(self, session_id: int):
        with self.connect() as conn:
            return conn.execute(
                """SELECT e.student_a_id, e.student_b_id,
                          a.list_position AS student_a_no, a.name AS student_a_name,
                          b.list_position AS student_b_no, b.name AS student_b_name
                   FROM peer_exclusions e
                   JOIN session_roster a
                     ON a.session_id=e.session_id AND a.student_id=e.student_a_id
                   JOIN session_roster b
                     ON b.session_id=e.session_id AND b.student_id=e.student_b_id
                   WHERE e.session_id=?
                   ORDER BY a.list_position, b.list_position""",
                (session_id,),
            ).fetchall()

    def exclusion_pairs(self, session_id: int) -> set[frozenset[int]]:
        return {
            frozenset((int(row["student_a_id"]), int(row["student_b_id"])))
            for row in self.exclusions(session_id)
        }

    def add_exclusion(
        self,
        session_id: int,
        list_position_a: int,
        list_position_b: int,
    ) -> None:
        session = self.session(session_id)
        if not session or session["phase"] not in {"setup", "self", "self_closed"}:
            raise ValueError(
                "Ausschlüsse können nur vor Beginn der Peerbewertung geändert werden."
            )
        if int(list_position_a) == int(list_position_b):
            raise ValueError("Bitte zwei verschiedene Listenplätze auswählen.")
        first = self.roster_student_by_position(session_id, int(list_position_a))
        second = self.roster_student_by_position(session_id, int(list_position_b))
        if not first or not second:
            raise ValueError("Mindestens ein Listenplatz gehört nicht zu dieser Klasse.")
        student_a, student_b = sorted((int(first["student_id"]), int(second["student_id"])))
        with self.connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO peer_exclusions(
                     session_id,student_a_id,student_b_id
                   ) VALUES(?,?,?)""",
                (session_id, student_a, student_b),
            )
            # A newly excluded pair may occur in the old assignment. Requiring
            # regeneration keeps the shown assignment and the rules consistent.
            conn.execute("DELETE FROM assignments WHERE session_id=?", (session_id,))

    def remove_exclusion(
        self,
        session_id: int,
        student_a_id: int,
        student_b_id: int,
    ) -> None:
        session = self.session(session_id)
        if not session or session["phase"] not in {"setup", "self", "self_closed"}:
            raise ValueError(
                "Ausschlüsse können nur vor Beginn der Peerbewertung geändert werden."
            )
        student_a, student_b = sorted((int(student_a_id), int(student_b_id)))
        with self.connect() as conn:
            conn.execute(
                """DELETE FROM peer_exclusions
                   WHERE session_id=? AND student_a_id=? AND student_b_id=?""",
                (session_id, student_a, student_b),
            )

    def assignment_mapping(self, session_id: int) -> dict[int, int]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT reviewer_id,subject_id FROM assignments WHERE session_id=?", (session_id,)
            ).fetchall()
        return {int(row["reviewer_id"]): int(row["subject_id"]) for row in rows}

    def assignments(self, session_id: int):
        with self.connect() as conn:
            return conn.execute(
                """SELECT a.*, r.name reviewer_name, r.list_position reviewer_no,
                          s.name subject_name, s.list_position subject_no
                   FROM assignments a
                   JOIN session_roster r ON r.session_id=a.session_id AND r.student_id=a.reviewer_id
                   JOIN session_roster s ON s.session_id=a.session_id AND s.student_id=a.subject_id
                   WHERE a.session_id=? ORDER BY r.list_position""",
                (session_id,),
            ).fetchall()

    def assignment_for(self, session_id: int, reviewer_id: int):
        with self.connect() as conn:
            return conn.execute(
                """SELECT a.*, s.name subject_name, s.list_position subject_no
                   FROM assignments a JOIN session_roster s
                   ON s.session_id=a.session_id AND s.student_id=a.subject_id
                   WHERE a.session_id=? AND a.reviewer_id=?""",
                (session_id, reviewer_id),
            ).fetchone()

    def active_session_for_student(self, class_id: str, session_code: str | None = None):
        with self.connect() as conn:
            query = (
                """SELECT * FROM sessions
                   WHERE workspace_id=? AND class_id=? AND phase IN ('setup','self','self_closed','peer')
                """ + (" AND session_code=?" if session_code is not None else "") +
                " ORDER BY id DESC LIMIT 1"
            )
            args = (self.workspace_id, class_id, session_code) if session_code is not None else (self.workspace_id, class_id)
            return conn.execute(query, args).fetchone()

    def student_session_by_code(self, class_id: str, session_code: str):
        with self.connect() as conn:
            return conn.execute(
                """SELECT * FROM sessions
                   WHERE workspace_id=? AND class_id=? AND session_code=?
                   AND archived=0 AND phase IN ('setup','self','self_closed','peer')
                   ORDER BY id DESC LIMIT 1""",
                (self.workspace_id, class_id, session_code),
            ).fetchone()

    def active_session_by_code(self, session_code: str):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM sessions WHERE session_code=? AND archived=0 AND phase<>'closed' AND workspace_id=?",
                (session_code.strip(), self.workspace_id),
            ).fetchone()

    def public_progress(self, session_id: int) -> dict[str, int]:
        with self.connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM session_roster WHERE session_id=?", (session_id,)).fetchone()[0]
            rows = conn.execute("SELECT role,COUNT(*) amount FROM ratings WHERE session_id=? GROUP BY role", (session_id,)).fetchall()
        counts = {str(row["role"]): int(row["amount"]) for row in rows}
        return {"total": int(total), "self": counts.get("self", 0), "peer": counts.get("peer", 0)}

    def save_rating(self, session_id: int, subject_id: int, rater_id: int | None, role: str, values: dict):
        if role not in {"self", "peer", "teacher"}:
            raise ValueError("Ungültige Bewertungsrolle.")
        total = sum(int(value) for value in values.values())
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO ratings(session_id,subject_id,rater_id,role,values_json,total,submitted_at)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(session_id,subject_id,role) DO UPDATE SET
                     rater_id=excluded.rater_id, values_json=excluded.values_json,
                     total=excluded.total, submitted_at=excluded.submitted_at""",
                (session_id, subject_id, rater_id, role, json.dumps(values), total, now()),
            )

    def rating(self, session_id: int, subject_id: int, role: str):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM ratings WHERE session_id=? AND subject_id=? AND role=?",
                (session_id, subject_id, role),
            ).fetchone()

    def delete_rating(self, session_id: int, subject_id: int, role: str) -> None:
        if role not in {"self", "peer"}:
            raise ValueError("Nur Schülerbewertungen können erneut freigegeben werden.")
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM ratings WHERE session_id=? AND subject_id=? AND role=?",
                (session_id, subject_id, role),
            )

    def comparisons(self, session_id: int):
        with self.connect() as conn:
            return conn.execute(
                """SELECT r.student_id, r.list_position, r.student_code, r.name,
                          se.values_json self_values, se.total self_total,
                          se.submitted_at self_submitted_at,
                          pe.values_json peer_values, pe.total peer_total,
                          pe.submitted_at peer_submitted_at,
                          te.values_json teacher_values, te.total teacher_total,
                          te.submitted_at teacher_submitted_at
                   FROM session_roster r
                   LEFT JOIN ratings se ON se.session_id=r.session_id AND se.subject_id=r.student_id AND se.role='self'
                   LEFT JOIN ratings pe ON pe.session_id=r.session_id AND pe.subject_id=r.student_id AND pe.role='peer'
                   LEFT JOIN ratings te ON te.session_id=r.session_id AND te.subject_id=r.student_id AND te.role='teacher'
                   WHERE r.session_id=? ORDER BY r.list_position""",
                (session_id,),
            ).fetchall()
