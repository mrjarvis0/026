import { loadFleet } from "@/lib/fleet";
import { askGate, loadPolicy } from "@/lib/sentinel";

export const dynamic = "force-dynamic";

// Route handlers are reachable by any POST, so every input is checked against the repo's own lists.
export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const agentId = typeof body?.agent === "string" ? body.agent : "";
  const tool = typeof body?.tool === "string" ? body.tool : "";
  const kind = typeof body?.kind === "string" ? body.kind : "";

  const [fleet, policy] = await Promise.all([loadFleet(), loadPolicy()]);
  const agent = fleet.find((a) => a.id === agentId && a.registered);
  if (!agent) return Response.json({ error: "Unknown or unregistered agent." }, { status: 400 });
  if (!/^[a-z][a-z0-9_.]{0,63}$/.test(tool)) return Response.json({ error: "Tool name must look like brain.write." }, { status: 400 });
  if (!["read", "write", ...policy.executionKinds].includes(kind)) {
    return Response.json({ error: "Unknown action kind." }, { status: 400 });
  }

  try {
    return Response.json(await askGate(agent.source, { tool, kind }));
  } catch (e) {
    return Response.json({ error: `Gate call failed: ${(e as Error).message}` }, { status: 500 });
  }
}
