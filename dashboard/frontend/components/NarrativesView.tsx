"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { useReducedMotion } from "motion/react";
import type { Narrative } from "@/lib/narratives";
import { CATEGORY_LABEL, TIER_LABEL, VERDICT, VERDICTS, ZONES, type VerdictId } from "@/lib/verdict";

const NarrativeCity = dynamic(() => import("./NarrativeCity"), { ssr: false });

const SORTS = {
  latest: { label: "Latest", key: null },
  mentions: { label: "Most mentioned", key: "mentions" },
  fomo: { label: "Highest FOMO", key: "fomo" },
  coordination: { label: "Most coordinated", key: "coordination" },
} as const;
type SortId = keyof typeof SORTS;
const PAGE = 40;

const HATCH = "repeating-linear-gradient(45deg, #454a52 0 3px, #2a2e35 3px 6px)";
const swatch = (v: VerdictId) => (v === "disputed" ? HATCH : VERDICT[v]?.color);

function ZoneIcon({ zone }: { zone: string }) {
  const d =
    zone === "real"
      ? "M3 8.5 6.5 12 13 4.5"
      : zone === "fake"
        ? "M4 4l8 8M12 4l-8 8"
        : "M6 6a2 2 0 1 1 2.5 2c-.4.2-.5.6-.5 1v.5M8 12v.5";
  return (
    <svg viewBox="0 0 16 16" className="size-3 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
      <path d={d} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function VerdictBadge({ verdict, confidence }: { verdict: VerdictId; confidence: number }) {
  const v = VERDICT[verdict];
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] text-ink">
      <span className="size-2.5" style={{ background: swatch(verdict) }} />
      <ZoneIcon zone={v?.zone ?? "rumor"} />
      {v?.label ?? verdict}
      <span className="text-mute">· {Math.round(confidence * 100)}% confidence</span>
    </span>
  );
}

function Meter({ label, value, hint }: { label: string; value: number; hint: string }) {
  return (
    <div title={hint}>
      <div className="flex justify-between text-[11px]">
        <span className="text-mute">{label}</span>
        <span className="text-soft tabular-nums">{Math.round(value)}</span>
      </div>
      <div className="mt-1 h-1 bg-white/[0.06]">
        <div className="h-full bg-soft/60" style={{ width: `${Math.min(100, value)}%` }} />
      </div>
    </div>
  );
}

export function NarrativesView({ narratives }: { narratives: Narrative[] }) {
  const still = !!useReducedMotion();
  const [verdict, setVerdict] = useState<VerdictId | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortId>("latest");
  const [limit, setLimit] = useState(PAGE);

  const verdictCounts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const n of narratives) c[n.verdict] = (c[n.verdict] ?? 0) + 1;
    return c;
  }, [narratives]);
  const categoryCounts = useMemo(() => {
    const c = new Map<string, number>();
    for (const n of narratives) c.set(n.category, (c.get(n.category) ?? 0) + 1);
    return [...c].sort((a, b) => b[1] - a[1]);
  }, [narratives]);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = narratives.filter(
      (n) =>
        (!verdict || n.verdict === verdict) &&
        (!category || n.category === category) &&
        (!q || n.claim.toLowerCase().includes(q) || n.entities.some((e) => e.toLowerCase() === q)),
    );
    const key = SORTS[sort].key;
    return key ? [...list].sort((a, b) => b[key] - a[key]) : list;
  }, [narratives, verdict, category, query, sort]);

  const pickCategory = (c: string) => {
    setCategory((cur) => (cur === c ? null : c));
    setLimit(PAGE);
  };
  const pickVerdict = (v: VerdictId) => {
    setVerdict((cur) => (cur === v ? null : v));
    setLimit(PAGE);
  };
  const total = narratives.length;

  return (
    <>
      <div className="frame relative mt-12 h-[460px] overflow-hidden bg-panel/40">
        <NarrativeCity narratives={narratives} active={category} onPick={pickCategory} still={still} />
        <p className="pointer-events-none absolute bottom-3 left-4 max-w-sm text-[11px] leading-relaxed text-mute">
          Every cube is one narrative — stacked by topic, colored by verdict. Hover to read, click to filter.
        </p>
      </div>

      {/* Verdict scale: graded, never a binary fake/real. */}
      <section className="mt-12" aria-label="Verdict scale">
        <div className="flex items-baseline justify-between">
          <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Verdict scale</h2>
          <span className="text-[11px] text-mute">click a verdict to filter</span>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-mute">
          {ZONES.map((z) => {
            const n = VERDICTS.filter((v) => v.zone === z.id).reduce((s, v) => s + (verdictCounts[v.id] ?? 0), 0);
            return (
              <p key={z.id} className="flex items-center gap-1.5">
                <ZoneIcon zone={z.id} />
                {z.label} <span className="text-soft tabular-nums">{n}</span>
              </p>
            );
          })}
        </div>
        <div className="mt-2 flex h-3 gap-[2px]">
          {VERDICTS.filter((v) => verdictCounts[v.id]).map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => pickVerdict(v.id)}
              aria-label={`${v.label}: ${verdictCounts[v.id]}`}
              className={`h-full transition-opacity ${verdict && verdict !== v.id ? "opacity-30" : ""}`}
              style={{ flexGrow: verdictCounts[v.id], minWidth: 6, background: swatch(v.id) }}
            />
          ))}
        </div>
        <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
          {VERDICTS.map((v) => (
            <li key={v.id}>
              <button
                type="button"
                onClick={() => pickVerdict(v.id)}
                aria-pressed={verdict === v.id}
                className={`flex items-center gap-1.5 text-xs ${verdict === v.id ? "text-ink" : "text-soft hover:text-ink"}`}
              >
                <span className="size-2.5" style={{ background: swatch(v.id) }} />
                {v.label}
                <span className="text-mute tabular-nums">{verdictCounts[v.id] ?? 0}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-10" aria-label="Topics">
        <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Topics</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {categoryCounts.map(([c, n]) => (
            <button
              key={c}
              type="button"
              onClick={() => pickCategory(c)}
              aria-pressed={category === c}
              className={`border px-3 py-1.5 text-xs transition-colors ${category === c ? "border-accent bg-accent/10 text-ink" : "border-line text-soft hover:border-line-strong hover:text-ink"}`}
            >
              {CATEGORY_LABEL[c] ?? c} <span className="text-mute tabular-nums">{n}</span>
            </button>
          ))}
        </div>
      </section>

      <div className="sticky top-14 z-20 -mx-4 mt-10 flex flex-wrap items-center gap-3 border-y border-line bg-bg/80 px-4 py-3 backdrop-blur-xl sm:-mx-6 sm:px-6">
        <input
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setLimit(PAGE);
          }}
          placeholder="Search claims or a ticker (BTC)…"
          aria-label="Search narratives"
          className="min-w-0 flex-1 border border-line bg-transparent px-3 py-2 text-sm text-ink placeholder:text-mute focus:border-accent focus:outline-none"
        />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as SortId)}
          aria-label="Sort"
          className="border border-line bg-panel px-3 py-2 text-sm text-ink"
        >
          {Object.entries(SORTS).map(([id, s]) => (
            <option key={id} value={id}>
              {s.label}
            </option>
          ))}
        </select>
        <p className="text-xs text-mute" aria-live="polite">
          {shown.length} of {total}
          {(verdict || category || query) && (
            <button
              type="button"
              onClick={() => {
                setVerdict(null);
                setCategory(null);
                setQuery("");
              }}
              className="ml-3 text-accent hover:text-accent-hi"
            >
              Clear filters
            </button>
          )}
        </p>
      </div>

      <ul className="mt-6 space-y-3">
        {shown.slice(0, limit).map((n) => (
          <li key={n.id}>
            <NarrativeCard n={n} />
          </li>
        ))}
      </ul>
      {shown.length === 0 && (
        <p className="frame mt-6 p-8 text-center text-sm text-mute">
          No narrative matches these filters. Clear a filter to widen the view.
        </p>
      )}
      {shown.length > limit && (
        <button
          type="button"
          onClick={() => setLimit((l) => l + PAGE)}
          className="frame mt-4 w-full py-3 text-sm text-soft hover:text-ink"
        >
          Show {Math.min(PAGE, shown.length - limit)} more
        </button>
      )}
    </>
  );
}

function NarrativeCard({ n }: { n: Narrative }) {
  const e = n.evidence;
  return (
    <article className="frame p-5">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <VerdictBadge verdict={n.verdict} confidence={n.confidence} />
        <span className="border border-line px-2 py-0.5 text-[11px] text-soft">
          {CATEGORY_LABEL[n.category] ?? n.category}
        </span>
        <span className="font-pixel text-[9px] uppercase text-mute">{n.lifecycle.replace("_", " ")}</span>
        <span className="ml-auto text-[11px] text-mute">last seen {n.lastSeen}</span>
      </div>
      <p className="mt-3 text-[15px] leading-relaxed text-ink">{n.claim}</p>
      {n.entities.length > 0 && (
        <p className="mt-2 flex flex-wrap gap-1.5">
          {n.entities.map((s) => (
            <span key={s} className="font-pixel text-[10px] text-accent-hi">
              ${s}
            </span>
          ))}
        </p>
      )}
      <div className="mt-4 grid gap-4 sm:grid-cols-[auto_auto_1fr_1fr] sm:items-end">
        <p className="text-[11px] text-mute">
          <span className="block text-sm text-ink tabular-nums">{n.mentions}</span>mentions
        </p>
        <p className="text-[11px] text-mute">
          <span className="block text-sm text-ink tabular-nums">{e.underlying}</span>independent sources
        </p>
        <Meter label="FOMO · hype, not truth" value={n.fomo} hint="How fast and loud it spreads (0–100). Separate from the verdict." />
        <Meter
          label="Coordination · manipulation signal"
          value={n.coordination}
          hint="Identical text, timing bursts, author concentration (0–100). Separate from the verdict."
        />
      </div>
      <details className="group mt-4 border-t border-line pt-3">
        <summary className="cursor-pointer list-none text-xs text-accent hover:text-accent-hi">
          <span className="group-open:hidden">Why this verdict?</span>
          <span className="hidden group-open:inline">Hide evidence</span>
        </summary>
        <p className="mt-3 text-xs leading-relaxed text-soft">
          {e.underlying} independent source{e.underlying === 1 ? "" : "s"} after dedup · {e.credible} credible ·{" "}
          {e.official} official · stances: {e.supports} support, {e.denies} deny, {e.questions} question
          {e.socialOnly && " · social-only (no established outlet)"}. First seen {n.firstSeen}.
        </p>
        <ul className="mt-3 space-y-2">
          {n.sources.map((s, i) => (
            <li key={i} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs">
              <span className="font-pixel text-[9px] text-mute" title={TIER_LABEL[s.tier]}>
                T{s.tier}
              </span>
              <span className="text-soft capitalize">{s.outlet}</span>
              {s.url ? (
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="min-w-0 flex-1 text-ink hover:text-accent-hi">
                  {s.title}
                </a>
              ) : (
                <span className="min-w-0 flex-1 text-ink">{s.title}</span>
              )}
              {s.stance !== "neutral" && <span className="text-mute">{s.stance}</span>}
            </li>
          ))}
        </ul>
      </details>
    </article>
  );
}
