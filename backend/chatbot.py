"""Chatbot pipeline: safety check -> retrieve -> generate (LLM, or retrieval-only fallback)."""
import os
import re
from datetime import datetime, timedelta

import httpx

from database import get_conn
from rag import get_retriever

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

EMERGENCY_TERMS = [
    "chest pain", "can't breathe", "cannot breathe", "difficulty breathing", "trouble breathing",
    "not breathing", "heavy bleeding", "severe bleeding", "unconscious", "fainted", "seizure",
    "stroke", "heart attack", "overdose", "poison", "suicid", "kill myself", "want to die",
]

EMERGENCY_REPLY = (
    "This may be an emergency, and I cannot help with urgent symptoms. Please call your local "
    "emergency number now (112 in India, 000 in Australia) or go to the nearest hospital "
    "emergency department. If someone is with you, please ask them to stay with you."
)

DISCLAIMER = "This is general guidance only, not medical advice or a diagnosis."

# ---- small talk: greetings and thanks never need the knowledge base ----
GREETING_RE = re.compile(
    r"^\s*(hi+|hii+|hello+|hey+|heya|hai|good\s*(morning|afternoon|evening)|namaste|vanakkam)\b[\s!.,?]*"
    r"(there|team|doctor|sir|madam|assistant|bot)?[\s!.?]*$", re.I)
THANKS_RE = re.compile(
    r"^\s*(ok(ay)?[\s,]*)?(thanks?(\s*you)?(\s*so\s*much|\s*a\s*lot)?|thx|ok(ay)?|great|nice|cool|got\s*it|alright)[\s!.,?]*$", re.I)
BYE_RE = re.compile(r"^\s*(bye|goodbye|see\s*you|take care)\b[\s!.?]*$", re.I)
ABOUT_RE = re.compile(r"\b(who are you|what are you|what can you do|how can you help|help me|what do you do)\b", re.I)

# asking for the doctors themselves (not "which doctor should I see for a rash")
DOCTOR_LIST_RE = re.compile(
    r"\b(doctors?\s*(list|details?|names?|info|information|timings?|schedule|profiles?)"
    r"|(list|details?|names?)\s*of\s*(the\s*|all\s*(the\s*)?|your\s*|our\s*)?doctors?"
    r"|(list|show|all|our|your|available|tell\s*me\s*about)\s*(me\s*)?(the\s*|all\s*(the\s*)?|our\s*|your\s*)?doctors?\b"
    r"|who\s*are\s*(the|your|our)\s*doctors?|which\s*doctors"
    r"|(is|are)\s*(there|any)\s*(a\s*|any\s*)?doctors?|doctors?\s*(is\s*|are\s*)?(there|available|present))", re.I)

# "I want an appointment for a dermatologist" -> go straight to booking with that speciality
BOOK_INTENT_RE = re.compile(r"\b(book|booking|appointment|consult|consultation|see|visit|meet)\b", re.I)
NOT_BOOKING_RE = re.compile(r"\b(cancel\w*|change|changing|reschedul\w*|fees?|cost|price|how long|length|timings?|hours)\b", re.I)
SPECIALITY_WORDS = {
    "Dermatologist": ["dermatologist", "dermatology", "skin doctor", "skin specialist"],
    "Paediatrician": ["paediatrician", "pediatrician", "paediatric", "pediatric", "child specialist", "children doctor"],
    "Gynaecologist": ["gynaecologist", "gynecologist", "gynaecology", "gynecology"],
    "Orthopaedic Specialist": ["orthopaedic", "orthopedic", "orthopaedics", "orthopedics", "bone doctor"],
    "General Physician": ["general physician", "general doctor", "physician", "general medicine"],
}


def _booking_for_speciality(message: str, chunks) -> dict | None:
    """If the patient wants an appointment and names a speciality (or a doctor), answer with that doctor."""
    if not BOOK_INTENT_RE.search(message) or NOT_BOOKING_RE.search(message):
        return None
    lowered = message.lower()
    speciality = next((s for s, words in SPECIALITY_WORDS.items() if any(w in lowered for w in words)), None)
    doctors = [ch for ch in chunks if ch.kind == "doctor"]
    if speciality is None:  # maybe they named a doctor, e.g. "appointment with Dr Meera"
        for ch in doctors:
            first, last = ch.title.split("(")[0].replace("Dr.", "").split()[:2]
            if first.lower() in lowered or last.lower() in lowered:
                speciality = ch.speciality
                break
    if speciality is None:
        return None
    matches = [ch for ch in doctors if ch.speciality == speciality]
    if not matches:
        return None
    lines = []
    for ch in matches:
        days = re.search(r"Available on: (.*)\.$", ch.text)
        lines.append(f"{ch.title.split(' (')[0]} ({speciality}) is available on {days.group(1) if days else 'set days'}.")
    text = " ".join(lines) + " Please use the button below to choose a day and time."
    return _reply(text, "booking", [m.title for m in matches], speciality, "book")


# ---- the chatbot can look up and cancel a booking from its reference (CLN-XXXXXX) ----
REF_RE = re.compile(r"\bCLN-[0-9A-F]{6}\b", re.I)
CANCEL_RE = re.compile(r"\bcancel\w*\b", re.I)
HOW_RE = re.compile(r"\b(how|can i|can we|what if|policy|charge|charges|allowed|possible|refund)\b", re.I)
MINE_RE = re.compile(r"\b(my|the)\s+(appointment|booking)\b", re.I)
YES_RE = re.compile(r"^\s*(yes|yeah|yep|y|confirm|go ahead|please do|cancel it|yes,?\s*cancel( it)?)[\s!.]*$", re.I)
NO_RE = re.compile(r"^\s*(no|nope|n|keep it|do not|don't|never mind|leave it)\b", re.I)
CONFIRM_MARK = "Reply YES to cancel"
CANCEL_NOTICE_HOURS = 4


def _when(day: str, slot: str) -> str:
    d = datetime.strptime(day, "%Y-%m-%d")
    t = datetime.strptime(slot, "%H:%M")
    return f"{d.strftime('%A')} {d.day} {d.strftime('%B %Y')} at {t.hour % 12 or 12}:{t.minute:02d} {'PM' if t.hour >= 12 else 'AM'}"


def _find_booking(reference: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT a.*, d.name AS doctor_name, d.speciality FROM appointments a "
            "JOIN doctors d ON d.id = a.doctor_id WHERE a.reference = ?", (reference,)).fetchone()


def _booking_summary(b) -> str:
    return f"{b['reference']}: {b['doctor_name']} ({b['speciality']}) on {_when(b['appointment_date'], b['slot_time'])}, for {b['patient_name']}."


def _history_reference(history: list[dict]) -> str | None:
    for turn in reversed(history):
        found = REF_RE.search(turn.get("content", ""))
        if found:
            return found[0].upper()
    return None


def _appointment_flow(message: str, history: list[dict]) -> dict | None:
    """Status and cancellation by reference. Returns None when the message is not about a specific booking."""
    last = history[-1] if history else {}
    pending = None
    if last.get("role") == "assistant" and CONFIRM_MARK in last.get("content", ""):
        found = REF_RE.search(last["content"])
        pending = found[0].upper() if found else None

    if pending and NO_RE.match(message):
        return _reply(f"Okay, I have kept your appointment {pending}.", "booking_status")
    if pending and YES_RE.match(message):
        return _cancel(pending)

    in_message = REF_RE.search(message)
    asking_how = bool(HOW_RE.search(message))
    wants_cancel = bool(CANCEL_RE.search(message)) and not asking_how
    wants_status = bool(in_message or MINE_RE.search(message)) and not asking_how
    if not (wants_cancel or wants_status):
        return None

    reference = in_message[0].upper() if in_message else _history_reference(history)
    if not reference:
        return _reply("Please send your booking reference. It starts with CLN, for example CLN-7F3A9C.", "need_reference")
    booking = _find_booking(reference)
    if booking is None:
        return _reply(f"I could not find a booking with reference {reference}. Please check it, or call reception on +91 90000 12345.", "booking_not_found")

    if not wants_cancel:
        state = " This appointment has been cancelled." if booking["status"] == "cancelled" else ""
        return _reply(_booking_summary(booking) + state, "booking_status", action="book" if booking["status"] == "cancelled" else None)
    if booking["status"] == "cancelled":
        return _reply(f"{reference} is already cancelled.", "booking_status", action="book")
    if not _can_cancel(booking):
        return _reply(f"{_booking_summary(booking)}\n\nThis appointment is less than {CANCEL_NOTICE_HOURS} hours away, so I cannot cancel it here. "
                      "Please call reception on +91 90000 12345.", "booking_status")
    return _reply(f"{_booking_summary(booking)}\n\n{CONFIRM_MARK} {reference}, or NO to keep it.", "cancel_confirm")


def _can_cancel(booking) -> bool:
    start = datetime.strptime(f"{booking['appointment_date']} {booking['slot_time']}", "%Y-%m-%d %H:%M")
    return start - datetime.now() >= timedelta(hours=CANCEL_NOTICE_HOURS)


def _cancel(reference: str) -> dict:
    booking = _find_booking(reference)
    if booking is None:
        return _reply(f"I could not find a booking with reference {reference}.", "booking_not_found")
    if booking["status"] == "cancelled":
        return _reply(f"{reference} is already cancelled.", "booking_status", action="book")
    if not _can_cancel(booking):
        return _reply("That appointment is now less than 4 hours away, so I cannot cancel it here. Please call reception on +91 90000 12345.", "booking_status")
    with get_conn() as conn:
        conn.execute("UPDATE appointments SET status = 'cancelled' WHERE reference = ? AND status = 'confirmed'", (reference,))
    return _reply(f"Done. Your appointment {reference} with {booking['doctor_name']} on "
                  f"{_when(booking['appointment_date'], booking['slot_time'])} has been cancelled. You can book a new one any time.",
                  "cancelled", action="book")


GREETING_REPLY = ("Hello! I am the Kaveri Family Clinic assistant. I can help you book an appointment, "
                  "show our doctors and timings, share fees and the address, or suggest which type of doctor to see.")
THANKS_REPLY = "You are welcome! Let me know if you need anything else."
BYE_REPLY = "Goodbye, and take care!"
ABOUT_REPLY = ("I am the clinic's virtual assistant. I can explain how to book an appointment, list our doctors, "
               "share opening hours, fees and the address, and suggest which type of doctor to see. "
               "I cannot give medical advice.")
NO_MATCH_REPLY = ("I am sorry, I am not sure about that. I can help with booking, doctors, opening hours, fees and "
                  "the clinic address. For anything else, please call reception on +91 90000 12345.")

SYSTEM_PROMPT = """You are the virtual assistant for Kaveri Family Clinic.
Rules:
1. Answer ONLY from the CONTEXT below. If the answer is not in the context, say you do not have that
   information and suggest calling reception.
2. For health concerns, only say which type of doctor to see. Never diagnose, never suggest medicines or doses.
3. Use simple British English. Keep the answer under 110 words.
4. Do not mention the word "context" to the patient."""


def _is_emergency(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in EMERGENCY_TERMS)


def _small_talk(message: str) -> str | None:
    if GREETING_RE.match(message):
        return GREETING_REPLY
    if THANKS_RE.match(message):
        return THANKS_REPLY
    if BYE_RE.match(message):
        return BYE_REPLY
    if ABOUT_RE.search(message):
        return ABOUT_REPLY
    return None


def _call_llm(question: str, context: str, history: list[dict]) -> str | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n\nCONTEXT:\n{context}"}]
    messages += [m for m in history[-4:] if m.get("role") in ("user", "assistant")]
    messages.append({"role": "user", "content": question})
    try:
        response = httpx.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 300,
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        return None  # fall back to retrieval-only mode


def _reply(text: str, mode: str, sources=None, speciality=None, action=None) -> dict:
    return {"answer": text, "sources": sources or [], "suggested_speciality": speciality, "mode": mode, "action": action}


def answer(message: str, history: list[dict] | None = None) -> dict:
    history = history or []

    if _is_emergency(message):
        return _reply(EMERGENCY_REPLY, "emergency")

    flow = _appointment_flow(message, history)
    if flow:
        return flow

    chat = _small_talk(message)
    if chat:
        return _reply(chat, "small_talk")

    retriever = get_retriever()
    booking = _booking_for_speciality(message, retriever.chunks)
    if booking:
        return booking
    if DOCTOR_LIST_RE.search(message):
        results = [(ch, 1.0) for ch in retriever.chunks if ch.kind == "doctor_list"]
    else:
        results = retriever.search(message)
    if not results:
        return _reply(NO_MATCH_REPLY, "no_match")

    best = results[0][0]
    if best.kind in ("doctor_list", "booking"):
        results = results[:1]  # the best match is a complete answer on its own, so do not mix in other topics

    context = "\n\n".join(f"[{c.title}]\n{c.text}" for c, _ in results)
    sources = [c.title for c, _ in results]
    # health guidance and the "Book a ..." button depend on the BEST match only
    speciality = best.speciality if best.kind != "doctor_list" else None
    is_health_guidance = bool(best.speciality) and best.kind == "kb"
    action = "book" if best.kind == "booking" else None

    text = _call_llm(message, context, history)
    mode = "llm"
    if text is None:
        mode = "retrieval"
        keep = 1 if (is_health_guidance or best.kind in ("doctor_list", "booking")) else 2
        text = " ".join(c.text for c, _ in results[:keep])
        if best.kind != "doctor_list" and len(text) > 420:
            text = text[:420].rsplit(" ", 1)[0] + "..."

    if is_health_guidance and DISCLAIMER.lower() not in text.lower():
        text = f"{text}\n\n{DISCLAIMER}"

    # the patient just told us about an emergency: say again that the clinic is not the place for it
    if best.kind == "doctor_list" and history and history[-1].get("role") == "assistant" \
            and history[-1].get("content", "").startswith("This may be an emergency"):
        text = ("Our doctors see booked patients at the clinic, but the clinic does not handle emergencies. "
                "Please go to the nearest hospital emergency department or call 112 now.\n\n" + text)

    return _reply(text, mode, sources, speciality, action)