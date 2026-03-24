export const STATE_DISPLAY: Record<string, { label: string; color: string; bg: string }> = {
  // Lifecycle states
  NEW:           { label: "New",       color: "text-text-dim",        bg: "bg-white/10" },
  SUBMITTED:     { label: "Pending",   color: "text-yellow-400",      bg: "bg-yellow-400/15" },
  VALIDATED:     { label: "Confirmed", color: "text-accent-green",    bg: "bg-accent-green/15" },
  AFFIRMED:      { label: "Confirmed", color: "text-accent-green",    bg: "bg-accent-green/15" },
  PRICED:        { label: "Confirmed", color: "text-accent-green",    bg: "bg-accent-green/15" },
  SETTLING:      { label: "Pending",   color: "text-yellow-400",      bg: "bg-yellow-400/15" },
  SETTLED:       { label: "Confirmed", color: "text-accent-green",    bg: "bg-accent-green/15" },
  // Exception states
  AMENDABLE:     { label: "Pending",   color: "text-yellow-400",      bg: "bg-yellow-400/15" },
  OPS_REVIEW:    { label: "Pending",   color: "text-yellow-400",      bg: "bg-yellow-400/15" },
  // Terminal negative
  REJECTED:      { label: "Rejected",  color: "text-accent-red",      bg: "bg-accent-red/15" },
  CANCELLED:     { label: "Cancelled", color: "text-accent-red",      bg: "bg-accent-red/15" },
};

export const TICKERS = ["SPY", "QQQ", "IWM", "VOO", "TLT", "XLF", "HYG", "EEM", "GLD", "VTI"];

export const METHODS = ["Cash", "In-Kind"];
export const BASKET_TYPES = ["Standard", "Custom"];
