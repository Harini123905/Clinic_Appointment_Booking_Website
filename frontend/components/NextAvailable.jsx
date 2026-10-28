"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatDate, formatTime, initials, tone } from "@/lib/format";

export default function NextAvailable() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/next-available").then(setItems).catch((e) => setError(e.message));
  }, []);

  return (
    <section aria-labelledby="next-heading" className="slip mx-auto w-full max-w-md lg:max-w-none">
      <div className="px-6 pb-5 pt-6">
        <h2 id="next-heading" className="text-2xl font-bold text-pine">Next free appointments</h2>
        <p className="mt-1 text-sm text-ink/70">Choose a time and we will fill in the booking form for you.</p>
      </div>

      <div className="slip-perf" />

      <div className="px-3 pb-3 pt-2 sm:px-4">
        {error && <p role="alert" className="m-3 rounded-lg bg-red-50 p-3 text-sm text-alert">{error}</p>}
        {!items && !error && <p className="p-3 text-sm text-ink/60">Loading available times...</p>}

        <ul>
          {items?.map((i) => (
            <li key={i.doctor_id}>
              <Link
                href={`/book?doctor=${i.doctor_id}&date=${i.date}&time=${i.slot_time}`}
                className="flex items-center gap-3 rounded-xl px-3 py-3 transition-colors hover:bg-mist"
              >
                <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full font-display text-sm font-bold ${tone(i.speciality)}`} aria-hidden="true">
                  {initials(i.name)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold">{i.name}</span>
                  <span className="block truncate text-sm text-ink/65">{i.speciality}</span>
                </span>
                <span className="shrink-0 text-right">
                  <span className="block text-xs text-ink/60">{formatDate(i.date)}</span>
                  <span className="block font-display text-base font-bold tabular-nums text-pine">{formatTime(i.slot_time)}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}