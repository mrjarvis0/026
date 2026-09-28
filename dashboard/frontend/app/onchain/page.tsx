import type { Metadata } from "next";
import { Footer, Nav } from "@/components/Nav";
import { Addr, FlowChart, OnchainStage, TxLink, type Flow, type OnBlock } from "@/components/OnchainView";
import { Reveal } from "@/components/Reveal";
import { loadFleet } from "@/lib/fleet";
import { eth, loadA001Service, loadChainRecords } from "@/lib/onchain";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "onchain — 026" };

const fmt = (n: number, d = 2) => n.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d });
const utc = (iso: string) => iso.replace("T", " ").replace(/(\+00:00|Z)$/, " UTC");

function Head({ eyebrow, title, children }: { eyebrow: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="max-w-3xl">
      <p className="font-pixel text-[11px] uppercase tracking-[0.3em] text-accent">{eyebrow}</p>
      <h2 className="mt-3 text-3xl font-medium tracking-tight text-ink">{title}</h2>
      {children && <p className="mt-3 text-sm leading-relaxed text-soft">{children}</p>}
    </div>
  );
}

function Warn({ children }: { children: React.ReactNode }) {
  return (
    <p className="flex items-start gap-2 text-xs leading-relaxed text-soft">
      <svg viewBox="0 0 16 16" className="mt-px size-3.5 shrink-0 text-warning" fill="currentColor" aria-label="Warning">
        <path d="M8 1.5 15 14H1L8 1.5Zm-.75 5v4h1.5v-4h-1.5Zm0 5v1.5h1.5V11.5h-1.5Z" />
      </svg>
      <span>{children}</span>
    </p>
  );
}

export default async function OnchainPage() {
  const records = loadChainRecords();
  const [service, fleet] = await Promise.all([
    loadA001Service().catch((e: Error): Awaited<ReturnType<typeof loadA001Service>> => ({ _error: e.message })),
    loadFleet(),
  ]);
  const err: string | undefined = service._error;
  const cov = service.coverage?.data;
  const flowData = service.flows?.data;
  const registry: { detector: string; maturity: string; ceiling: number; may_alert: boolean; blocked_by: string }[] =
    service.health?.data?.decision?.gate?.registry ?? service.detectors?.data?.detectors ?? [];
  const chains: Record<string, any>[] = service.chains?.data?.chains ?? [];
  const manifest = fleet.find((a) => a.id === "A001");

  const blocks: OnBlock[] = records.blocks.map((b) => ({
    number: b.number,
    time: b.time,
    txs: b.txs,
    state: b.complete ? "complete" : b.reason === "selective_capture" ? "selective" : "unfetched",
    valueEth: b.valueEth,
    gasPct: b.gasUsed && b.gasLimit ? (b.gasUsed / b.gasLimit) * 100 : null,
    top: b.top,
  }));
  const first = records.blocks[0];
  const last = records.blocks[records.blocks.length - 1];

  const flows: Flow[] = Object.entries(flowData?.flow?.entities ?? {}).map(([entity, v]) => {
    const f = v as Record<string, number>;
    return {
      entity,
      inCount: f.inflow_count,
      inEth: eth(f.inflow_value),
      outCount: f.outflow_count,
      outEth: eth(f.outflow_value),
      netEth: eth(f.net_value),
    };
  });
  const totals = flowData?.flow?.totals;

  const mismatches = registry.filter((r) => {
    const m = manifest?.detectors.find((d) => d.id === r.detector);
    return !m || m.maturity !== r.maturity || (m.ceiling != null && Math.abs(m.ceiling - r.ceiling) > 1e-9);
  });

  return (
    <>
      <Nav current="onchain" />
      <main className="mx-auto max-w-7xl px-4 pt-28 pb-16 sm:px-6">
        <Reveal>
          <p className="font-pixel text-[11px] uppercase tracking-[0.3em] text-accent">A001 · Blockchain Intelligence</p>
          <h1 className="mt-4 text-5xl font-medium tracking-tight text-ink sm:text-6xl">
            Onchain. <span className="font-serif text-[1.1em] italic text-accent-hi">What the chain actually shows.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-soft">
            Everything A001 has stored and computed — read-only, straight from its own store and its own intelligence service.
            It reports deviation only: flows and transfers, never a trade idea.
          </p>
        </Reveal>

        <dl className="mt-10 grid gap-px bg-line sm:grid-cols-2 lg:grid-cols-5">
          {[
            ["Chain", "Ethereum", "a001.db — the store A001 reads"],
            ["Blocks", `${records.blocks.length}`, first && last ? `#${first.number.toLocaleString("en-US")} → #${last.number.toLocaleString("en-US")}` : "—"],
            ["Window", first && last ? `${Math.round((Date.parse(last.time) - Date.parse(first.time)) / 60000)} min` : "—", first ? utc(first.time) : "—"],
            ["Transactions", records.txTotal.toLocaleString("en-US"), `${records.tokenTotal.toLocaleString("en-US")} token · ${records.nftTotal} NFT transfers`],
            ["Labelled addresses", `${flowData?.flow?.labelled_addresses ?? "—"}`, `${flowData?.flow?.labelled_entities ?? "—"} entities · confidence ${flowData?.flow?.label_confidence ?? "—"}`],
          ].map(([k, v, note]) => (
            <div key={k} className="bg-bg p-4">
              <dt className="text-[11px] text-mute">{k}</dt>
              <dd className="mt-1 text-2xl font-semibold text-ink">{v}</dd>
              <p className="mt-1 text-[11px] text-mute">{note}</p>
            </div>
          ))}
        </dl>
        {err && (
          <div className="mt-4">
            <Warn>A001&apos;s intelligence service did not answer ({err}). Stored records below are still shown.</Warn>
          </div>
        )}

        <OnchainStage blocks={blocks} labels={records.labels} />

        {cov && (
          <section className="mt-16" aria-label="Coverage">
            <Head eyebrow="Law · coverage before absence" title="What this window can and cannot prove">
              A negative claim needs proof the window was observed. A001 measures that itself.
            </Head>
            <div className="mt-6 grid gap-px bg-line sm:grid-cols-4">
              {[
                ["Complete", cov.window.complete_blocks],
                ["Selective capture", cov.window.selective_blocks],
                ["Unfetched (logs missing)", cov.window.unfetched_blocks],
                ["Contiguous", cov.window.contiguous ? "yes" : "no"],
              ].map(([k, v]) => (
                <div key={k} className="bg-bg p-4">
                  <p className="text-[11px] text-mute">{k}</p>
                  <p className="mt-1 text-2xl font-semibold text-ink">{String(v)}</p>
                </div>
              ))}
            </div>
            <div className="mt-4">
              {cov.supports_absence ? (
                <p className="text-sm text-soft">This window can license an absence claim.</p>
              ) : (
                <Warn>
                  Cannot license &ldquo;nothing happened&rdquo;. A001 says: <span className="text-ink">{cov.limitation}</span>
                </Warn>
              )}
            </div>
          </section>
        )}

        {flowData && (
          <section className="mt-16" aria-label="Exchange flows">
            <Head eyebrow="DET-EXCHANGE-01 · exchange flows" title="Where ETH moved in and out of exchanges">
              {/* Built from A001's structured fields: its reason string counts exchange-hour rows as hours. */}
              {flowData.flow?.attributed?.toLocaleString("en-US")} of {flowData.flow?.transfers_scanned?.toLocaleString("en-US")}{" "}
              transfers attributed to {flows.length} labelled exchanges. A deposit is a transfer into a labelled exchange address
              from an unlabelled one; a withdrawal is the reverse. Flows only — no direction is read into them.
            </Head>
            <div className="frame mt-6 p-5">
              <FlowChart flows={flows} />
              {totals && (
                <p className="mt-5 border-t border-line pt-3 text-xs text-soft">
                  Window totals: {fmt(eth(totals.inflow_value), 1)} ETH deposited ({totals.inflow_count}) ·{" "}
                  {fmt(eth(totals.outflow_value), 1)} ETH withdrawn ({totals.outflow_count}) · net {fmt(eth(totals.net_value), 1)} ETH{" "}
                  {totals.direction}.
                </p>
              )}
            </div>
            <div className="mt-3">
              <Warn>
                Exchange labels come from {flowData.flow?.label_source} and are unverified (confidence{" "}
                {flowData.flow?.label_confidence}); every entity total inherits that uncertainty.
                {records.selectiveGap.blocks > 0 &&
                  ` The ${records.selectiveGap.blocks} selective blocks kept ${records.selectiveGap.kept.toLocaleString("en-US")} of ${records.selectiveGap.header.toLocaleString("en-US")} transactions (only those above the capture floor), so small flows there are missing.`}
              </Warn>
            </div>
          </section>
        )}

        <section className="mt-16" aria-label="Largest transfers">
          <Head eyebrow="Raw records" title="Largest ETH transfers in the window">
            Ranked by value from A001&apos;s transactions table — a list, not a detector alert.
          </Head>
          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="text-[11px] text-mute">
                <tr>
                  <th className="py-2 pr-4 font-normal">ETH</th>
                  <th className="py-2 pr-4 font-normal">From</th>
                  <th className="py-2 pr-4 font-normal">To</th>
                  <th className="py-2 pr-4 font-normal">Block</th>
                  <th className="py-2 font-normal">Tx</th>
                </tr>
              </thead>
              <tbody>
                {records.top.map((t) => (
                  <tr key={t.hash} className="border-t border-line">
                    <td className="py-2.5 pr-4 text-ink tabular-nums">{fmt(t.eth, 3)}</td>
                    <td className="py-2.5 pr-4 text-xs">
                      <Addr a={t.from} labels={records.labels} />
                    </td>
                    <td className="py-2.5 pr-4 text-xs">
                      <Addr a={t.to} labels={records.labels} />
                    </td>
                    <td className="py-2.5 pr-4 font-pixel text-[10px] text-soft">#{t.block.toLocaleString("en-US")}</td>
                    <td className="py-2.5">
                      <TxLink hash={t.hash} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-16" aria-label="Tokens">
          <Head eyebrow="Token transfers" title="Most active token contracts">
            Counts only: A001 has not resolved token decimals, so raw amounts cannot be compared across tokens.
          </Head>
          <div className="mt-6 grid gap-px bg-line sm:grid-cols-2 lg:grid-cols-4">
            {records.tokens.map((t) => (
              <div key={t.token} className="bg-bg p-4">
                <Addr a={t.token} labels={records.labels} />
                <p className="mt-2 text-2xl font-semibold text-ink tabular-nums">{t.n.toLocaleString("en-US")}</p>
                <p className="text-[11px] text-mute">
                  transfers · {t.senders.toLocaleString("en-US")} senders
                  {t.mints ? ` · ${t.mints} mints` : ""}
                  {t.burns ? ` · ${t.burns} burns` : ""}
                </p>
              </div>
            ))}
          </div>
        </section>

        {registry.length > 0 && (
          <section className="mt-16" aria-label="Detectors">
            <Head eyebrow="Maturity gates" title="A001's detectors — its code vs its contract" />
            {mismatches.length > 0 && (
              <div className="mt-4">
                <Warn>
                  A001&apos;s own registry and its fleet manifest (<code className="font-pixel text-[10px]">agent.yaml</code>) disagree on{" "}
                  {mismatches.length} detector{mismatches.length === 1 ? "" : "s"}. The rest of this dashboard counts the manifest. Per
                  AGENTS.md, one of them is wrong and must be reconciled explicitly.
                </Warn>
              </div>
            )}
            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-[11px] text-mute">
                  <tr>
                    <th className="py-2 pr-4 font-normal">Detector</th>
                    <th className="py-2 pr-4 font-normal">A001 code says</th>
                    <th className="py-2 pr-4 font-normal">Manifest says</th>
                    <th className="py-2 font-normal">Blocked by</th>
                  </tr>
                </thead>
                <tbody>
                  {registry.map((r) => {
                    const m = manifest?.detectors.find((d) => d.id === r.detector);
                    const off = mismatches.includes(r);
                    return (
                      <tr key={r.detector} className="border-t border-line align-top">
                        <td className="py-2.5 pr-4 font-pixel text-xs text-ink">{r.detector}</td>
                        <td className="py-2.5 pr-4 text-xs text-soft">
                          {r.maturity} · ceiling {r.ceiling.toFixed(2)} · {r.may_alert ? "may alert" : "muted"}
                        </td>
                        <td className={`py-2.5 pr-4 text-xs ${off ? "text-warning" : "text-soft"}`}>
                          {m ? `${m.maturity}${m.ceiling != null ? ` · ceiling ${m.ceiling.toFixed(2)}` : ""}` : "not declared"}
                        </td>
                        <td className="py-2.5 text-xs text-mute">{r.blocked_by || "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {chains.length > 0 && (
          <section className="mt-16" aria-label="Chains">
            <Head eyebrow="Chain registry" title={`${chains.length} chains A001 knows`}>
              Measured by A001 on {service.chains?.data?.measured_on}. Only Ethereum is in the store this page reads.
            </Head>
            <div className="mt-6 grid gap-px bg-line sm:grid-cols-2 lg:grid-cols-3">
              {chains.map((c) => (
                <details key={c.chain} className="group bg-bg p-4">
                  <summary className="cursor-pointer list-none">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-ink">{c.display_name}</span>
                      <span className={`font-pixel text-[9px] uppercase ${c.observable ? "text-accent" : "text-mute"}`}>
                        {c.observable ? "observable" : "registry only"}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-mute">
                      {c.native_currency} · {c.block_time_seconds}s blocks · {c.finality} finality
                      {c.chain_id != null ? ` · id ${c.chain_id}` : ""}
                    </p>
                  </summary>
                  {Array.isArray(c.limits) && c.limits.length > 0 && (
                    <ul className="mt-3 space-y-1.5 border-t border-line pt-3 text-[11px] leading-relaxed text-soft">
                      {c.limits.map((l: string) => (
                        <li key={l}>— {l}</li>
                      ))}
                    </ul>
                  )}
                </details>
              ))}
            </div>
          </section>
        )}
      </main>
      <Footer current="onchain" />
    </>
  );
}
