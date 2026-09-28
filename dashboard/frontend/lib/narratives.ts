import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import { ROOT } from "./fleet";
import type { VerdictId } from "./verdict";

// Server-only, read-only view of A002's own store. The dashboard never writes agent data.
const DB_FILE = path.join(ROOT, "agents/A002_News_Intelligence/data/processed/a002.db");
const SOURCES_PER_NARRATIVE = 6;

export type Source = {
  title: string;
  outlet: string;
  tier: number;
  url: string | null;
  stance: string;
  published: string | null;
};

export type Narrative = {
  id: number;
  claim: string;
  category: string;
  verdict: VerdictId;
  confidence: number;
  lifecycle: string;
  fomo: number;
  coordination: number;
  mentions: number;
  sourceCount: number;
  entities: string[];
  firstSeen: string;
  lastSeen: string;
  evidence: {
    underlying: number;
    credible: number;
    official: number;
    supports: number;
    denies: number;
    questions: number;
    socialOnly: boolean;
  };
  sources: Source[];
};

type Row = {
  id: number;
  claim_text: string;
  category: string | null;
  epistemic_status: VerdictId;
  confidence: number;
  status: string;
  fomo_score: number;
  coordination_score: number;
  mention_count: number;
  source_count: number;
  entities: string;
  first_seen: string;
  last_seen: string;
  evidence: string;
};

const when = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "UTC",
      }) + " UTC"
    : null;

export function loadNarratives() {
  const db = new DatabaseSync(DB_FILE, { readOnly: true });
  try {
    const rows = db
      .prepare(
        `select id, claim_text, category, epistemic_status, confidence, status, fomo_score,
                coordination_score, mention_count, source_count, entities, first_seen, last_seen, evidence
         from narratives order by last_seen desc`,
      )
      .all() as unknown as Row[];
    const scan = db
      .prepare("select created_at, items_fetched, items_stored from scan_stats order by id desc limit 1")
      .get() as { created_at: string; items_fetched: number; items_stored: number } | undefined;
    const items = (db.prepare("select count(*) n from items").get() as { n: number }).n;

    const narratives = rows.map((r): Narrative => {
      const ev = JSON.parse(r.evidence || "{}");
      return {
        id: r.id,
        claim: r.claim_text,
        category: r.category ?? "unclassified",
        verdict: r.epistemic_status,
        confidence: r.confidence,
        lifecycle: r.status,
        fomo: r.fomo_score,
        coordination: r.coordination_score,
        mentions: r.mention_count,
        sourceCount: r.source_count,
        entities: JSON.parse(r.entities || "[]"),
        firstSeen: when(r.first_seen)!,
        lastSeen: when(r.last_seen)!,
        evidence: {
          underlying: ev.underlying_sources ?? 0,
          credible: ev.credible_sources ?? 0,
          official: ev.official_sources ?? 0,
          supports: ev.supports ?? 0,
          denies: ev.denies ?? 0,
          questions: ev.questions ?? 0,
          socialOnly: !!ev.social_only,
        },
        sources: (ev.sources ?? []).slice(0, SOURCES_PER_NARRATIVE).map(
          (s: Record<string, unknown>): Source => ({
            title: String(s.title ?? ""),
            outlet: String(s.source ?? "").replace(/^rss_/, "").replaceAll("_", " "),
            tier: Number(s.tier ?? 6),
            url: typeof s.url === "string" && /^https?:\/\//.test(s.url) ? s.url : null,
            stance: String(s.stance ?? "neutral"),
            published: when((s.published_at as string) ?? null),
          }),
        ),
      };
    });

    const hoursSinceScan = scan
      ? (Date.now() - new Date(scan.created_at).getTime()) / 3_600_000
      : null;
    return {
      narratives,
      items,
      lastScan: scan ? { at: when(scan.created_at)!, hoursAgo: hoursSinceScan!, stored: scan.items_stored } : null,
    };
  } finally {
    db.close();
  }
}
