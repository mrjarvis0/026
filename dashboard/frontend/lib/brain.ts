import { readFile, readdir, stat } from "node:fs/promises";
import path from "node:path";
import { ROOT, type Agent } from "./fleet";
import { run } from "./sentinel";

// Server-only view of the shared brain (AGENTS.md §7): the memory contract every manifest
// declares, plus the brain's real build state.

export const NAMESPACE_RE = /^([a-z][a-z0-9_]{0,31}|(projects|private)\/[A-Za-z0-9_.-]{1,48})$/;

export type Space = { ns: string; readers: string[]; writers: string[] };

// Manifests write `projects.*`; the store's namespace for it is `projects/<id>`.
const label = (declared: string) => declared.replace(/\.\*$/, "/*");

export function brainMap(fleet: Agent[]) {
  const agents = fleet
    .filter((a) => a.registered)
    .map((a) => ({ id: a.id, name: a.name, reads: a.memory.reads.map(label), writes: a.memory.writes.map(label) }));
  const spaces = new Map<string, Space>();
  const at = (ns: string) => spaces.get(ns) ?? spaces.set(ns, { ns, readers: [], writers: [] }).get(ns)!;
  for (const a of agents) {
    a.reads.forEach((ns) => at(ns).readers.push(a.id));
    a.writes.forEach((ns) => at(ns).writers.push(a.id));
  }
  return { agents, spaces: [...spaces.values()].sort((x, y) => y.readers.length - x.readers.length) };
}

// Is anything running the brain against a real file? A persistent store is `Brain(<path>)`;
// `Brain()` is the in-memory default used by tests and by this dashboard's throwaway checks.
export async function brainStatus() {
  const dirs = ["orchestrator", "bootstrap", "security", "brain", "dashboard/backend"];
  const hits: string[] = [];
  for (const dir of dirs) {
    const stack = [path.join(/*turbopackIgnore: true*/ ROOT, dir)];
    while (stack.length) {
      const d = stack.pop()!;
      for (const e of await readdir(d, { withFileTypes: true }).catch(() => [])) {
        const p = path.join(d, e.name);
        if (e.isDirectory()) {
          if (e.name !== "tests" && e.name !== "__pycache__") stack.push(p);
        } else if (e.name.endsWith(".py") && /\bBrain\(\s*[^)\s]/.test(await readFile(p, "utf8"))) {
          hits.push(path.relative(ROOT, p).replaceAll("\\", "/"));
        }
      }
    }
  }
  const prompt = await stat(path.join(ROOT, "brain/prompts/system.md")).catch(() => null);
  return { persistentCallers: hits, systemPromptBytes: prompt?.size ?? null };
}

export async function checkAccess(agent: Agent, op: "read" | "write", namespace: string) {
  const out = await run(
    ["dashboard/backend/brain_check.py"],
    JSON.stringify({ agent: agent.id, manifest: path.join(ROOT, agent.source), op, namespace }),
    20_000,
  );
  return JSON.parse(out);
}
