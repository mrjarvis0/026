// Status colours are reserved for real states (sentinel verdicts, gate decisions, bus outcomes)
// and always ship with a label. Client-safe: no three.js, no node imports.
export const STATE_COLOR: Record<string, string> = {
  PASS: "#0ca30c",
  HOLD: "#fab219",
  FAIL: "#d03b3b",
  allow: "#0ca30c",
  hold: "#fab219",
  deny: "#d03b3b",
};

export const BUS_STATUS_COLOR: Record<string, string> = {
  ok: "#0ca30c",
  held: "#fab219",
  denied: "#d03b3b",
  error: "#d03b3b",
  degraded: "#ec835a",
  no_handler: "#6b7280",
};

// A001 block capture states (blocks.complete + incomplete_reason) — coverage before absence.
export type BlockState = "complete" | "selective" | "unfetched";
export const BLOCK_STATE: Record<BlockState, { color: string; label: string }> = {
  complete: { color: "#5fb8ea", label: "complete — every transaction and token transfer stored" },
  selective: { color: "#fab219", label: "selective — only transactions above the capture floor kept" },
  unfetched: { color: "#6b7280", label: "logs missing — transactions stored, token-transfer logs never obtained" },
};
