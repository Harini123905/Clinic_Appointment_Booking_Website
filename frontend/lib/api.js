export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Small fetch wrapper that turns API errors into readable messages. */
export async function api(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      ...options,
    });
  } catch {
    throw new Error("We could not reach the clinic server. Please check your connection and try again.");
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg.replace(/^Value error, /, "")).join(" ")
      : detail || "Something went wrong. Please try again.";
    throw new Error(message);
  }
  return data;
}
