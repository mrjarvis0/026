import { statSync } from "node:fs";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import { ROOT } from "./fleet";
import { run } from "./sentinel";

// Server-only, read-only view of A001: its own IntelligenceService (via the bus adapter)
// for computed facts, and its SQLite store for the raw chain records.

const DB_FILE = path.join(ROOT, "agents/A001_Blockchain_Intelligence/data/a001.db");
const WEI = 10n ** 18n;
const CACHE_MS = 60_000;

// Exact wei -> ETH as a number for display (BigInt keeps the integer part exact).
export const eth = (wei: string | bigint | number) => {
  const w = BigInt(typeof wei === "number" ? Math.round(wei) : wei);
  const neg = w < 0n;
  const a = neg ? -w : w;
  const v = Number(a / WEI) + Number(a % WEI) / 1e18;
  return neg ? -v : v;
};

// The shape is A001's own; fields are read defensively in the page.
type Snapshot = Record<string, any>;
let cache: { at: number; data: Snapshot } | null = null;
let inFlight: Promise<Snapshot> | null = null;

export function loadA001Service() {
  if (cache && Date.now() - cache.at < CACHE_MS) return Promise.resolve(cache.data);
  inFlight ??= run(["dashboard/backend/onchain_snapshot.py"], undefined, 60_000)
    .then((out) => {
      const data = JSON.parse(out);
      cache = { at: Date.now(), data };
      return data;
    })
    .finally(() => {
      inFlight = null;
    });
  return inFlight;
}

export type Tx = { hash: string; block: number; from: string; to: string | null; eth: number };
export type Block = {
  number: number;
  time: string;
  txs: number;
  complete: boolean;
  reason: string;
  gasUsed: number | null;
  gasLimit: number | null;
  valueEth: number;
  top: Tx[];
};

// The store only changes when A001 ingests, so reuse the scan until the file's mtime moves.
let records: { mtime: number; data: ReturnType<typeof readChainRecords> } | null = null;

export function loadChainRecords() {
  const mtime = statSync(DB_FILE).mtimeMs;
  if (records?.mtime !== mtime) records = { mtime, data: readChainRecords() };
  return records.data;
}

function readChainRecords() {
  const db = new DatabaseSync(DB_FILE, { readOnly: true });
  try {
    const blocks = db
      .prepare(
        `select number, timestamp, tx_count, complete, incomplete_reason, gas_used, gas_limit
         from blocks where chain = 'ethereum' and canonical = 1 order by number`,
      )
      .all() as { number: number; timestamp: string; tx_count: number; complete: number; incomplete_reason: string; gas_used: number | null; gas_limit: number | null }[];

    const txRows = db
      .prepare(`select tx_hash, block_number, from_address, to_address, value from transactions where chain = 'ethereum'`)
      .all() as { tx_hash: string; block_number: number; from_address: string; to_address: string | null; value: string }[];

    // Sum and rank in BigInt: values are 78-digit decimals that overflow doubles.
    const perBlock = new Map<number, { sum: bigint; txs: (Tx & { wei: bigint })[] }>();
    const all: (Tx & { wei: bigint })[] = [];
    for (const r of txRows) {
      const wei = BigInt(r.value);
      const tx = { hash: r.tx_hash, block: r.block_number, from: r.from_address, to: r.to_address, eth: eth(wei), wei };
      all.push(tx);
      const b = perBlock.get(r.block_number) ?? { sum: 0n, txs: [] };
      b.sum += wei;
      b.txs.push(tx);
      perBlock.set(r.block_number, b);
    }
    const byValue = (a: { wei: bigint }, b: { wei: bigint }) => (b.wei > a.wei ? 1 : b.wei < a.wei ? -1 : 0);
    const strip = ({ wei, ...t }: Tx & { wei: bigint }): Tx => (void wei, t);

    const tokens = db
      .prepare(
        `select token, count(*) n, count(distinct from_address) senders, sum(is_mint) mints, sum(is_burn) burns
         from token_transfers where chain = 'ethereum' group by token order by n desc limit 12`,
      )
      .all() as { token: string; n: number; senders: number; mints: number; burns: number }[];
    const tokenTotal = (db.prepare("select count(*) n from token_transfers").get() as { n: number }).n;
    const nftTotal = (db.prepare("select count(*) n from nft_transfers").get() as { n: number }).n;

    const top = all.sort(byValue).slice(0, 20).map(strip);
    const addresses = [...new Set(top.flatMap((t) => [t.from, t.to]).filter(Boolean) as string[])];
    const labelRows = addresses.length
      ? (db
          .prepare(`select address, label, entity from labels where address in (${addresses.map(() => "?").join(",")})`)
          .all(...addresses) as { address: string; label: string; entity: string }[])
      : [];

    // Selective blocks keep only transactions above a floor: count what the header says vs what was kept.
    const selective = blocks.filter((b) => !b.complete && b.incomplete_reason === "selective_capture");
    const selectiveHeader = selective.reduce((s, b) => s + b.tx_count, 0);
    const selectiveKept = selective.reduce((s, b) => s + (perBlock.get(b.number)?.txs.length ?? 0), 0);

    return {
      selectiveGap: { blocks: selective.length, header: selectiveHeader, kept: selectiveKept },
      blocks: blocks.map(
        (b): Block => ({
          number: b.number,
          time: b.timestamp,
          txs: b.tx_count,
          complete: !!b.complete,
          reason: b.incomplete_reason,
          gasUsed: b.gas_used,
          gasLimit: b.gas_limit,
          valueEth: eth(perBlock.get(b.number)?.sum ?? 0n),
          top: (perBlock.get(b.number)?.txs ?? []).sort(byValue).slice(0, 5).map(strip),
        }),
      ),
      top,
      labels: Object.fromEntries(labelRows.map((l) => [l.address, l.entity || l.label])),
      tokens,
      tokenTotal,
      nftTotal,
      txTotal: txRows.length,
    };
  } finally {
    db.close();
  }
}
