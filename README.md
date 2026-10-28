# Clinic Appointment Booking Website with AI Chatbot

A clinic website where patients can view doctors and book appointments, with an AI chatbot that answers clinic questions.

## How to run

### 1. Backend (FastAPI)
```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000
```
The backend runs at http://localhost:8000

Optional: add your Groq API key in `backend/.env` (`GROQ_API_KEY=...`). Without a key, the chatbot still works in retrieval-only mode.

### 2. Frontend (Next.js)
Open a second terminal:
```
cd frontend
npm install
npm run dev
```
The website runs at http://localhost:3000

## Links
- Demo video: https://drive.google.com/file/d/1Mzg319KHfnT0PLdgWj6GMK5fGakLgcK8/view?usp=drive_link
- Prompt document: [Prompt_Document_Clinic_Appointment_Website.pdf]
