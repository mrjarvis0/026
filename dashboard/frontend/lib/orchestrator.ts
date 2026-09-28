import { readdir, stat } from "node:fs/promises";
import path from "node:path";
import { ROOT } from "./fleet";

// Server-only: the orchestrator's real build state, measured from the filesystem.
export type Module = { name: string; files: { path: string; bytes: number }[]; bytes: number; tests: number };

async function walk(dir: string): Promise<string[]> {
  const entries = await readdir(dir, { withFileTypes: true }).catch(() => []);
  const nested = await Promise.all(
    entries.map((e) => {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) return e.name === "__pycache__" ? [] : walk(p);
      return e.name.endsWith(".py") ? [p] : [];
    }),
  );
  return nested.flat();
}

export async function loadAnatomy() {
  const base = path.join(ROOT, "orchestrator");
  const dirs = (await readdir(base, { withFileTypes: true }))
    .filter((d) => d.isDirectory() && d.name !== "__pycache__")
    .map((d) => d.name)
    .sort();

  const modules: Module[] = await Promise.all(
    dirs.map(async (name) => {
      const all = await walk(path.join(base, name));
      const isTest = (p: string) => p.split(path.sep).includes("tests");
      const files = await Promise.all(
        all.filter((p) => !isTest(p)).map(async (p) => ({
          path: path.relative(ROOT, p).replaceAll("\\", "/"),
          bytes: (await stat(p)).size,
        })),
      );
      return {
        name,
        files,
        bytes: files.reduce((s, f) => s + f.bytes, 0),
        tests: all.filter(isTest).filter((p) => path.basename(p).startsWith("test_")).length,
      };
    }),
  );

  const models = await stat(path.join(ROOT, "config/models/models.yaml")).catch(() => null);
  return { modules, modelRoutingBytes: models?.size ?? null };
}
