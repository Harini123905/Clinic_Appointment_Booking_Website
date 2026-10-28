"""AI helpers for the booking page: pick a doctor from a description, and book by typing a sentence.

Both work with no API key (rules plus the clinic's own knowledge base). If GROQ_API_KEY is set, the language
model reads the sentence first and the rules fill in anything it missed.
"""
import json
import os
import re
from datetime import date, timedelta

import httpx

from chatbot import EMERGENCY_REPLY, GROQ_URL, SPECIALITY_WORDS, _is_emergency
from database import get_conn
from rag import get_retriever
from scheduling import DAY_NAMES, free_slots, works_on

WEEKDAYS = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1, "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3, "friday": 4, "fri": 4, "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}
MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
PARTS_OF_DAY = {  # (first slot, last slot) for each word
    "morning": ("09:00", "12:30"),
    "afternoon": ("14:00", "16:30"),
    "evening": ("16:00", "16:30"),
}
MAX_OPTIONS = 6
LOOK_AHEAD_DAYS = 30


# ---------- feature 1: which doctor should I see? ----------
def _speciality_from_words(text: str) -> str | None:
    lowered = text.lower()
    return next((s for s, words in SPECIALITY_WORDS.items() if any(w in lowered for w in words)), None)


def _doctors_for(speciality: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM doctors WHERE speciality = ? ORDER BY id", (speciality,)).fetchall()
    return [{"id": r["id"], "name": r["name"], "speciality": r["speciality"],
             "available_days": r["available_days"].split(",")} for r in rows]


def suggest_doctor(text: str) -> dict:
    """Return the type of doctor that fits the patient's description (never a diagnosis)."""
    if _is_emergency(text):
        return {"emergency": True, "message": EMERGENCY_REPLY}

    speciality, explanation, fallback = _speciality_from_words(text), None, False
    if not speciality:
        for chunk, _ in get_retriever().search(text, k=3):
            if chunk.kind == "kb" and chunk.speciality:
                speciality, explanation = chunk.speciality, chunk.text
                break
    if not speciality:
        speciality, fallback = "General Physician", True
        explanation = "I could not match that to one speciality. If you are unsure, start with the General Physician."

    return {
        "emergency": False,
        "speciality": speciality,
        "explanation": explanation,
        "fallback": fallback,
        "doctors": _doctors_for(speciality),
        "disclaimer": "This is general guidance only, not medical advice or a diagnosis.",
    }


# ---------- feature 2: book by typing ----------
def _parse_day(text: str, today: date) -> date | None:
    t = text.lower()
    if "day after tomorrow" in t:
        return today + timedelta(days=2)
    if re.search(r"\b(tomorrow|tmrw|tomorow)\b", t):
        return today + timedelta(days=1)
    if re.search(r"\btoday\b", t):
        return today

    iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if iso:
        try:
            return date(int(iso[1]), int(iso[2]), int(iso[3]))
        except ValueError:
            return None

    month_names = "|".join(MONTHS)
    for pattern, day_group, month_group in (
        (rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s*(?:of\s*)?({month_names})[a-z]*\b", 1, 2),
        (rf"\b({month_names})[a-z]*\s*(\d{{1,2}})(?:st|nd|rd|th)?\b", 2, 1),
    ):
        m = re.search(pattern, t)
        if m:
            try:
                found = date(today.year, MONTHS[m[month_group]], int(m[day_group]))
            except ValueError:
                return None
            return found if found >= today else found.replace(year=today.year + 1)

    m = re.search(r"\b(\d{1,2})/(\d{1,2})\b", t)  # 28/10 means 28 October
    if m:
        try:
            found = date(today.year, int(m[2]), int(m[1]))
            return found if found >= today else found.replace(year=today.year + 1)
        except ValueError:
            return None

    m = re.search(r"\b(" + "|".join(sorted(WEEKDAYS, key=len, reverse=True)) + r")\b", t)
    if m:
        ahead = (WEEKDAYS[m[1]] - today.weekday()) % 7
        return today + timedelta(days=ahead or 7)  # naming today's weekday means next week's
    return None


def _parse_part_of_day(text: str) -> str | None:
    t = text.lower()
    for word in ("morning", "evening"):
        if word in t:
            return word
    if "afternoon" in t or "after lunch" in t:
        return "afternoon"
    return None


def _parse_time(text: str) -> str | None:
    """'3 pm' or '10:30 am' -> '15:00' / '10:30' (nearest half hour)."""
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text.lower())
    if not m:
        return None
    hour, minute = int(m[1]) % 12, int(m[2] or 0)
    if m[3] == "pm":
        hour += 12
    if minute > 59:
        return None
    total = round((hour * 60 + minute) / 30) * 30  # nearest half hour, because slots are 30 minutes
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"


def _doctor_from_name(text: str, doctors) -> dict | None:
    lowered = text.lower()
    for d in doctors:
        parts = [p for p in re.sub(r"[^a-z' ]", " ", d["name"].lower()).split() if p != "dr"]
        if any(re.search(rf"\b{re.escape(p)}\b", lowered) for p in parts):
            return d
    return None


def _llm_extract(text: str, today: date) -> dict | None:
    """Ask the language model to read the sentence. Returns None without a key or on any problem."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    prompt = (
        f"Today is {today.isoformat()} ({DAY_NAMES[today.weekday()]}). A patient wrote a request to book a clinic appointment. "
        "Reply with ONLY a JSON object with these keys: "
        '"speciality" (one of General Physician, Paediatrician, Dermatologist, Orthopaedic Specialist, Gynaecologist, or null), '
        '"doctor_name" (a doctor name if given, else null), "date" (YYYY-MM-DD resolved from today, or null), '
        '"part_of_day" (morning, afternoon, evening or null), "time" (HH:MM 24 hour or null). '
        "Never diagnose. Only pick a speciality the patient asked for or whose area they described."
    )
    try:
        response = httpx.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": text}],
                "temperature": 0,
                "max_tokens": 200,
                "response_format": {"type": "json_object"},
            },
            timeout=15,
        )
        response.raise_for_status()
        return json.loads(response.json()["choices"][0]["message"]["content"])
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError):
        return None


def _clean_llm(raw: dict | None, doctors) -> dict:
    """Keep only values we can trust from the model."""
    out: dict = {}
    if not isinstance(raw, dict):
        return out
    if raw.get("speciality") in SPECIALITY_WORDS:
        out["speciality"] = raw["speciality"]
    if isinstance(raw.get("doctor_name"), str):
        out["doctor"] = _doctor_from_name(raw["doctor_name"], doctors)
    if isinstance(raw.get("date"), str):
        try:
            out["day"] = date.fromisoformat(raw["date"])
        except ValueError:
            pass
    if raw.get("part_of_day") in PARTS_OF_DAY:
        out["part"] = raw["part_of_day"]
    if isinstance(raw.get("time"), str) and re.fullmatch(r"\d{2}:\d{2}", raw["time"]):
        out["time"] = raw["time"]
    return out


def works_on_day(doctor: dict, day: date) -> bool:
    return DAY_NAMES[day.weekday()] in doctor["available_days"].split(",")


def _option(doctor, day: date, slot: str) -> dict:
    return {"doctor_id": doctor["id"], "name": doctor["name"], "speciality": doctor["speciality"],
            "date": day.isoformat(), "slot_time": slot}


def _in_part(slot: str, part: str | None) -> bool:
    if not part:
        return True
    first, last = PARTS_OF_DAY[part]
    return first <= slot <= last


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def parse_booking(text: str, today: date | None = None) -> dict:
    """Understand 'skin doctor tomorrow morning' and return real free slots the patient can pick."""
    today = today or date.today()
    if _is_emergency(text):
        return {"emergency": True, "message": EMERGENCY_REPLY, "options": [], "understood": {}}

    with get_conn() as conn:
        all_doctors = [dict(r) for r in conn.execute("SELECT * FROM doctors ORDER BY id").fetchall()]

    found = _clean_llm(_llm_extract(text, today), all_doctors)  # empty when there is no API key
    doctor = found.get("doctor") or _doctor_from_name(text, all_doctors)
    speciality = doctor["speciality"] if doctor else (found.get("speciality") or _speciality_from_words(text))
    explanation = None
    if not speciality:  # a described problem, e.g. "rash on my arm tomorrow"
        suggestion = suggest_doctor(text)
        if suggestion.get("emergency"):
            return {"emergency": True, "message": suggestion["message"], "options": [], "understood": {}}
        if not suggestion["fallback"]:
            speciality, explanation = suggestion["speciality"], suggestion["explanation"]

    day = found.get("day") or _parse_day(text, today)
    part = found.get("part") or _parse_part_of_day(text)
    wanted_time = found.get("time") or _parse_time(text)
    understood = {"speciality": speciality, "doctor": doctor["name"] if doctor else None,
                  "date": day.isoformat() if day else None, "part_of_day": part, "time": wanted_time}

    if not speciality:
        return {"emergency": False, "understood": understood, "options": [],
                "message": "Tell me which doctor or what the problem is, for example "
                           "\"skin doctor tomorrow morning\" or \"Dr Rahul on Friday at 10 am\"."}

    candidates = [doctor] if doctor else [d for d in all_doctors if d["speciality"] == speciality]
    notes: list[str] = []
    if day and day < today:
        notes.append("That date has already passed, so here are the next free times.")
        day = None
    if day and day > today + timedelta(days=LOOK_AHEAD_DAYS):
        notes.append(f"We only book up to {LOOK_AHEAD_DAYS} days ahead, so here are the next free times.")
        day = None
    if day and day.weekday() == 6:
        notes.append("The clinic is closed on Sundays, so here are the next free times.")
        day = None

    def sort_key(opt):
        return (opt["date"], abs(_minutes(opt["slot_time"]) - _minutes(wanted_time)) if wanted_time else 0, opt["slot_time"])

    options: list[dict] = []
    with get_conn() as conn:
        if day:
            for d in candidates:
                options += [_option(d, day, s) for s in free_slots(conn, d, day) if _in_part(s, part)]
            options.sort(key=sort_key)
            options = options[:MAX_OPTIONS]
            if not options:
                if not any(works_on_day(d, day) for d in candidates):
                    names = " and ".join(d["name"] for d in candidates)
                    notes.append(f"{names} {'does' if len(candidates) == 1 else 'do'} not work on {day.strftime('%A')}s, so here are the next free times.")
                else:
                    notes.append("There are no free times that match on that day, so here are the next free times.")
        if not options:
            for offset in range(0, LOOK_AHEAD_DAYS + 1):
                d_day = today + timedelta(days=offset)
                if day and d_day <= day:
                    continue
                for d in candidates:
                    options += [_option(d, d_day, s) for s in free_slots(conn, d, d_day) if _in_part(s, part)]
                if len(options) >= MAX_OPTIONS:
                    break
            options.sort(key=sort_key)
            options = options[:MAX_OPTIONS]

    who = doctor["name"] if doctor else f"our {speciality}"
    if options:
        notes.append(f"Here are free times with {who}. Tap one to choose it.")
    else:
        notes.append(f"I could not find free times with {who} in the next {LOOK_AHEAD_DAYS} days. Please call reception.")
    return {"emergency": False, "understood": understood, "explanation": explanation,
            "options": options, "message": " ".join(notes)}