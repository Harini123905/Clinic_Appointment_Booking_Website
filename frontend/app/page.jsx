import Link from "next/link";
import NextAvailable from "@/components/NextAvailable";

const FACTS = [
  ["Open", "Mon to Sat, 9 AM to 5 PM"],
  ["Visit length", "30 minutes"],
  ["Fee", "Paid at the clinic"],
];

const SERVICES = [
  ["General medicine", "Fevers, infections, blood pressure and sugar check-ups.", "General Physician"],
  ["Child health", "Vaccinations, growth checks and common childhood illness.", "Paediatrician"],
  ["Skin and hair", "Rashes, acne, eczema and hair fall.", "Dermatologist"],
  ["Bones and joints", "Back, neck and knee pain, sprains and sports injuries.", "Orthopaedic Specialist"],
  ["Women's health", "Check-ups, period problems and pregnancy care.", "Gynaecologist"],
];

const STEPS = [
  ["Choose a doctor", "Pick the doctor you need, or ask the assistant which type to see."],
  ["Pick a day and time", "You only see times that are really free."],
  ["Get your reference", "Keep your CLN reference number and arrive 10 minutes early."],
];

export default function Home() {
  return (
    <>
      <section className="mx-auto grid max-w-6xl gap-12 px-5 py-12 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:py-20">
        <div>
          <h1 className="text-4xl font-bold leading-[1.08] text-pine sm:text-5xl lg:text-[3.4rem]">
            See the right doctor this week, without waiting on the phone.
          </h1>
          <p className="mt-5 max-w-[34rem] text-lg leading-relaxed text-ink/80">
            Book a 30 minute appointment in under a minute. Not sure which doctor you need? Ask the assistant and it will point you to the right one.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/book" className="btn btn-primary px-6">Book an appointment</Link>
            <Link href="/doctors" className="btn btn-outline px-6">Meet our doctors</Link>
          </div>
          <dl className="mt-10 grid max-w-[34rem] grid-cols-1 gap-x-6 gap-y-3 border-t border-pine/15 pt-6 text-sm sm:grid-cols-3">
            {FACTS.map(([label, value]) => (
              <div key={label}>
                <dt className="text-ink/60">{label}</dt>
                <dd className="mt-0.5 font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <NextAvailable />
      </section>

      <section className="bg-mist py-16">
        <div className="mx-auto max-w-6xl px-5">
          <h2 className="text-3xl font-bold text-pine">What we help with</h2>
          <p className="mt-2 text-ink/75">Choose a topic to book with the matching doctor.</p>
          <ul className="mt-8 divide-y divide-pine/15 border-y border-pine/15">
            {SERVICES.map(([title, text, speciality]) => (
              <li key={title}>
                <Link
                  href={`/book?speciality=${encodeURIComponent(speciality)}`}
                  className="group flex items-center justify-between gap-4 py-5 transition-colors hover:bg-white/60 sm:px-3"
                >
                  <span>
                    <span className="block font-display text-xl font-semibold">{title}</span>
                    <span className="mt-1 block text-sm text-ink/70">{text}</span>
                  </span>
                  <span className="shrink-0 rounded-lg border-2 border-pine/70 px-3.5 py-1.5 text-sm font-semibold text-pine group-hover:bg-pine group-hover:text-white">
                    Book
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 pt-16">
        <h2 className="text-3xl font-bold text-pine">How booking works</h2>
        <ol className="mt-8 grid gap-8 md:grid-cols-3">
          {STEPS.map(([title, text], i) => (
            <li key={title} className="flex gap-4">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-marigold font-display text-lg font-bold text-ink" aria-hidden="true">{i + 1}</span>
              <div>
                <h3 className="text-lg font-semibold">{title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-ink/75">{text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}