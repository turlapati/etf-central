export interface Position {
  ticker: string;
  side: "Long" | "Short";
  shares: number;
  avgCost: number;
  price: number;
  mktValue: number;
  unrealPnl: number;
  pnlPct: number;
  realPnl: number;
  dayChg: number;
  dayChgPct: number;
  nav: number;
  weight: number;
  lastUpdated: string;
}

export const mockPositions: Position[] = [
  { ticker: "SPY", side: "Long", shares: 25000, avgCost: 548.10, price: 571.82, mktValue: 14295500, unrealPnl: 593000, pnlPct: 4.33, realPnl: 12400, dayChg: 3.21, dayChgPct: 0.56, nav: 571.64, weight: 32.9, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "QQQ", side: "Long", shares: 18000, avgCost: 472.50, price: 489.56, mktValue: 8812080, unrealPnl: 307080, pnlPct: 3.61, realPnl: 8750, dayChg: 2.14, dayChgPct: 0.44, nav: 489.21, weight: 20.3, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "IWM", side: "Long", shares: 40000, avgCost: 210.34, price: 218.46, mktValue: 8738400, unrealPnl: 324800, pnlPct: 3.86, realPnl: 15200, dayChg: 1.52, dayChgPct: 0.70, nav: 218.31, weight: 20.1, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "TLT", side: "Long", shares: 30000, avgCost: 96.80, price: 92.17, mktValue: 2765100, unrealPnl: -138900, pnlPct: -4.78, realPnl: -5100, dayChg: -0.44, dayChgPct: -0.47, nav: 92.09, weight: 6.4, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "VOO", side: "Long", shares: 8000, avgCost: 502.20, price: 526.38, mktValue: 4211040, unrealPnl: 193440, pnlPct: 4.82, realPnl: 7200, dayChg: 2.95, dayChgPct: 0.56, nav: 526.12, weight: 9.7, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "GLD", side: "Long", shares: 12000, avgCost: 178.40, price: 185.62, mktValue: 2227440, unrealPnl: 86640, pnlPct: 4.05, realPnl: 3200, dayChg: 0.88, dayChgPct: 0.48, nav: 185.50, weight: 5.1, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "XLF", side: "Short", shares: -20000, avgCost: 46.10, price: 43.26, mktValue: -865200, unrealPnl: 56800, pnlPct: 6.16, realPnl: 4300, dayChg: -0.32, dayChgPct: -0.73, nav: 43.19, weight: 2.0, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "HYG", side: "Short", shares: -50000, avgCost: 78.30, price: 78.35, mktValue: -3917500, unrealPnl: -2500, pnlPct: -0.06, realPnl: 18200, dayChg: -0.08, dayChgPct: -0.10, nav: 78.28, weight: 9.0, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "EEM", side: "Long", shares: 35000, avgCost: 42.80, price: 44.92, mktValue: 1572200, unrealPnl: 74200, pnlPct: 4.95, realPnl: 2100, dayChg: 0.34, dayChgPct: 0.76, nav: 44.85, weight: 3.6, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "VTI", side: "Long", shares: 5000, avgCost: 244.60, price: 252.18, mktValue: 1260900, unrealPnl: 37900, pnlPct: 3.10, realPnl: 1500, dayChg: 1.42, dayChgPct: 0.57, nav: 252.02, weight: 2.9, lastUpdated: "2026-03-17 16:00:01" },
];

export const positionSummary = {
  longMv: 43882660,
  shortMv: -4782700,
  netMv: 39099960,
  unrealPnl: 1532460,
  realPnl: 67650,
};
