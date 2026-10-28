"""SQLite database setup and seed data for Kaveri Family Clinic."""
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("CLINIC_DB", Path(__file__).parent / "clinic.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS doctors (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL,
    speciality       TEXT NOT NULL,
    bio              TEXT NOT NULL,
    experience_years INTEGER NOT NULL,
    available_days   TEXT NOT NULL            -- e.g. "Mon,Wed,Fri"
);

CREATE TABLE IF NOT EXISTS appointments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    reference        TEXT NOT NULL UNIQUE,
    doctor_id        INTEGER NOT NULL REFERENCES doctors(id),
    appointment_date TEXT NOT NULL,           -- YYYY-MM-DD
    slot_time        TEXT NOT NULL,           -- HH:MM
    patient_name     TEXT NOT NULL,
    phone            TEXT NOT NULL,
    reason           TEXT,
    status           TEXT NOT NULL DEFAULT 'confirmed',   -- confirmed or cancelled
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- the database itself refuses a double booking, but a cancelled slot can be booked again
CREATE UNIQUE INDEX IF NOT EXISTS one_confirmed_per_slot
    ON appointments (doctor_id, appointment_date, slot_time) WHERE status = 'confirmed';

-- what patients asked the chatbot: the text is only kept when the bot could not answer
CREATE TABLE IF NOT EXISTS chat_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    mode       TEXT NOT NULL,
    message    TEXT
);
"""

DOCTORS = [
    ("Dr. Ananya Rao", "General Physician",
     "Looks after fevers, infections, blood pressure, diabetes check-ups and everyday health concerns for adults.",
     12, "Mon,Tue,Wed,Thu,Fri"),
    ("Dr. Rahul Menon", "Paediatrician",
     "Cares for babies, children and teenagers, including vaccinations, growth checks and common childhood illnesses.",
     9, "Mon,Wed,Fri"),
    ("Dr. Meera Iyer", "Dermatologist",
     "Treats acne, rashes, eczema, hair loss and other skin, hair and nail concerns.",
     8, "Tue,Thu,Sat"),
    ("Dr. Karthik Nair", "Orthopaedic Specialist",
     "Helps with joint pain, back and neck pain, sports injuries and bone health.",
     15, "Mon,Tue,Thu"),
    ("Dr. Sofia D'Souza", "Gynaecologist",
     "Provides women's health care, including check-ups, pregnancy care and menstrual health.",
     11, "Wed,Thu,Fri"),
]


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_old_appointments(conn: sqlite3.Connection) -> None:
    """Older databases had UNIQUE (doctor, date, time) on every row, so a cancelled slot could never be re-booked."""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='appointments'").fetchone()
    if row and "UNIQUE (doctor_id" in row["sql"]:
        conn.executescript(
            """
            ALTER TABLE appointments RENAME TO appointments_old;
            """ + SCHEMA.split("CREATE TABLE IF NOT EXISTS chat_log")[0] + """
            INSERT INTO appointments (id, reference, doctor_id, appointment_date, slot_time, patient_name, phone, reason, status, created_at)
                SELECT id, reference, doctor_id, appointment_date, slot_time, patient_name, phone, reason, status, created_at
                FROM appointments_old;
            DROP TABLE appointments_old;
            """
        )


def init_db() -> None:
    """Create tables and seed the doctors on first run."""
    with get_conn() as conn:
        _migrate_old_appointments(conn)
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO doctors (name, speciality, bio, experience_years, available_days) "
                "VALUES (?, ?, ?, ?, ?)",
                DOCTORS,
            )