"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const MODE_LABELS = {
  llm: "AI answers",
  retrieval: "Answered from clinic information",
  small_talk: "Greetings and thanks",
  no_match: "Could not answer",
  emergency: "Emergency warnings",
  booking: "Booking help",
  booking_status: "Booking look-ups",
  cancel_confirm: "Cancel requests",
  cancelled: "Cancelled in chat",
  need_reference: "Asked for a reference",
  booking_not_found: "Reference not found",
};

function Stat({ label, value, note }) {
  return (
    <div className="rounded-2xl bg-white p-5 ring-1 ring-pine/10">
      <p className="text-sm text-ink/65">{label}</p>
      <p className="mt-1 font-display text-4xl font-bold tabular-nums text-pine">{value}</p>
      {note && <p className="mt-1 text-xs text-ink/60">{note}</p>}
    </div>
  );
}

function Bars({ title, rows, labelOf = (l) => l, empty = "Nothing to show yet." }) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <section className="rounded-2xl bg-white p-5 ring-1 ring-pine/10">
      <h2 className="font-display text-lg font-bold text-pine">{title}</h2>
      {rows.length === 0 ? (
        <p className="mt-3 text-sm text-ink/60">{empty}</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {rows.map((r) => (
            <li key={r.label}>
              <div className="flex justify-between text-sm">
                <span>{labelOf(r.label)}</span>
                <span className="font-semibold tabular-nums">{r.count}</span>
              </div>
              <div className="mt-1 h-2.5 rounded-full bg-mist" role="presentation">
                <div className="h-2.5 rounded-full bg-pine" style={{ width: `${(r.count / max) * 100}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function AdminPage() {
  const [key, setKey] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load(k) {
    setLoading(true);
    setError("");
    try {
      const result = await api("/api/admin/insights", { headers: { "Content-Type": "application/json", "X-Admin-Key": k } });
      setData(result);
      try { sessionStorage.setItem("staff-key", k); } catch {}
    } catch (e) {
      setData(null);
      setError(e.message);
      try { sessionStorage.removeItem("staff-key"); } catch {}
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem("staff-key");
      if (saved) { setKey(saved); load(saved); }
    } catch {}
  }, []);

  if (!data) {
    return (
      <div className="mx-auto max-w-md px-5 py-16">
        <h1 className="text-3xl font-bold text-pine">Staff insights</h1>
        <p className="mt-3 text-ink/75">Enter the staff key to see bookings and the questions the assistant could not answer.</p>
        <form onSubmit={(e) => { e.preventDefault(); load(key); }} className="mt-6 space-y-4">
          <div>
            <label htmlFor="staff-key" className="mb-1 block text-sm font-medium">Staff key</label>
            <input id="staff-key" type="password" value={key} onChange={(e) => setKey(e.target.value)} className="field" autoComplete="current-password" />
          </div>
          {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-alert">{error}</p>}
          <button type="submit" disabled={!key || loading} className="btn btn-dark">{loading ? "Checking..." : "Open insights"}</button>
        </form>
      </div>
    );
  }

  const t = data.totals;
  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-4xl font-bold text-pine">Staff insights</h1>
          <p className="mt-2 text-ink/75">What patients book, and what the assistant could not answer.</p>
        </div>
        <button onClick={() => load(key)} className="btn btn-outline">Refresh</button>
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Confirmed bookings" value={t.confirmed} />
        <Stat label="Coming up" value={t.upcoming} note="From today onwards" />
        <Stat label="Cancelled" value={t.cancelled} note={`${t.cancel_rate_percent}% of all bookings`} />
        <Stat label="Chat messages" value={t.chat_messages} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Bars title="Bookings by speciality" rows={data.bookings_by_speciality} empty="No bookings yet." />
        <Bars title="Bookings by weekday" rows={data.bookings_by_weekday} />
        <Bars title="How the assistant replied" rows={data.chat_modes} labelOf={(l) => MODE_LABELS[l] || l} empty="No chat messages yet." />

        <section className="rounded-2xl bg-white p-5 ring-1 ring-pine/10">
          <h2 className="font-display text-lg font-bold text-pine">Questions it could not answer</h2>
          <p className="mt-1 text-sm text-ink/65">Add answers for these to the clinic information file so the assistant can reply next time.</p>
          {data.unanswered_questions.length === 0 ? (
            <p className="mt-3 text-sm text-ink/60">None yet. Good news.</p>
          ) : (
            <ol className="mt-4 divide-y divide-pine/10">
              {data.unanswered_questions.map((q) => (
                <li key={q.question} className="flex items-start justify-between gap-4 py-3 text-sm">
                  <span className="break-words">{q.question}</span>
                  <span className="shrink-0 rounded-full bg-mist px-2.5 py-0.5 text-xs font-semibold tabular-nums text-pine">{q.count}x</span>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}