"""Slot rules shared by the booking API, the chatbot and the AI helpers."""
import sqlite3
from datetime import date, datetime

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SLOT_TIMES = [f"{h:02d}:{m:02d}" for h in (9, 10, 11, 12, 14, 15, 16) for m in (0, 30)]  # 1-2 PM is lunch


def works_on(doctor: sqlite3.Row, day: date) -> bool:
    return DAY_NAMES[day.weekday()] in doctor["available_days"].split(",")


def free_slots(conn, doctor: sqlite3.Row, day: date) -> list[str]:
    if not works_on(doctor, day):
        return []
    booked = {
        r["slot_time"]
        for r in conn.execute(
            "SELECT slot_time FROM appointments WHERE doctor_id = ? AND appointment_date = ? AND status = 'confirmed'",
            (doctor["id"], day.isoformat()),
        )
    }
    slots = [s for s in SLOT_TIMES if s not in booked]
    if day == date.today():
        now = datetime.now().strftime("%H:%M")
        slots = [s for s in slots if s > now]
    return slots