// Client-safe: shared by the server loader and the WebGL scene (which needs raw hex).
export const MATURITY = ["planned", "scaffold", "partial", "substantial", "complete"] as const;
export type Maturity = (typeof MATURITY)[number];

export const MATURITY_COLOR: Record<Maturity, string> = {
  planned: "#4a505b",
  scaffold: "#2a5670",
  partial: "#3b86b0",
  substantial: "#5fb8ea",
  complete: "#a6e1ff",
};

export const count = (n: number, noun: string) => `${n} ${noun}${n === 1 ? "" : "s"}`;

// Derived from the tool's verb in its typed name (e.g. brain.write) — not declared in manifests.
export const toolAccess = (t: string) =>
  /\.(write|post|delete|place)$/.test(t) ? "write" : /\.call$/.test(t) ? "call" : "read";
