"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { formatDate, formatTime, initials, tone } from "@/lib/format";

const TABS = {
  find: {
    label: "Find the right doctor",
    hint: "Describe the problem in your own words. We will suggest the type of doctor.",
    placeholder: "For example: my child has a fever and cough",
    examples: ["My child has a fever", "Rash on my arm", "Knee pain for a week"],
    path: "/api/suggest-doctor",
  },
  type: {
    label: "Book by typing",
    hint: "Say who you want to see and when. We will show real free times.",
    placeholder: "For example: skin doctor tomorrow morning",
    examples: ["Skin doctor tomorrow morning", "Dr Rahul on Friday at 10 am", "Bone doctor 3 pm"],
    path: "/api/parse-booking",
  },
};

export default function AssistPanel({ onPickDoctor, onPickSlot }) {
  const [tab, setTab] = useState("find");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const t = TABS[tab];

  function switchTab(next) {
    setTab(next);
    setResult(null);
    setError("");
    setText("");
  }

  async function run(value) {
    const q = (value ?? text).trim();
    if (q.length < 2 || busy) return;
    setText(q);
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(await api(t.path, { method: "POST", body: JSON.stringify({ text: q }) }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="assist-heading" className="mt-8 rounded-2xl bg-mist p-5 sm:p-6">
      <h2 id="assist-heading" className="font-display text-xl font-bold text-pine">Not sure where to start?</h2>

      <div role="tablist" aria-label="Choose a helper" className="mt-3 flex gap-2">
        {Object.entries(TABS).map(([key, value]) => (
          <button
            key={key}
            role="tab"
            type="button"
            aria-selected={tab === key}
            onClick={() => switchTab(key)}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${tab === key ? "bg-pine text-white" : "bg-white text-pine ring-1 ring-pine/25 hover:bg-white/70"}`}
          >
            {value.label}
          </button>
        ))}
      </div>

      <p className="mt-4 text-sm text-ink/75">{t.hint}</p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <label htmlFor="assist-input" className="sr-only">{t.label}</label>
        <input
          id="assist-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); run(); } }}
          maxLength={300}
          placeholder={t.placeholder}
          className="field"
          autoComplete="off"
        />
        <button type="button" onClick={() => run()} disabled={busy || text.trim().length < 2} className="btn btn-dark shrink-0">
          {busy ? "Looking..." : tab === "find" ? "Suggest a doctor" : "Show free times"}
        </button>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {t.examples.map((ex) => (
          <button key={ex} type="button" onClick={() => run(ex)} className="rounded-full bg-white px-3 py-1.5 text-xs font-medium text-pine ring-1 ring-pine/20 hover:bg-white/70">
            {ex}
          </button>
        ))}
      </div>

      <div aria-live="polite" className="mt-4">
        {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-alert">{error}</p>}

        {result?.emergency && (
          <p role="alert" className="rounded-lg bg-red-50 p-4 text-sm font-medium text-alert ring-1 ring-alert/40">{result.message}</p>
        )}

        {result && !result.emergency && tab === "find" && (
          <div className="rounded-xl bg-white p-4 ring-1 ring-pine/10">
            <p className="text-sm text-ink/65">We suggest</p>
            <p className="font-display text-xl font-bold text-pine">{result.speciality}</p>
            {result.explanation && <p className="mt-1 text-sm text-ink/80">{result.explanation}</p>}
            <ul className="mt-3 space-y-2">
              {result.doctors.map((d) => (
                <li key={d.id} className="flex flex-wrap items-center gap-3">
                  <span className={`flex h-9 w-9 items-center justify-center rounded-full font-display text-xs font-bold ${tone(d.speciality)}`} aria-hidden="true">{initials(d.name)}</span>
                  <span className="flex-1 text-sm"><span className="font-semibold">{d.name}</span><span className="block text-xs text-ink/65">{d.available_days.join(", ")}</span></span>
                  <button type="button" onClick={() => onPickDoctor(d.id)} className="btn btn-primary !min-h-[40px]">Choose {d.name.replace("Dr. ", "Dr ")}</button>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-ink/60">{result.disclaimer}</p>
          </div>
        )}

        {result && !result.emergency && tab === "type" && (
          <div className="rounded-xl bg-white p-4 ring-1 ring-pine/10">
            <p className="text-sm text-ink/80">{result.message}</p>
            {result.explanation && <p className="mt-1 text-xs text-ink/60">{result.explanation}</p>}
            {result.options.length > 0 && (
              <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                {result.options.map((o) => (
                  <li key={`${o.doctor_id}-${o.date}-${o.slot_time}`}>
                    <button
                      type="button"
                      onClick={() => onPickSlot(o)}
                      className="flex w-full items-center gap-3 rounded-xl border border-pine/20 p-3 text-left transition-colors hover:bg-mist"
                    >
                      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full font-display text-xs font-bold ${tone(o.speciality)}`} aria-hidden="true">{initials(o.name)}</span>
                      <span className="min-w-0 flex-1 text-sm"><span className="block truncate font-semibold">{o.name}</span><span className="text-xs text-ink/65">{formatDate(o.date)}</span></span>
                      <span className="font-display font-bold tabular-nums text-pine">{formatTime(o.slot_time)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </section>
  );
}