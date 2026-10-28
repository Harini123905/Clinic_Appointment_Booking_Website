"""Small RAG retriever: clinic knowledge base + live doctor data -> TF-IDF search."""
import re
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from database import get_conn

KB_DIR = Path(__file__).parent / "knowledge_base"
# words that appear in almost every chunk say nothing about what the patient is asking
DOMAIN_STOP_WORDS = ["clinic", "kaveri", "family"]
# patients and the knowledge base do not always use the same words, so we add the knowledge base's word
QUERY_SYNONYMS = {
    "where": "address location", "located": "address location", "directions": "address location",
    "cost": "fees", "price": "fees", "charge": "fees", "charges": "fees", "pay": "fees payment",
    "timing": "opening hours", "timings": "opening hours", "open": "opening hours", "close": "opening hours",
    "hurts": "pain", "hurt": "pain", "aching": "pain", "sore": "pain", "itchy": "itching", "pimple": "pimples",
    "pregnant": "pregnancy care", "lady": "women's health", "ladies": "women's health",
    "woman": "women's health", "girl": "women's health", "period": "periods", "babies": "baby",
    "vaccination": "vaccinations", "vaccine": "vaccinations", "vaccines": "vaccinations",
    "cancel": "cancelling", "reschedule": "changing", "call": "phone", "number": "phone",
}
# "appointment", "how can I book" ... mean: show the booking steps (unless the patient asks about something else)
BOOKING_WORDS_RE = re.compile(r"\b(book|booking|booked|appointments?|schedule|reserve|slots?|register)\b", re.I)
OTHER_TOPIC_RE = re.compile(
    r"\b(cancel\w*|change|changing|reschedul\w*|fees?|cost|price|how long|length|duration|hours|timings?|open|"
    r"vaccin\w*|bring|late|policy|ahead|advance|refund|pay\w*|address|location|phone|contact)\b", re.I)
MIN_SCORE = 0.08  # below this, we treat the question as "not in the knowledge base"

# If clinic_info.md has no "## How to book an appointment online" section, this built-in one is used instead,
# so the booking questions always work.
BOOKING_TITLE = "How to book an appointment online, make a booking, book a doctor appointment"
BOOKING_TEXT = (
    "To book online, open the Book appointment page, choose a doctor, pick a day the doctor works, "
    "pick a free time, enter the patient's name and phone number, and press Confirm appointment. "
    "You will then see a reference number that starts with CLN. You can also call reception to book."
)


@dataclass
class Chunk:
    title: str
    text: str
    speciality: str | None = None
    kind: str = "kb"  # "kb" (knowledge base), "doctor" (one doctor), "doctor_list" (all doctors)


def _load_markdown_chunks() -> list[Chunk]:
    """Split each markdown file on '##' and '###' headings (one chunk per section)."""
    chunks: list[Chunk] = []
    for path in sorted(KB_DIR.glob("*.md")):
        title, body = None, []

        def flush():
            if title and body:
                speciality = None
                lines = []
                for line in body:
                    if line.lower().startswith("speciality:"):
                        speciality = line.split(":", 1)[1].strip()  # metadata line, not answer text
                    elif line.strip():
                        lines.append(line.strip())
                if not lines:
                    return  # a heading with no text of its own (it only groups sub-sections)
                kind = "booking" if title.lower().startswith("how to book") else "kb"
                chunks.append(Chunk(title=title, text=" ".join(lines), speciality=speciality, kind=kind))

        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("### ") or line.startswith("## "):
                flush()
                title, body = line.lstrip("# ").strip(), []
            elif line.startswith("# "):
                continue
            else:
                body.append(line)
        flush()
    return chunks


def _doctor_chunks() -> list[Chunk]:
    """Doctors come from the database, so chatbot answers never go out of date."""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM doctors ORDER BY id").fetchall()
    chunks = [
        Chunk(
            title=f"{r['name']} ({r['speciality']})",
            text=(f"{r['name']} is a {r['speciality']} with {r['experience_years']} years of experience. "
                  f"{r['bio']} Available on: {r['available_days'].replace(',', ', ')}."),
            speciality=r["speciality"],
            kind="doctor",
        )
        for r in rows
    ]
    if rows:
        listing = "; ".join(f"{r['name']} ({r['speciality']}, {r['available_days'].replace(',', ', ')})" for r in rows)
        chunks.append(Chunk(
            title="Our doctors, list of doctors",
            text=f"Our doctors are: {listing}.",
            kind="doctor_list",
        ))
    return chunks


class Retriever:
    def __init__(self) -> None:
        self.chunks = _load_markdown_chunks() + _doctor_chunks()
        if not any(c.kind == "booking" for c in self.chunks):
            self.chunks.append(Chunk(title=BOOKING_TITLE, text=BOOKING_TEXT, kind="booking"))
        corpus = [f"{c.title}. {c.title}. {c.text}" for c in self.chunks]  # title counted twice = boost
        self.vectorizer = TfidfVectorizer(stop_words=list(ENGLISH_STOP_WORDS.union(DOMAIN_STOP_WORDS)), ngram_range=(1, 2), sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(corpus)

    @staticmethod
    def _expand(query: str) -> str:
        words = re.findall(r"[a-z']+", query.lower())
        return query + " " + " ".join(QUERY_SYNONYMS[w] for w in words if w in QUERY_SYNONYMS)

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        original = query
        query = self._expand(query)
        scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        ranked = sorted(zip(self.chunks, scores), key=lambda p: p[1], reverse=True)
        results = [(c, float(s)) for c, s in ranked[:k] if s >= MIN_SCORE]

        if BOOKING_WORDS_RE.search(original) and not OTHER_TOPIC_RE.search(original):
            top_is_health = bool(results) and results[0][0].kind == "kb" and results[0][0].speciality and results[0][1] >= 0.25
            if not top_is_health:
                booking = next(c for c in self.chunks if c.kind == "booking")
                return [(booking, 1.0)]
        return results


_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever