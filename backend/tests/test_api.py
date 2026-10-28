import os
import tempfile
from datetime import date, timedelta

os.environ["CLINIC_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.pop("GROQ_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def next_weekday(day_name: str, start_offset: int = 1) -> str:
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    d = date.today() + timedelta(days=start_offset)
    while names[d.weekday()] != day_name:
        d += timedelta(days=1)
    return d.isoformat()


def booking(**over):
    base = {"doctor_id": 1, "appointment_date": next_weekday("Mon"), "slot_time": "09:00",
            "patient_name": "Test Patient", "phone": "+91 90000 11111"}
    base.update(over)
    return base


def test_all():
    with TestClient(app) as c:
        # doctors
        doctors = c.get("/api/doctors").json()
        assert len(doctors) == 5 and doctors[0]["available_days"][0] == "Mon"
        assert len(c.get("/api/doctors?speciality=Dermatologist").json()) == 1

        # slots: lunch hour excluded, Sunday empty
        monday = next_weekday("Mon")
        slots = c.get(f"/api/doctors/1/slots?date={monday}").json()["slots"]
        assert "13:00" not in slots and "09:00" in slots
        assert c.get(f"/api/doctors/1/slots?date={next_weekday('Sun')}").json()["slots"] == []

        # booking works, then slot disappears and double booking is refused
        r = c.post("/api/appointments", json=booking())
        assert r.status_code == 201, r.text
        ref = r.json()["reference"]
        assert ref.startswith("CLN-")
        assert "09:00" not in c.get(f"/api/doctors/1/slots?date={monday}").json()["slots"]
        assert c.post("/api/appointments", json=booking()).status_code == 409
        assert c.get(f"/api/appointments/{ref.lower()}").json()["patient_name"] == "Test Patient"

        # validation
        assert c.post("/api/appointments", json=booking(phone="abc")).status_code == 422
        assert c.post("/api/appointments", json=booking(patient_name=" ")).status_code == 422
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        assert c.post("/api/appointments", json=booking(appointment_date=yesterday)).status_code == 400
        far = (date.today() + timedelta(days=90)).isoformat()
        assert c.post("/api/appointments", json=booking(appointment_date=far)).status_code == 400
        assert c.post("/api/appointments", json=booking(slot_time="13:00")).status_code == 400
        # Dr. Rahul (id 2) does not work on Tuesdays
        assert c.post("/api/appointments", json=booking(doctor_id=2, appointment_date=next_weekday("Tue"))).status_code == 400
        assert c.get("/api/appointments/CLN-NOPE00").status_code == 404

        # next available
        assert len(c.get("/api/next-available").json()) == 5


def test_chatbot():
    with TestClient(app) as c:
        r = c.post("/api/chat", json={"message": "I have a skin rash and itching, who should I see?"}).json()
        assert r["suggested_speciality"] == "Dermatologist"
        assert "not medical advice" in r["answer"].lower()

        r = c.post("/api/chat", json={"message": "I have a fever and cough"}).json()
        assert r["suggested_speciality"] == "General Physician"
        assert "Physician For" not in r["answer"]

        r = c.post("/api/chat", json={"message": "What are your opening hours?"}).json()
        assert "9:00" in r["answer"]

        r = c.post("/api/chat", json={"message": "I have severe chest pain"}).json()
        assert r["mode"] == "emergency" and r["sources"] == []

        r = c.post("/api/chat", json={"message": "Who won the cricket world cup in 2011?"}).json()
        assert r["mode"] == "no_match"

        r = c.post("/api/chat", json={"message": "What is the fee for a consultation?"}).json()
        assert "600" in r["answer"]
