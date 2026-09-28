import { loadFleet } from "@/lib/fleet";
import { loadPolicy } from "@/lib/sentinel";
import { runRound, type RoundMessage } from "@/lib/trace";

export const dynamic = "force-dynamic";

const MAX_MESSAGES = 12;

// Reachable by any POST: every field is checked against the repo's own lists before it
// reaches the bus, and the bus payload is rebuilt server-side (see lib/trace.ts).
export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const input: unknown[] = Array.isArray(body?.messages) ? body.messages : [];
  if (!input.length || input.length > MAX_MESSAGES) {
    return Response.json({ error: `Send 1–${MAX_MESSAGES} messages.` }, { status: 400 });
  }
  const [fleet, policy] = await Promise.all([loadFleet(), loadPolicy()]);
  const registered = new Set(fleet.filter((a) => a.registered).map((a) => a.id));
  const kinds = new Set(["read", "write", ...policy.executionKinds]);

  const messages: RoundMessage[] = [];
  for (const raw of input as Record<string, unknown>[]) {
    const to = String(raw?.to ?? "");
    const type = raw?.type === "task.assign" ? "task.assign" : "query";
    const op = String(raw?.op ?? "");
    const budget = Number(raw?.budget ?? 100);
    const action = raw?.action as { tool?: unknown; kind?: unknown } | undefined;
    if (!registered.has(to)) return Response.json({ error: `Unknown or unregistered agent: ${to}` }, { status: 400 });
    if (!/^[a-z_]{0,32}$/.test(op)) return Response.json({ error: "Op must be a short snake_case name." }, { status: 400 });
    if (!Number.isInteger(budget) || budget < 0 || budget > 100) {
      return Response.json({ error: "Budget must be a whole number of calls, 0–100." }, { status: 400 });
    }
    let act: RoundMessage["action"];
    if (action) {
      const tool = String(action.tool ?? "");
      const kind = String(action.kind ?? "");
      if (!/^[a-z][a-z0-9_.]{0,63}$/.test(tool) || !kinds.has(kind)) {
        return Response.json({ error: "Action needs a tool like brain.write and a known kind." }, { status: 400 });
      }
      act = { tool, kind };
    }
    messages.push({ to, type, op, action: act, budget });
  }

  try {
    return Response.json(await runRound(messages));
  } catch (e) {
    return Response.json({ error: `The bus round failed: ${(e as Error).message}` }, { status: 500 });
  }
}
