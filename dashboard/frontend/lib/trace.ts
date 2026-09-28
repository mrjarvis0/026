import { run } from "./sentinel";

// What the bus adapters answer today (bootstrap/adapters.py, orchestrator/adapters/a015.py).
// A UX list only: the op is still passed to the adapter, which rejects anything it doesn't know.
export const BUS_OPS: Record<string, { key: "op" | "intent"; values: string[] }> = {
  A001: { key: "op", values: ["detectors", "skills", "chains", "metrics", "coverage", "flows", "labels", "health"] },
  A002: { key: "op", values: ["stats", "sources", "settings"] },
  A015: { key: "intent", values: ["latest_events"] },
};

export type RoundMessage = {
  to: string;
  type: "query" | "task.assign";
  op: string;
  action?: { tool: string; kind: string };
  budget: number;
};

export type TraceEntry = { at: string; kind: string; id: string; trace_id: string; from: string; to: string; type: string; reason?: string };
export type RoundResult = {
  message: { id: string; trace_id: string; to: string; type: string; payload: Record<string, unknown>; action: RoundMessage["action"] | null; budget: { calls: number } };
  response: { ok: boolean; status: string; reason: string; payload: Record<string, unknown> };
  ms: number;
};

// The payload is built here from validated fields only — adapters read other payload keys
// (A015 reads `event_log_dir`), so client-supplied payloads must never reach the bus.
function payloadFor(m: RoundMessage) {
  const spec = BUS_OPS[m.to];
  if (!spec) return {};
  return spec.key === "intent" ? { intent: m.op, limit: 20 } : { op: m.op };
}

export async function runRound(messages: RoundMessage[]) {
  const out = await run(
    ["dashboard/backend/trace_round.py"],
    JSON.stringify({
      messages: messages.map((m) => ({
        to: m.to,
        type: m.type,
        payload: payloadFor(m),
        action: m.action ?? null,
        budget: m.budget,
      })),
    }),
    90_000,
  );
  return JSON.parse(out) as { results: RoundResult[]; trace: TraceEntry[] };
}
