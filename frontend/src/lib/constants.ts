export const STATE_DISPLAY: Record<string, { label: string; color: string }> = {
  // Lifecycle states
  NEW:           { label: "NEW",  color: "text-text-dim" },
  SUBMITTED:     { label: "SENT", color: "text-accent-blue" },
  VALIDATED:     { label: "VALD", color: "text-accent-blue" },
  AFFIRMED:      { label: "AFRM", color: "text-accent-green" },
  PRICED:        { label: "PRCD", color: "text-accent-green" },
  SETTLING:      { label: "STLG", color: "text-accent-blue" },
  SETTLED:       { label: "DONE", color: "text-accent-green" },
  // Exception states
  AMENDABLE:     { label: "AMND", color: "text-yellow-400" },
  OPS_REVIEW:    { label: "OPS",  color: "text-yellow-400" },
  // Terminal negative
  REJECTED:      { label: "REJ",  color: "text-accent-red" },
  CANCELLED:     { label: "CXLD", color: "text-accent-red" },
};

export const TICKERS = ["SPY", "QQQ", "IWM", "VOO", "TLT", "XLF", "HYG", "EEM", "GLD", "VTI"];

export const METHODS = ["Cash", "In-Kind"];
export const BASKET_TYPES = ["Standard", "Custom"];
