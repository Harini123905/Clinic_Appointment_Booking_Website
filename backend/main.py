"""Kaveri Family Clinic - FastAPI backend (booking + RAG chatbot)."""
import os
import re
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

load_dotenv()

from assistant import parse_booking, suggest_doctor  # noqa: E402
from chatbot import answer as chatbot_answer  # noqa: E402
from database import get_conn, init_db  # noqa: E402
from scheduling import DAY_NAMES, SLOT_TIMES, free_slots as _free_slots, works_on as _works_on  # noqa: E402

MAX_DAYS_AHEAD = 30


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Kaveri Family Clinic API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- helpers ----------
def _doctor_or_404(conn, doctor_id: int) -> sqlite3.Row:
    doctor = conn.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
    if doctor is None:
        raise HTTPException(404, "Doctor not found.")
    return doctor


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(400, "Date must be in YYYY-MM-DD format.")


def _doctor_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["available_days"] = row["available_days"].split(",")
    return d


# ---------- schemas ----------
class BookingRequest(BaseModel):
    doctor_id: int
    appointment_date: str
    slot_time: str
    patient_name: str = Field(min_length=2, max_length=80)
    phone: str
    reason: str | None = Field(default=None, max_length=300)

    @field_validator("patient_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("Please enter the patient's full name.")
        return v

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str) -> str:
        digits = re.sub(r"[\s\-()]", "", v)
        if not re.fullmatch(r"\+?\d{8,15}", digits):
            raise ValueError("Please enter a valid phone number (8 to 15 digits).")
        return digits


class ChatTurn(BaseModel):
    role: str
    content: str = Field(max_length=800)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    history: list[ChatTurn] = []


# ---------- routes ----------
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/doctors")
def list_doctors(speciality: str | None = None):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM doctors ORDER BY id").fetchall()
    doctors = [_doctor_dict(r) for r in rows]
    if speciality:
        doctors = [d for d in doctors if d["speciality"].lower() == speciality.lower()]
    return doctors


@app.get("/api/doctors/{doctor_id}/slots")
def doctor_slots(doctor_id: int, date_: str = Query(alias="date")):
    day = _parse_date(date_)
    with get_conn() as conn:
        doctor = _doctor_or_404(conn, doctor_id)
        return {"doctor_id": doctor_id, "date": day.isoformat(), "slots": _free_slots(conn, doctor, day)}


@app.get("/api/next-available")
def next_available():
    """For each doctor, the first free slot in the next two weeks."""
    results = []
    with get_conn() as conn:
        for doctor in conn.execute("SELECT * FROM doctors ORDER BY id").fetchall():
            for offset in range(0, 15):
                day = date.today() + timedelta(days=offset)
                slots = _free_slots(conn, doctor, day)
                if slots:
                    results.append({
                        "doctor_id": doctor["id"], "name": doctor["name"], "speciality": doctor["speciality"],
                        "date": day.isoformat(), "slot_time": slots[0],
                    })
                    break
    return results


@app.post("/api/appointments", status_code=201)
def create_appointment(body: BookingRequest):
    day = _parse_date(body.appointment_date)
    today = date.today()
    if day < today:
        raise HTTPException(400, "That date has already passed. Please choose a future date.")
    if day > today + timedelta(days=MAX_DAYS_AHEAD):
        raise HTTPException(400, f"Appointments can only be booked up to {MAX_DAYS_AHEAD} days ahead.")
    if body.slot_time not in SLOT_TIMES:
        raise HTTPException(400, "That time is not a valid appointment slot.")

    with get_conn() as conn:
        doctor = _doctor_or_404(conn, body.doctor_id)
        if not _works_on(doctor, day):
            days = ", ".join(doctor["available_days"].split(","))
            raise HTTPException(400, f"{doctor['name']} is not available on that day. Available days: {days}.")
        if body.slot_time not in _free_slots(conn, doctor, day):
            raise HTTPException(409, "Sorry, that slot is no longer available. Please choose another time.")

        for _ in range(5):  # retry in the very unlikely case of a duplicate reference
            reference = "CLN-" + secrets.token_hex(3).upper()
            try:
                conn.execute(
                    "INSERT INTO appointments (reference, doctor_id, appointment_date, slot_time, patient_name, phone, reason) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (reference, body.doctor_id, day.isoformat(), body.slot_time, body.patient_name, body.phone, body.reason),
                )
                break
            except sqlite3.IntegrityError as exc:
                if "appointments.reference" in str(exc):
                    continue
                # two patients clicked at the same moment: the UNIQUE constraint caught it
                raise HTTPException(409, "Sorry, that slot was just taken. Please choose another time.")
        else:
            raise HTTPException(500, "Could not create a booking reference. Please try again.")

        return _appointment_payload(conn, reference)


def _appointment_payload(conn, reference: str) -> dict:
    row = conn.execute(
        "SELECT a.*, d.name AS doctor_name, d.speciality FROM appointments a "
        "JOIN doctors d ON d.id = a.doctor_id WHERE a.reference = ?",
        (reference,),
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Booking not found. Please check the reference number.")
    return {
        "reference": row["reference"], "doctor_id": row["doctor_id"], "doctor_name": row["doctor_name"],
        "speciality": row["speciality"], "appointment_date": row["appointment_date"], "slot_time": row["slot_time"],
        "patient_name": row["patient_name"], "reason": row["reason"], "status": row["status"],
    }


@app.get("/api/appointments/{reference}")
def get_appointment(reference: str):
    with get_conn() as conn:
        return _appointment_payload(conn, reference.upper())


class DescribeRequest(BaseModel):
    text: str = Field(min_length=2, max_length=300)


@app.post("/api/suggest-doctor")
def suggest(body: DescribeRequest):
    """AI helper: describe the problem, get the type of doctor to see."""
    return suggest_doctor(body.text)


@app.post("/api/parse-booking")
def parse(body: DescribeRequest):
    """AI helper: 'skin doctor tomorrow morning' -> real free slots."""
    return parse_booking(body.text)


@app.post("/api/chat")
def chat(body: ChatRequest):
    result = chatbot_answer(body.message, [t.model_dump() for t in body.history])
    # keep the question text only when the bot could not answer, so staff can improve the knowledge base
    unanswered = result["mode"] == "no_match"
    with get_conn() as conn:
        conn.execute("INSERT INTO chat_log (mode, message) VALUES (?, ?)",
                     (result["mode"], body.message.strip()[:200] if unanswered else None))
    return result


# ---------- staff insights ----------
def _require_admin(key: str | None) -> None:
    expected = os.getenv("ADMIN_KEY", "")
    if not expected:
        raise HTTPException(503, "The staff page is switched off. Set ADMIN_KEY in the backend .env file to use it.")
    if not key or not secrets.compare_digest(key, expected):
        raise HTTPException(401, "Wrong staff key.")


@app.get("/api/admin/insights")
def insights(x_admin_key: str | None = Header(default=None)):
    _require_admin(x_admin_key)
    today = date.today().isoformat()
    with get_conn() as conn:
        one = lambda sql, *args: conn.execute(sql, args).fetchone()[0]  # noqa: E731
        by_speciality = [dict(r) for r in conn.execute(
            "SELECT d.speciality AS label, COUNT(*) AS count FROM appointments a JOIN doctors d ON d.id = a.doctor_id "
            "WHERE a.status = 'confirmed' GROUP BY d.speciality ORDER BY count DESC")]
        weekday_counts = {name: 0 for name in DAY_NAMES[:6]}
        for r in conn.execute("SELECT appointment_date FROM appointments WHERE status = 'confirmed'"):
            name = DAY_NAMES[date.fromisoformat(r["appointment_date"]).weekday()]
            if name in weekday_counts:
                weekday_counts[name] += 1
        chat_modes = [dict(r) for r in conn.execute(
            "SELECT mode AS label, COUNT(*) AS count FROM chat_log GROUP BY mode ORDER BY count DESC")]
        unanswered = [dict(r) for r in conn.execute(
            "SELECT lower(message) AS question, COUNT(*) AS count, MAX(created_at) AS last_asked FROM chat_log "
            "WHERE mode = 'no_match' AND message IS NOT NULL GROUP BY lower(message) ORDER BY count DESC, last_asked DESC LIMIT 10")]
        confirmed = one("SELECT COUNT(*) FROM appointments WHERE status = 'confirmed'")
        cancelled = one("SELECT COUNT(*) FROM appointments WHERE status = 'cancelled'")
        return {
            "totals": {
                "confirmed": confirmed,
                "cancelled": cancelled,
                "upcoming": one("SELECT COUNT(*) FROM appointments WHERE status = 'confirmed' AND appointment_date >= ?", today),
                "chat_messages": one("SELECT COUNT(*) FROM chat_log"),
                "cancel_rate_percent": round(100 * cancelled / (confirmed + cancelled), 1) if confirmed + cancelled else 0,
            },
            "bookings_by_speciality": by_speciality,
            "bookings_by_weekday": [{"label": k, "count": v} for k, v in weekday_counts.items()],
            "chat_modes": chat_modes,
            "unanswered_questions": unanswered,
        }