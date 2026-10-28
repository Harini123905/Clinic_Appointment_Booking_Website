"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import AssistPanel from "@/components/AssistPanel";
import { formatDate, formatTime, initials, tone, upcomingDates } from "@/lib/format";

function StepTitle({ n, done, children }) {
  return (
    <legend className="flex items-center gap-3 font-display text-xl font-bold text-pine">
      <span
        className={`flex h-8 w-8 items-center justify-center rounded-full text-sm ${done ? "bg-pine text-white" : "bg-mist text-pine ring-1 ring-pine/30"}`}
        aria-hidden="true"
      >
        {done ? "\u2713" : n}
      </span>
      {children}
    </legend>
  );
}

function BookingForm() {
  const router = useRouter();
  const params = useSearchParams();

  const [doctors, setDoctors] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [doctorId, setDoctorId] = useState(null);
  const [date, setDate] = useState("");
  const [slots, setSlots] = useState(null);
  const [time, setTime] = useState("");
  const [form, setForm] = useState({ patient_name: "", phone: "", reason: "" });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Load doctors, then apply any choices passed in the link (?doctor=, ?speciality=, ?date=, ?time=)
  useEffect(() => {
    api("/api/doctors")
      .then((list) => {
        setDoctors(list);
        const bySpeciality = list.find((d) => d.speciality === params.get("speciality"));
        const byId = list.find((d) => String(d.id) === params.get("doctor"));
        const chosen = byId || bySpeciality;
        if (chosen) {
          setDoctorId(chosen.id);
          if (params.get("date")) setDate(params.get("date"));
          if (params.get("time")) setTime(params.get("time"));
        }
      })
      .catch((e) => setLoadError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const doctor = doctors?.find((d) => d.id === doctorId);
  const dates = useMemo(() => (doctor ? upcomingDates(doctor.available_days) : []), [doctor]);

  // Whenever doctor or date changes, load the free slots
  useEffect(() => {
    if (!doctorId || !date) return setSlots(null);
    let cancelled = false;
    setSlots(null);
    api(`/api/doctors/${doctorId}/slots?date=${date}`)
      .then((res) => {
        if (cancelled) return;
        setSlots(res.slots);
        setTime((t) => (res.slots.includes(t) ? t : ""));
      })
      .catch((e) => !cancelled && setError(e.message));
    return () => { cancelled = true; };
  }, [doctorId, date]);

  function chooseDoctor(id) {
    setDoctorId(id);
    setDate("");
    setTime("");
    setSlots(null);
    setError("");
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const booking = await api("/api/appointments", {
        method: "POST",
        body: JSON.stringify({
          doctor_id: doctorId,
          appointment_date: date,
          slot_time: time,
          patient_name: form.patient_name,
          phone: form.phone,
          reason: form.reason || null,
        }),
      });
      router.push(`/confirmation?ref=${booking.reference}`);
    } catch (err) {
      setError(err.message);
      // if the slot was taken, refresh the list so the patient can choose again
      api(`/api/doctors/${doctorId}/slots?date=${date}`).then((r) => { setSlots(r.slots); setTime(""); }).catch(() => {});
      setSubmitting(false);
    }
  }

  // the AI helpers fill in the form for the patient
  function pickSuggestedDoctor(id) {
    chooseDoctor(id);
    setTimeout(() => document.getElementById("pick-day")?.scrollIntoView({ behavior: "smooth", block: "start" }), 150);
  }

  function pickSuggestedSlot(o) {
    setError("");
    setDoctorId(o.doctor_id);
    setDate(o.date);
    setTime(o.slot_time);
    setTimeout(() => document.getElementById("your-details")?.scrollIntoView({ behavior: "smooth", block: "start" }), 400);
  }

  const ready = doctorId && date && time && form.patient_name.trim().length >= 2 && form.phone.trim();

  return (
    <div className="mx-auto max-w-3xl px-5 py-12">
      <h1 className="text-4xl font-bold text-pine">Book an appointment</h1>
      <p className="mt-3 text-ink/75">Appointments last 30 minutes. Fee is paid at the clinic.</p>

      {loadError && <p role="alert" className="mt-6 rounded-md bg-red-50 p-3 text-alert">{loadError}</p>}
      {!doctors && !loadError && <p className="mt-6 text-ink/60">Loading doctors...</p>}

      {doctors && (
        <>
        <AssistPanel onPickDoctor={pickSuggestedDoctor} onPickSlot={pickSuggestedSlot} />
        <form onSubmit={submit} className="mt-8 space-y-10">
          <fieldset>
            <StepTitle n={1} done={!!doctor}>Choose a doctor</StepTitle>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {doctors.map((d) => (
                <label key={d.id} className={`flex cursor-pointer items-center gap-3 rounded-xl border p-4 transition-colors ${doctorId === d.id ? "border-pine bg-mist ring-2 ring-pine" : "border-pine/20 bg-white hover:bg-mist/60"}`}>
                  <input type="radio" name="doctor" value={d.id} checked={doctorId === d.id} onChange={() => chooseDoctor(d.id)} className="sr-only" />
                  <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full font-display text-sm font-bold ${tone(d.speciality)}`} aria-hidden="true">{initials(d.name)}</span>
                  <span>
                    <span className="block font-semibold">{d.name}</span>
                    <span className="block text-sm text-ink/70">{d.speciality}</span>
                    <span className="mt-0.5 block text-xs font-medium text-leaf">{d.available_days.join(", ")}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          {doctor && (
            <fieldset id="pick-day" className="scroll-mt-24">
              <StepTitle n={2} done={!!date}>Pick a day</StepTitle>
              <div className="mt-4 flex flex-wrap gap-2">
                {dates.map((d) => (
                  <label key={d} className={`cursor-pointer rounded-md border px-3 py-2 text-sm font-medium ${date === d ? "border-pine bg-pine text-white" : "border-pine/25 bg-white hover:bg-mist"}`}>
                    <input type="radio" name="date" value={d} checked={date === d} onChange={() => { setDate(d); setTime(""); setError(""); }} className="sr-only" />
                    {formatDate(d)}
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          {doctor && date && (
            <fieldset>
              <StepTitle n={3} done={!!time}>Pick a time</StepTitle>
              {!slots && <p className="mt-4 text-sm text-ink/60">Checking free times...</p>}
              {slots?.length === 0 && <p className="mt-4 text-sm text-ink/75">No free times on this day. Please choose another day.</p>}
              <div className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-5">
                {slots?.map((s) => (
                  <label key={s} className={`cursor-pointer rounded-md border px-2 py-2 text-center text-sm font-medium ${time === s ? "border-marigold bg-marigold text-ink" : "border-pine/25 bg-white hover:bg-mist"}`}>
                    <input type="radio" name="time" value={s} checked={time === s} onChange={() => setTime(s)} className="sr-only" />
                    {formatTime(s)}
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          {doctor && date && time && (
            <fieldset id="your-details" className="scroll-mt-24 space-y-4">
              <StepTitle n={4} done={!!ready}>Your details</StepTitle>
              <div>
                <label htmlFor="name" className="mb-1 block text-sm font-medium">Patient's full name</label>
                <input id="name" required minLength={2} maxLength={80} className="field" value={form.patient_name} onChange={(e) => setForm({ ...form, patient_name: e.target.value })} autoComplete="name" />
              </div>
              <div>
                <label htmlFor="phone" className="mb-1 block text-sm font-medium">Phone number</label>
                <input id="phone" type="tel" required className="field" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} autoComplete="tel" placeholder="+91 90000 12345" />
              </div>
              <div>
                <label htmlFor="reason" className="mb-1 block text-sm font-medium">Reason for visit (optional)</label>
                <textarea id="reason" rows={3} maxLength={300} className="field" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
              </div>
              <p className="rounded-md bg-mist p-3 text-sm">
                Booking <strong>{doctor.name}</strong> on <strong>{formatDate(date)}</strong> at <strong>{formatTime(time)}</strong>.
              </p>
            </fieldset>
          )}

          {error && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-alert">{error}</p>}

          <button type="submit" disabled={!ready || submitting} className="btn btn-primary">
            {submitting ? "Booking..." : "Confirm appointment"}
          </button>
        </form>
        </>
      )}
    </div>
  );
}

export default function BookPage() {
  return (
    <Suspense fallback={<p className="p-10">Loading...</p>}>
      <BookingForm />
    </Suspense>
  );
}