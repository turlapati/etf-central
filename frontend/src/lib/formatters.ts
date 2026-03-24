export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
}

export function formatCurrencyCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000).toLocaleString("en-US", { maximumFractionDigits: 0 })}k`;
  }
  return `$${value.toLocaleString("en-US", { maximumFractionDigits: 0 })}k`;
}

export function formatNumber(value: number): string {
  return value.toLocaleString("en-US");
}

export function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString("en-US", { hour12: false });
}

export function formatPct(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function formatPnl(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${formatCurrency(value)}`;
}
