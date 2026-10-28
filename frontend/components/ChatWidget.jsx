"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

const STARTERS = [
  "What are your opening hours?",
  "How do I book an appointment?",
  "Show me the doctor list",
  "How much is a consultation?",
];

const WELCOME = {
  role: "assistant",
  content:
    "Hello! I can answer questions about the clinic and suggest which type of doctor to see. I cannot give medical advice.",
};

function ChatIcon({ className = "h-5 w-5" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" />
    </svg>
  );
}

function MicIcon({ className = "h-5 w-5" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </svg>
  );
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef(null);
  const recognitionRef = useRef(null);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceError, setVoiceError] = useState("");

  // the browser's own speech recognition (Chrome, Edge, Safari). Nothing is sent anywhere except the text we recognise.
  useEffect(() => {
    setVoiceSupported(Boolean(window.SpeechRecognition || window.webkitSpeechRecognition));
    return () => recognitionRef.current?.abort();
  }, []);

  function toggleVoice() {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new Recognition();
    recognition.lang = "en-IN";
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    setVoiceError("");
    let finalText = "";
    recognition.onresult = (event) => {
      const heard = Array.from(event.results).map((r) => r[0].transcript).join(" ");
      setInput(heard);
      if (event.results[event.results.length - 1].isFinal) finalText = heard;
    };
    recognition.onerror = (event) => {
      setVoiceError(
        event.error === "not-allowed" || event.error === "service-not-allowed"
          ? "The microphone is blocked. Allow it in your browser, or type your question."
          : event.error === "no-speech"
          ? "I did not hear anything. Please try again."
          : "Voice input did not work. Please type your question."
      );
    };
    recognition.onend = () => {
      setListening(false);
      if (finalText.trim()) send(finalText);
    };
    recognitionRef.current = recognition;
    setListening(true);
    recognition.start();
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages, busy, open]);

  async function send(text) {
    const message = text.trim();
    if (!message || busy) return;
    const history = messages.filter((m) => m !== WELCOME).map(({ role, content }) => ({ role, content }));
    setMessages((m) => [...m, { role: "user", content: message }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api("/api/chat", { method: "POST", body: JSON.stringify({ message, history }) });
      setMessages((m) => [...m, { role: "assistant", content: res.answer, speciality: res.suggested_speciality, action: res.action, mode: res.mode }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: e.message, mode: "error" }]);
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-40 flex items-center gap-2.5 rounded-full bg-pine px-5 py-3.5 text-sm font-semibold text-white shadow-[0_10px_28px_-8px_rgba(13,79,89,0.6)] transition-colors hover:bg-pine-light"
        aria-label="Open the clinic assistant"
      >
        <ChatIcon />
        Ask the assistant
      </button>
    );
  }

  return (
    <section
      aria-label="Clinic assistant"
      className="fixed bottom-0 right-0 z-40 flex h-[34rem] max-h-[100dvh] w-full flex-col overflow-hidden bg-paper shadow-2xl ring-1 ring-pine/20 sm:bottom-5 sm:right-5 sm:w-[24rem] sm:rounded-2xl"
    >
      <div className="flex items-center gap-3 bg-pine px-4 py-3.5 text-white">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/15"><ChatIcon /></span>
        <div className="flex-1">
          <p className="font-display text-lg font-bold leading-tight">Clinic assistant</p>
          <p className="text-xs text-white/75">Doctors, fees, timings and booking</p>
        </div>
        <button onClick={() => setOpen(false)} className="rounded-lg p-2 hover:bg-white/15" aria-label="Close the assistant">
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
        </button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div
              className={`max-w-[88%] whitespace-pre-line px-3.5 py-2.5 text-sm leading-relaxed ${
                m.role === "user"
                  ? "rounded-2xl rounded-br-md bg-pine text-white"
                  : m.mode === "emergency"
                  ? "rounded-2xl rounded-bl-md bg-red-50 text-alert ring-1 ring-alert/40"
                  : "rounded-2xl rounded-bl-md bg-white text-ink ring-1 ring-pine/10"
              }`}
            >
              {m.content}
              {m.action === "book" && !m.speciality && (
                <Link href="/book" className="btn btn-primary mt-3 w-full">Book an appointment</Link>
              )}
              {m.speciality && (
                <Link href={`/book?speciality=${encodeURIComponent(m.speciality)}`} className="btn btn-primary mt-3 w-full">
                  Book a {m.speciality}
                </Link>
              )}
              {m.mode === "cancel_confirm" && i === messages.length - 1 && !busy && (
                <div className="mt-3 flex gap-2">
                  <button type="button" onClick={() => send("yes")} className="btn btn-dark flex-1 !min-h-[40px]">Yes, cancel it</button>
                  <button type="button" onClick={() => send("no")} className="btn btn-outline flex-1 !min-h-[40px]">No, keep it</button>
                </div>
              )}
            </div>
          </div>
        ))}

        {busy && (
          <div className="flex justify-start" role="status" aria-label="The assistant is typing">
            <div className="flex gap-1 rounded-2xl rounded-bl-md bg-white px-4 py-3.5 ring-1 ring-pine/10">
              {[0, 1, 2].map((n) => (
                <span key={n} className="h-2 w-2 animate-bounce rounded-full bg-pine/50" style={{ animationDelay: `${n * 140}ms` }} />
              ))}
            </div>
          </div>
        )}

        {messages.length === 1 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {STARTERS.map((s) => (
              <button key={s} onClick={() => send(s)} className="rounded-full border border-pine/30 bg-white px-3.5 py-2 text-left text-xs font-medium text-pine hover:bg-mist">
                {s}
              </button>
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-2 border-t border-pine/10 bg-white p-3">
        <label htmlFor="chat-input" className="sr-only">Your question</label>
        <input id="chat-input" value={input} onChange={(e) => setInput(e.target.value)} maxLength={500} placeholder={listening ? "Listening..." : "Type your question"} className="field !rounded-full !py-2.5" autoComplete="off" />
        {voiceSupported && (
          <button
            type="button"
            onClick={toggleVoice}
            aria-pressed={listening}
            aria-label={listening ? "Stop listening" : "Speak your question"}
            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full ring-1 transition-colors ${listening ? "animate-pulse bg-alert text-white ring-alert" : "bg-white text-pine ring-pine/40 hover:bg-mist"}`}
          >
            <MicIcon />
          </button>
        )}
        <button type="submit" disabled={busy || !input.trim()} className="btn btn-dark !rounded-full" aria-label="Send">
          Send
        </button>
      </form>
      {voiceError && <p role="alert" className="bg-white px-3 pb-1 text-center text-xs text-alert">{voiceError}</p>}
      <p className="bg-white px-3 pb-2 text-center text-[11px] text-ink/55">General guidance only. Not medical advice. In an emergency, call your local emergency number.</p>
    </section>
  );
}