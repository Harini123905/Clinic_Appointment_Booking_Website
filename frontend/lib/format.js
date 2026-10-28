const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export const ALL_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function toISO(d) {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

export function parseISO(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function formatDate(iso) {
  const d = parseISO(iso);
  return `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

export function formatLongDate(iso) {
  const d = parseISO(iso);
  return `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

export function formatTime(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  const suffix = h >= 12 ? "PM" : "AM";
  return `${h % 12 || 12}:${String(m).padStart(2, "0")} ${suffix}`;
}

/** Upcoming dates (within `span` days) on which the doctor works. */
export function upcomingDates(availableDays, span = 30, limit = 12) {
  const out = [];
  const today = new Date();
  for (let i = 0; i <= span && out.length < limit; i++) {
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() + i);
    if (availableDays.includes(DAYS[d.getDay()])) out.push(toISO(d));
  }
  return out;
}

export function initials(name) {
  return name.replace("Dr. ", "").split(" ").map((p) => p[0]).slice(0, 2).join("");
}

/** One colour per speciality, used the same way on every page so patients learn it. */
const TONES = {
  "General Physician": "bg-[#D6EBE6] text-[#0D4F59]",
  "Paediatrician": "bg-[#FBE7C2] text-[#7A4B05]",
  "Dermatologist": "bg-[#F8DAD2] text-[#8A3524]",
  "Orthopaedic Specialist": "bg-[#DAE3F5] text-[#2B3F7A]",
  "Gynaecologist": "bg-[#E9DAEF] text-[#5E2F73]",
};

export function tone(speciality) {
  return TONES[speciality] || "bg-mist text-pine";
}