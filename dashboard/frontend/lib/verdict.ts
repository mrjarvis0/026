// Client-safe vocabulary for A002's outputs. Order = the diverging scale, real -> fake.
export const VERDICTS = [
  { id: "confirmed_true", label: "Confirmed", zone: "real", color: "#8fd0ff" },
  { id: "likely_true", label: "Likely true", zone: "real", color: "#3a7fb0" },
  { id: "unconfirmed", label: "Unconfirmed", zone: "rumor", color: "#454a52" },
  { id: "disputed", label: "Disputed", zone: "rumor", color: "#454a52" },
  { id: "likely_false", label: "Likely false", zone: "fake", color: "#9a5a2c" },
  { id: "confirmed_false", label: "Confirmed false", zone: "fake", color: "#e0803c" },
  { id: "fabricated", label: "Fabricated", zone: "fake", color: "#ffb57e" },
] as const;
// Palette validated with the dataviz checks on #0c0e12: each side passes as an ordinal ramp;
// the neutral clears ΔE 15 against both neighbours but sits under 3:1, so it always ships labelled.

export type VerdictId = (typeof VERDICTS)[number]["id"];
export const VERDICT = Object.fromEntries(VERDICTS.map((v) => [v.id, v])) as Record<
  VerdictId,
  (typeof VERDICTS)[number]
>;

export const ZONES = [
  { id: "real", label: "Real-leaning" },
  { id: "rumor", label: "Rumor · unresolved" },
  { id: "fake", label: "Fake-leaning" },
] as const;

export const CATEGORY_LABEL: Record<string, string> = {
  etf: "ETF",
  hack: "Hack / exploit",
  delisting: "Delisting",
  regulatory: "Regulatory",
  fraud: "Fraud",
  earnings: "Earnings",
  partnership: "Partnership",
  macro: "Macro",
  product_launch: "Product launch",
  executive_change: "Executive change",
  merger_acquisition: "M&A",
  guidance_change: "Guidance",
  dividend: "Dividend",
  stock_split: "Stock split",
  bankruptcy: "Bankruptcy",
  clinical_trial: "Clinical trial",
  patent: "Patent",
  contract_win: "Contract win",
  investigation: "Investigation",
  sanctions: "Sanctions",
  general: "General",
  unclassified: "Unclassified",
};

export const TIER_LABEL: Record<number, string> = {
  1: "Official",
  2: "Established media",
  3: "Crypto media",
  4: "Aggregator",
  5: "Social",
  6: "Anonymous",
};
