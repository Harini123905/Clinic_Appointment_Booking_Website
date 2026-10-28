"""Fill the database with FAKE bookings and chat questions so the staff insights page has something to show.

Run it once before recording your demo video:   python seed_demo.py
All names and phone numbers below are invented. To start clean again, delete clinic.db and restart the backend.
"""
import random
from datetime import date, timedelta

from database import get_conn, init_db
from scheduling import free_slots

random.seed(7)
FIRST = ["Priya", "Arjun", "Meena", "Karthik", "Divya", "Suresh", "Lakshmi", "Vignesh", "Anitha", "Ramesh", "Kavya", "Naveen"]
LAST = ["Kumar", "Raj", "Devi", "Selvam", "Pillai", "Nathan", "Krishnan", "Babu"]
REASONS = ["Fever and cold", "Skin rash", "Child vaccination", "Knee pain", "Routine check-up", "Back pain", "Period problems", None]
UNANSWERED = [
    "do you have a pharmacy inside the clinic", "do you accept health insurance", "is there a lab for blood tests",
    "can I get a medical certificate", "do you do home visits", "is there a lift for wheelchair users",
]


def main() -> None:
    init_db()
    made = 0
    with get_conn() as conn:
        doctors = conn.execute("SELECT * FROM doctors").fetchall()
        for offset in range(0, 21):
            day = date.today() + timedelta(days=offset)
            for doctor in doctors:
                slots = free_slots(conn, doctor, day)
                random.shuffle(slots)
                for slot in slots[: random.randint(0, 3)]:
                    status = "cancelled" if random.random() < 0.12 else "confirmed"
                    conn.execute(
                        "INSERT INTO appointments (reference, doctor_id, appointment_date, slot_time, patient_name, phone, reason, status) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (f"CLN-D{random.randrange(16**5):05X}", doctor["id"], day.isoformat(), slot,
                         f"{random.choice(FIRST)} {random.choice(LAST)}", f"+9190000{random.randrange(10**5):05d}",
                         random.choice(REASONS), status),
                    )
                    made += 1
        modes = ["retrieval"] * 30 + ["small_talk"] * 12 + ["booking"] * 8 + ["booking_status"] * 4 + ["cancelled"] * 2 + ["emergency"] * 1
        for mode in modes:
            conn.execute("INSERT INTO chat_log (mode, message) VALUES (?, NULL)", (mode,))
        for question in UNANSWERED:
            for _ in range(random.randint(1, 4)):
                conn.execute("INSERT INTO chat_log (mode, message) VALUES ('no_match', ?)", (question,))
    print(f"Added {made} fake bookings and some chat questions. Open http://localhost:3000/admin")


if __name__ == "__main__":
    main()