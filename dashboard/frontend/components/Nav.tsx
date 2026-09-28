import Link from "next/link";

export const PAGES = [
  { slug: "026", href: "/" },
  { slug: "narratives", href: "/narratives" },
  { slug: "agents", href: "/agents" },
  { slug: "onchain", href: "/onchain" },
  { slug: "desk", href: "/desk" },
  { slug: "brain", href: "/brain" },
  { slug: "orchestrator", href: "/orchestrator" },
  { slug: "sentinel", href: "/sentinel" },
  { slug: "trace", href: "/trace" },
];

function PageLink({ slug, href, current }: { slug: string; href: string; current: string }) {
  const active = slug === current;
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`px-2.5 py-1.5 transition-colors ${active ? "bg-white/[0.06] text-ink" : "text-soft hover:text-ink"}`}
    >
      {slug}
    </Link>
  );
}

export function Nav({ current }: { current: string }) {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-line bg-bg/60 backdrop-blur-xl">
      <nav className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:px-6">
        <Link href="/" className="font-pixel text-lg text-ink">
          026<span className="animate-pulse text-accent">_</span>
        </Link>
        <ul className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto text-[13px] whitespace-nowrap [scrollbar-width:none]">
          {PAGES.map((p) => (
            <li key={p.slug}>
              <PageLink {...p} current={current} />
            </li>
          ))}
        </ul>
        <span className="hidden items-center gap-2 text-[11px] text-soft lg:flex">
          <svg viewBox="0 0 16 16" className="size-3.5 text-good" fill="currentColor" aria-hidden>
            <path d="M8 1 2 3.5v4C2 11 4.6 14 8 15c3.4-1 6-4 6-7.5v-4L8 1Zm-1 10L4.5 8.5l1-1L7 9l3.5-3.5 1 1L7 11Z" />
          </svg>
          Execution gate: deny by default
        </span>
      </nav>
    </header>
  );
}

export function Footer({ current }: { current: string }) {
  return (
    <footer className="relative mt-16 overflow-hidden border-t border-line">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-16 sm:px-6 md:grid-cols-[1.4fr_1fr]">
        <div>
          <p className="max-w-md text-lg text-ink">
            The fleet is only as strong as its weakest agent —{" "}
            <span className="font-serif italic text-accent-hi">and its weakest claim.</span>
          </p>
          <p className="mt-4 text-sm text-mute">
            Python thinks. TypeScript shows. Postgres remembers. Redis speeds.
          </p>
        </div>
        <ul className="grid grid-cols-2 gap-1 text-[13px]">
          {PAGES.map((p) => (
            <li key={p.slug}>
              <PageLink {...p} current={current} />
            </li>
          ))}
        </ul>
      </div>
      <p
        aria-hidden
        className="pointer-events-none -mb-[0.2em] select-none text-center font-pixel text-[28vw] leading-none text-white/[0.03]"
      >
        026
      </p>
    </footer>
  );
}
