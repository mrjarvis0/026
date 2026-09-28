import { NAMESPACE_RE, checkAccess } from "@/lib/brain";
import { loadFleet } from "@/lib/fleet";

export const dynamic = "force-dynamic";

// Reachable by any POST: the agent must be registered (its manifest path comes from the
// registry, never the client) and the namespace must match the brain's own naming rule.
export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const agentId = typeof body?.agent === "string" ? body.agent : "";
  const op = body?.op === "write" ? "write" : body?.op === "read" ? "read" : null;
  const namespace = typeof body?.namespace === "string" ? body.namespace : "";

  const agent = (await loadFleet()).find((a) => a.id === agentId && a.registered);
  if (!agent) return Response.json({ error: "Unknown or unregistered agent." }, { status: 400 });
  if (!op) return Response.json({ error: "Op must be read or write." }, { status: 400 });
  if (!NAMESPACE_RE.test(namespace)) {
    return Response.json({ error: "Namespace must look like news, projects/<id> or private/<agent>." }, { status: 400 });
  }
  try {
    return Response.json(await checkAccess(agent, op, namespace));
  } catch (e) {
    return Response.json({ error: `Brain check failed: ${(e as Error).message}` }, { status: 500 });
  }
}
