"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

function Logo() {
  return (
    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-pine" aria-hidden="true">
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round">
        <path d="M12 5v14M5 12h14" />
      </svg>
    </span>
  );
}

export default function Header() {
  const path = usePathname();
  const link = (href, label, extra = "") => (
    <Link
      href={href}
      aria-current={path === href ? "page" : undefined}
      className={`border-b-2 py-1 transition-colors ${path === href ? "border-marigold text-pine" : "border-transparent hover:text-leaf"} ${extra}`}
    >
      {label}
    </Link>
  );

  return (
    <header className="sticky top-0 z-30 border-b border-pine/10 bg-paper/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-5">
        <Link href="/" className="flex items-center gap-2 whitespace-nowrap font-display text-[15px] font-bold text-pine sm:gap-2.5 sm:text-lg">
          <Logo />
          <span className="leading-tight">Kaveri Family Clinic</span>
        </Link>
        <nav aria-label="Main" className="flex items-center gap-3 whitespace-nowrap text-sm font-semibold sm:gap-5">
          {link("/", "Home", "hidden sm:inline-block")}
          {link("/doctors", "Our doctors")}
          <Link href="/book" className="btn btn-dark !px-4 sm:!px-5">
            <span className="sm:hidden">Book</span>
            <span className="hidden sm:inline">Book appointment</span>
          </Link>
        </nav>
      </div>
    </header>
  );
}