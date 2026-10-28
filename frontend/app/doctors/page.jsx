"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ALL_DAYS, initials, tone } from "@/lib/format";

export default function DoctorsPage() {
  const [doctors, setDoctors] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/doctors").then(setDoctors).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <h1 className="text-4xl font-bold text-pine">Our doctors</h1>
      <p className="mt-3 max-w-prose text-ink/75">Each doctor works on set days. Filled days are open for booking.</p>

      {error && <p role="alert" className="mt-6 rounded-lg bg-red-50 p-3 text-alert">{error}</p>}
      {!doctors && !error && <p className="mt-6 text-ink/60">Loading doctors...</p>}

      <ul className="mt-10 grid gap-5 md:grid-cols-2">
        {doctors?.map((d) => (
          <li key={d.id} className="flex flex-col rounded-2xl bg-white p-6 ring-1 ring-pine/10">
            <div className="flex items-center gap-4">
              <span className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl font-display text-xl font-bold ${tone(d.speciality)}`} aria-hidden="true">
                {initials(d.name)}
              </span>
              <div>
                <h2 className="text-xl font-bold">{d.name}</h2>
                <p className="mt-0.5 text-sm font-semibold text-leaf">{d.speciality}</p>
                <p className="text-sm text-ink/65">{d.experience_years} years of experience</p>
              </div>
            </div>
            <p className="mt-5 text-sm leading-relaxed text-ink/80">{d.bio}</p>

            <ul className="mt-5 grid grid-cols-6 gap-1.5" aria-label={`${d.name} is available on ${d.available_days.join(", ")}`}>
              {ALL_DAYS.map((day) => {
                const on = d.available_days.includes(day);
                return (
                  <li
                    key={day}
                    className={`rounded-lg py-1.5 text-center text-xs font-semibold ${on ? "bg-pine text-white" : "bg-mist/70 text-ink/35"}`}
                  >
                    {day}
                  </li>
                );
              })}
            </ul>

            <Link href={`/book?doctor=${d.id}`} className="btn btn-primary mt-6 self-start">
              Book with {d.name.replace("Dr. ", "Dr ")}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}