// Locale-aware formatters. Default to en-US; per-org locale arrives in Phase 3
// alongside FE-013 i18n.

const USD = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const COMPACT = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
const DATE = new Intl.DateTimeFormat("en-US", { dateStyle: "medium" });
const DATETIME = new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" });

export function formatCurrency(amount: number): string {
  return USD.format(amount);
}

// Sub-cent costs are common; keep extra precision for those.
export function formatCost(usd: number): string {
  if (usd === 0) return "$0.00";
  if (Math.abs(usd) < 0.01) return `$${usd.toFixed(6)}`;
  return USD.format(usd);
}

export function formatTokens(tokens: number): string {
  return COMPACT.format(tokens);
}

export function formatDate(value: Date | string | number): string {
  const date = typeof value === "object" ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return DATE.format(date);
}

// Convenience for the model marketplace pricing displays.
export function formatPerMillion(usdPerMillion: number): string {
  return formatCost(usdPerMillion);
}

export function formatDateTime(value: Date | string | number): string {
  return DATETIME.format(typeof value === "object" ? value : new Date(value));
}

export function formatRelative(value: Date | string | number): string {
  const date = typeof value === "object" ? value : new Date(value);
  const diffMs = date.getTime() - Date.now();
  const rtf = new Intl.RelativeTimeFormat("en-US", { numeric: "auto" });
  const ranges: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["year", 1000 * 60 * 60 * 24 * 365],
    ["month", 1000 * 60 * 60 * 24 * 30],
    ["day", 1000 * 60 * 60 * 24],
    ["hour", 1000 * 60 * 60],
    ["minute", 1000 * 60],
    ["second", 1000],
  ];
  for (const [unit, ms] of ranges) {
    if (Math.abs(diffMs) >= ms || unit === "second") {
      return rtf.format(Math.round(diffMs / ms), unit);
    }
  }
  return DATE.format(date);
}
