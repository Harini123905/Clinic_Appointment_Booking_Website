# Kaveri Family Clinic: AI-assisted appointment booking

A full-stack clinic booking website with a RAG chatbot assistant, built for the
AI Growth & Automation Associate assessment (healthcare domain, website development).

## What it does
- **Book appointments**: choose a doctor, a day the doctor works, and a free 30 minute slot.
  The server checks every rule again, so double bookings, past dates, lunch-hour slots and
  wrong working days are refused (the database also has a UNIQUE constraint as a safety net).
- **Live "next free appointments"** on the home page, one click opens the form pre-filled.
- **Confirmation page** with a reference number (for example `CLN-A1B2C3`).
- **Clinic assistant (RAG + LLM)** that answers questions about hours, fees, location and doctors,
  and suggests which type of doctor to see for mild concerns, then offers a "Book a ..." button.

## How the chatbot works
1. **Safety check first**: emergency words (chest pain, trouble breathing and so on) skip the AI and
   show an emergency message.
2. **Retrieve**: the question is matched against the clinic knowledge base
   (`backend/knowledge_base/clinic_info.md`) and the live doctor list from the database,
   using TF-IDF and cosine similarity (`backend/rag.py`).
3. **Generate**: the best matches are sent to the LLM (Groq, free tier) with strict rules: answer only
   from the context, never diagnose, never suggest medicines. If no API key is set, or the call fails,
   the bot still answers in retrieval-only mode.
4. Health answers always end with a "general guidance only, not medical advice" note.
5. Nothing relevant found: the bot says so and gives the reception number instead of guessing.

## Tech stack
| Part | Technology |
| --- | --- |
| Frontend | Next.js 14 (React), Tailwind CSS |
| Backend | Python, FastAPI |
| Database | SQLite |
| Retrieval | scikit-learn TF-IDF |
| LLM | Groq API (optional), `llama-3.3-70b-versatile` |

## Run it locally
**Backend** (terminal 1)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # optional: paste your GROQ_API_KEY
uvicorn main:app --reload --port 8000
```
**Frontend** (terminal 2)
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```
Open http://localhost:3000. API documentation is at http://localhost:8000/docs.

**Tests**: `cd backend && pytest -q`

## API
| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/doctors` | List doctors (optional `?speciality=`) |
| GET | `/api/doctors/{id}/slots?date=YYYY-MM-DD` | Free slots for a day |
| GET | `/api/next-available` | First free slot for each doctor |
| POST | `/api/appointments` | Create a booking |
| GET | `/api/appointments/{reference}` | Look up a booking |
| POST | `/api/chat` | Ask the assistant |

## Deploying (for a live link)
- Backend: Render or Railway. Start command `uvicorn main:app --host 0.0.0.0 --port $PORT`.
  Set `ALLOWED_ORIGINS` to your frontend URL and, optionally, `GROQ_API_KEY`.
- Frontend: Vercel. Set `NEXT_PUBLIC_API_URL` to your backend URL.
- Note: on free hosting the SQLite file may reset when the service restarts. This is fine for a demo.

## Limits (honest notes)
- The clinic, doctors and phone numbers are fictional.
- TF-IDF retrieval matches words, not meaning. For a larger knowledge base, swap in embeddings
  (for example sentence-transformers with FAISS) inside `rag.py`; the rest of the app stays the same.
- There is no login, cancellation or payment, to keep the scope focused.
