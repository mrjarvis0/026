import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { parse } from "yaml";
import { MATURITY, type Maturity } from "./maturity";

// Server-only: reads the fleet straight from the repo so the UI never shows hand-typed numbers.
export const ROOT = process.env.FLEET_ROOT ?? path.resolve(/*turbopackIgnore: true*/ process.cwd(), "../..");

export type Detector = { id: string; maturity: string; ceiling: number | null; note: string | null };

export type Agent = {
  id: string;
  name: string;
  domain: string;
  status: Maturity;
  registered: boolean;
  trust: number | null;
  kernelWired: boolean;
  runtimeVerified: boolean;
  execution: boolean;
  tools: string[];
  detectors: Detector[];
  version: string | null;
  role: string;
  model: { tier: string; fallback: string | null; temperature: number | null; note: string | null } | null;
  memory: { reads: string[]; writes: string[] };
  requiresApproval: string[];
  invariants: Record<string, boolean>;
  charter: string[];
  origin: string;
  source: string; // repo-relative file the facts above were read from
  spec: { meta: string; summary: string } | null; // planned agents: from their README
};

type RegistryEntry = {
  manifest: string;
  name: string;
  domain: string;
  status: Maturity;
  trust: number;
  kernel_wired?: boolean;
  runtime_verified?: boolean;
  origin?: string;
};

const plain = (s: string) => s.replace(/\*\*|`/g, "").trim();

// Planned agents have no manifest yet — only a README spec. Pull its meta line and first mission paragraph.
async function readSpec(readme: string) {
  const lines = (await readFile(path.join(ROOT, readme), "utf8").catch(() => "")).split(/\r?\n/);
  const meta = plain(lines.find((l) => /^\*\*(Layer|Series):\*\*/.test(l)) ?? "");
  const at = lines.findIndex((l) => /^##\s.*(what it|mission)/i.test(l));
  const para: string[] = [];
  for (const raw of at < 0 ? [] : lines.slice(at + 1)) {
    const l = raw.trim();
    if (l.startsWith("#") || (!l && para.length)) break;
    if (l) para.push(l);
  }
  return { meta, summary: plain(para.join(" ")) };
}

export async function loadFleet(): Promise<Agent[]> {
  const registry: Record<string, RegistryEntry> = parse(
    await readFile(path.join(ROOT, "config/agents/registry.yaml"), "utf8"),
  ).agents;
  const dirs = (await readdir(path.join(ROOT, "agents"), { withFileTypes: true }))
    .filter((d) => d.isDirectory() && /^[AT]\d+_/.test(d.name))
    .map((d) => d.name)
    .sort();

  return Promise.all(
    dirs.map(async (dir): Promise<Agent> => {
      const id = dir.split("_")[0];
      const reg = registry[id];
      if (!reg) {
        const readme = `agents/${dir}/README.md`;
        return {
          id,
          name: dir.slice(id.length + 1).replaceAll("_", " "),
          domain: "",
          status: "planned",
          registered: false,
          trust: null,
          kernelWired: false,
          runtimeVerified: false,
          execution: false,
          tools: [],
          detectors: [],
          version: null,
          role: "",
          model: null,
          memory: { reads: [], writes: [] },
          requiresApproval: [],
          invariants: {},
          charter: [],
          origin: "",
          source: readme,
          spec: await readSpec(readme),
        };
      }
      const m = parse(await readFile(path.join(ROOT, reg.manifest), "utf8"));
      return {
        id,
        name: reg.name,
        domain: reg.domain,
        status: reg.status,
        registered: true,
        trust: reg.trust,
        kernelWired: !!reg.kernel_wired,
        runtimeVerified: !!reg.runtime_verified,
        execution: !!m.invariants?.execution_enabled,
        tools: m.tools ?? [],
        detectors: (m.evidence?.detectors ?? []).map((d: Record<string, unknown>) => ({
          id: String(d.id),
          maturity: String(d.maturity),
          ceiling: typeof d.ceiling === "number" ? d.ceiling : null,
          note: typeof d.note === "string" ? d.note : null,
        })),
        version: m.version != null ? String(m.version) : null,
        role: plain(String(m.role ?? "")),
        model: m.model
          ? {
              tier: String(m.model.tier),
              fallback: m.model.fallback ?? null,
              temperature: m.model.temperature ?? null,
              note: m.model.note ?? null,
            }
          : null,
        memory: { reads: m.memory?.reads ?? [], writes: m.memory?.writes ?? [] },
        requiresApproval: m.trust?.requires_approval ?? [],
        invariants: m.invariants ?? {},
        charter: String(m.charter ?? "")
          .split(/\r?\n/)
          .map((l) => l.replace(/^\s*-\s*/, "").trim())
          .filter(Boolean),
        origin: reg.origin ?? "",
        source: reg.manifest,
        spec: null,
      };
    }),
  );
}

export function fleetStats(agents: Agent[]) {
  const registered = agents.filter((a) => a.registered);
  const detectors = registered.flatMap((a) => a.detectors);
  return {
    total: agents.length,
    registered: registered.length,
    planned: agents.length - registered.length,
    detectors: detectors.length,
    validated: detectors.filter((d) => d.maturity === "validated").length,
    kernelWired: registered.filter((a) => a.kernelWired).map((a) => a.id),
    execution: registered.filter((a) => a.execution).map((a) => a.id),
    tools: new Set(registered.flatMap((a) => a.tools)).size,
    byStatus: Object.fromEntries(
      MATURITY.map((m) => [m, agents.filter((a) => a.status === m).length]),
    ) as Record<Maturity, number>,
  };
}
