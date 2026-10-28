export default function Footer() {
  return (
    <footer className="mt-24 bg-pine text-white">
      <div className="mx-auto grid max-w-6xl gap-10 px-5 py-12 text-sm sm:grid-cols-3">
        <div>
          <p className="font-display text-xl font-bold">Kaveri Family Clinic</p>
          <p className="mt-3 text-white/75">12, Temple Road, Paramakudi</p>
          <p className="text-white/75">Parking in front of the clinic</p>
        </div>
        <div>
          <p className="font-semibold">Opening hours</p>
          <p className="mt-3 text-white/75">Monday to Saturday, 9:00 AM to 5:00 PM</p>
          <p className="text-white/75">Lunch break 1:00 PM to 2:00 PM</p>
          <p className="text-white/75">Closed on Sundays and public holidays</p>
        </div>
        <div>
          <p className="font-semibold">Reception</p>
          <p className="mt-3 text-white/75">+91 90000 12345</p>
          <p className="text-white/75">care@kavericlinic.example</p>
        </div>
      </div>
      <p className="border-t border-white/15 px-5 py-4 text-center text-xs text-white/60">
        Demo project for an assessment. The clinic, doctors and phone numbers are fictional.{" "}
        <a href="/admin" className="underline hover:text-white">Staff</a>
      </p>
    </footer>
  );
}