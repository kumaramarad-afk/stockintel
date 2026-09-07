export function isPlaceholder(value: unknown) {
  if (value == null) return false;
  if (typeof value === "string") return value.includes("$$$") || value === "🔒";
  return false;
}

export function formatPrice(value: string | number | null | undefined) {
  if (value === null || value === undefined) return "—";
  if (isPlaceholder(value)) return String(value);
  const amount = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(amount)) return "—";
  return amount.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

export function formatChange(value: string | number | null | undefined) {
  if (value === null || value === undefined) return { label: "—", positive: true };
  const amount = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(amount)) return { label: "—", positive: true };
  const positive = amount >= 0;
  return { label: `${positive ? "+" : ""}${amount.toFixed(2)}%`, positive };
}

export function formatDate(value: string | null | undefined) {
  if (!value) return "Draft";
  return new Date(value).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatCompact(value: string | number | null | undefined) {
  if (value === null || value === undefined) return "—";
  if (isPlaceholder(value)) return String(value);
  const amount = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(amount)) return "—";
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 }).format(amount);
}

export function formatRatio(value: string | number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "—";
  if (isPlaceholder(value)) return String(value);
  const amount = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(amount)) return "—";
  return amount.toFixed(digits);
}

export function formatVolume(value: string | number | null | undefined) {
  return formatCompact(value);
}

export function formatSigned(value: string | number | null | undefined, digits = 2, suffix = "") {
  if (value === null || value === undefined) return "—";
  if (isPlaceholder(value)) return String(value);
  const amount = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(amount)) return "—";
  const sign = amount > 0 ? "+" : "";
  return `${sign}${amount.toFixed(digits)}${suffix}`;
}

export function toneClass(value: number | boolean | string | null | undefined, invert = false) {
  if (value === null || value === undefined || isPlaceholder(value)) return "text-slate-400";
  let positive: boolean;
  let negative: boolean;
  if (typeof value === "boolean") {
    positive = value;
    negative = !value;
  } else {
    const amount = typeof value === "number" ? value : Number(value);
    if (Number.isNaN(amount)) return "text-slate-400";
    positive = amount > 0;
    negative = amount < 0;
  }
  if (invert) {
    if (positive) return "text-rose-400";
    if (negative) return "text-gsr-accent";
    return "text-amber-300";
  }
  if (positive) return "text-gsr-accent";
  if (negative) return "text-rose-400";
  return "text-amber-300";
}

export function scoreColor(score: number | null | undefined) {
  if (score === null || score === undefined) return "text-slate-400";
  if (score <= 50) return "text-rose-400";
  if (score <= 70) return "text-amber-300";
  return "text-gsr-accent";
}

export function scoreBarColor(score: number | null | undefined) {
  if (score === null || score === undefined) return "bg-slate-600";
  if (score <= 50) return "bg-rose-500";
  if (score <= 70) return "bg-amber-400";
  return "bg-gsr-accent";
}

