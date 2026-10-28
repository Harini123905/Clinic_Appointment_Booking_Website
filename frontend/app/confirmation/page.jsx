"use client";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { formatLongDate, formatTime } from "@/lib/format";

function Confirmation() {
  const ref = useSearchParams().get("ref");
  const [booking, setBooking] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ref) return setError("No booking reference was provided.");
    api(`/api/appointments/${encodeURIComponent(ref)}`).then(setBooking).catch((e) => setError(e.message));
  }, [ref]);

  return (
    <div className="mx-auto max-w-2xl px-5 py-12">
      {error && (
        <>
          <p role="alert" className="rounded-md bg-red-50 p-3 text-alert">{error}</p>
          <Link href="/book" className="btn btn-dark mt-6">Make a new booking</Link>
        </>
      )}
      {!booking && !error && <p className="text-ink/60">Loading your booking...</p>}

      {booking && (
        <>
          <p className="no-print inline-flex items-center gap-2 rounded-full bg-[#D6EBE6] px-3.5 py-1.5 text-sm font-semibold text-pine">
            <svg viewBox="0 0 20 20" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 10.5l4 4 8-9" /></svg>
            Confirmed
          </p>
          <h1 className="mt-4 text-4xl font-bold text-pine">Your appointment is booked</h1>
          <p className="mt-3 text-ink/75">Keep your reference number. You will need it to change or cancel.</p>

          <div className="slip mt-8">
            <div className="p-6 sm:p-8">
              <p className="text-sm text-ink/65">Booking reference</p>
              <p className="mt-1 font-display text-4xl font-bold tracking-wider text-pine">{booking.reference}</p>
            </div>
            <div className="slip-perf" />
            <dl className="grid gap-5 p-6 text-sm sm:grid-cols-2 sm:p-8">
              <div><dt className="text-ink/65">Doctor</dt><dd className="mt-0.5 text-base font-semibold">{booking.doctor_name}</dd><dd className="text-ink/65">{booking.speciality}</dd></div>
              <div><dt className="text-ink/65">Patient</dt><dd className="mt-0.5 text-base font-semibold">{booking.patient_name}</dd></div>
              <div><dt className="text-ink/65">Date</dt><dd className="mt-0.5 text-base font-semibold">{formatLongDate(booking.appointment_date)}</dd></div>
              <div><dt className="text-ink/65">Time</dt><dd className="mt-0.5 text-base font-semibold">{formatTime(booking.slot_time)}</dd><dd className="text-ink/65">30 minutes</dd></div>
              {booking.reason && <div className="sm:col-span-2"><dt className="text-ink/65">Reason for visit</dt><dd className="mt-0.5 font-semibold">{booking.reason}</dd></div>}
            </dl>
          </div>

          <ul className="mt-6 list-disc space-y-1.5 pl-5 text-sm text-ink/80">
            <li>Please arrive 10 minutes early with a photo ID and any previous reports.</li>
            <li>To change or cancel, call +91 90000 12345 at least 4 hours before.</li>
          </ul>

          <div className="no-print mt-8 flex flex-wrap gap-3">
            <button onClick={() => window.print()} className="btn btn-outline">Print this page</button>
            <Link href="/" className="btn btn-dark">Back to home</Link>
          </div>
        </>
      )}
    </div>
  );
}

export default function ConfirmationPage() {
  return (
    <Suspense fallback={<p className="p-10">Loading...</p>}>
      <Confirmation />
    </Suspense>
  );
}