import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { parse } from "yaml";
import { ROOT } from "./fleet";

// Server-only bridge to security/sentinel. Everything here is read-only: it runs the
// sentinel's own scan CLI and its own gate function; it never changes policy or state.

export type Verdict = "PASS" | "HOLD" | "FAIL";
export type Check = { check: string; verdict: Verdict; summary: string; evidence: string[]; scanned: number };
export type AgentScan = { id: string; dir: string; effective_trust: number; verdict: Verdict; checks: Check[] };
export type ScanReport = {
  generated_at: string;
  sentinel_version: string;
  policy_version: number;
  verdict: Verdict;
  agents: AgentScan[];
  durationMs: number;
};

const PYTHON = process.env.PYTHON ?? "python";

export function run(args: string[], stdin?: string, timeout = 120_000): Promise<string> {
  return new Promise((resolve, reject) => {
    const opts = { cwd: ROOT, timeout, maxBuffer: 16 * 1024 * 1024, env: { ...process.env, PYTHONIOENCODING: "utf-8" } };
    const child = execFile(/*turbopackIgnore: true*/ PYTHON, args, opts, (err, stdout, stderr) => {
      // The scan exits 1 on HOLD and 2 on FAIL — that is a verdict, not a crash.
      if (stdout.trim()) return resolve(stdout);
      reject(new Error(stderr.trim().split("\n").pop() || err?.message || "sentinel produced no output"));
    });
    if (stdin !== undefined) child.stdin?.end(stdin);
  });
}

let last: ScanReport | null = null;
let inFlight: Promise<ScanReport> | null = null;

export const lastScan = () => last;

// One scan at a time: concurrent callers share the running one.
export function runScan(): Promise<ScanReport> {
  inFlight ??= (async () => {
    const t0 = Date.now();
    try {
      const report = JSON.parse(await run(["-m", "security.sentinel", "scan", "--json"]));
      return (last = { ...report, durationMs: Date.now() - t0 });
    } finally {
      inFlight = null;
    }
  })();
  return inFlight;
}

export async function loadPolicy() {
  const p = parse(await readFile(path.join(ROOT, "security/policies/sentinel.yaml"), "utf8"));
  // The gate's execution kinds live in code, not policy: read them from the source of truth.
  const gateSrc = await readFile(path.join(ROOT, "security/sentinel/gate.py"), "utf8");
  const kinds = gateSrc.match(/EXECUTION_KINDS\s*=\s*frozenset\(\{([^}]*)\}\)/)?.[1] ?? "";
  return {
    version: p.version as number,
    bannedPrimitives: (p.execution?.banned_primitives ?? []) as string[],
    secretPatterns: Object.keys(p.secrets?.patterns ?? {}),
    adviceTerms: (p.deviation?.advice_terms ?? []) as string[],
    trustNeedsEvidenceFrom: p.trust?.min_level_requiring_evidence as number,
    executionKinds: [...kinds.matchAll(/"([a-z_]+)"/g)].map((m) => m[1]),
  };
}

const GATE_PY = `
import json, sys, yaml
from security.sentinel.gate import check_action
req = json.load(sys.stdin)
with open(req["manifest"], encoding="utf-8") as f:
    manifest = yaml.safe_load(f) or {}
r = check_action(req["action"], manifest)
print(json.dumps({"decision": r.decision.value, "reason": r.reason}))
`;

// Asks the real runtime gate. `manifestPath` must come from the registry, never from the client.
export async function askGate(manifestPath: string, action: { tool: string; kind: string }) {
  const out = await run(["-c", GATE_PY], JSON.stringify({ manifest: path.join(ROOT, manifestPath), action }), 20_000);
  return JSON.parse(out) as { decision: "allow" | "hold" | "deny"; reason: string };
}
