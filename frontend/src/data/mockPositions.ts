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
  premDisc: number;
  weight: number;
  lastUpdated: string;
}

export const mockPositions: Position[] = [
  { ticker: "SPY", side: "Long", shares: 25000, avgCost: 548.10, price: 571.82, mktValue: 14295500, unrealPnl: 593000, pnlPct: 4.33, realPnl: 12400, dayChg: 3.21, dayChgPct: 0.56, nav: 571.64, premDisc: 0.03, weight: 32.9, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "QQQ", side: "Long", shares: 18000, avgCost: 472.50, price: 489.56, mktValue: 8812080, unrealPnl: 307080, pnlPct: 3.61, realPnl: 8750, dayChg: 2.14, dayChgPct: 0.44, nav: 489.21, premDisc: 0.07, weight: 20.3, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "VOO", side: "Long", shares: 12000, avgCost: 505.60, price: 525.14, mktValue: 6301680, unrealPnl: 234480, pnlPct: 3.86, realPnl: 9400, dayChg: 2.97, dayChgPct: 0.57, nav: 524.95, premDisc: 0.04, weight: 14.5, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "HYG", side: "Long", shares: 40000, avgCost: 75.90, price: 77.38, mktValue: 3095200, unrealPnl: 59200, pnlPct: 1.95, realPnl: 6200, dayChg: 0.11, dayChgPct: 0.14, nav: 77.31, premDisc: 0.09, weight: 7.1, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "TLT", side: "Long", shares: 30000, avgCost: 96.80, price: 92.17, mktValue: 2765100, unrealPnl: -138900, pnlPct: -4.78, realPnl: -5100, dayChg: -0.44, dayChgPct: -0.47, nav: 92.09, premDisc: 0.09, weight: 6.4, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "GLD", side: "Long", shares: 8000, avgCost: 198.30, price: 215.90, mktValue: 1727200, unrealPnl: 140800, pnlPct: 8.88, realPnl: 21500, dayChg: 1.85, dayChgPct: 0.86, nav: 215.72, premDisc: 0.08, weight: 4.0, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "IQD", side: "Long", shares: 15000, avgCost: 105.20, price: 108.52, mktValue: 1627800, unrealPnl: 49800, pnlPct: 3.16, realPnl: 3100, dayChg: 0.28, dayChgPct: 0.26, nav: 108.41, premDisc: 0.10, weight: 3.8, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "XLF", side: "Short", shares: -20000, avgCost: 46.10, price: 43.26, mktValue: -865200, unrealPnl: 56800, pnlPct: 6.16, realPnl: 4300, dayChg: -0.32, dayChgPct: -0.73, nav: 43.19, premDisc: 0.16, weight: 2.0, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "EFA", side: "Short", shares: -22000, avgCost: 85.40, price: 82.45, mktValue: -1813900, unrealPnl: 64900, pnlPct: 3.45, realPnl: 1800, dayChg: -0.55, dayChgPct: -0.66, nav: 82.32, premDisc: 0.16, weight: 4.2, lastUpdated: "2026-03-17 16:00:01" },
  { ticker: "IWM", side: "Short", shares: -10000, avgCost: 218.45, price: 210.34, mktValue: -2103400, unrealPnl: 81100, pnlPct: 3.71, realPnl: -3200, dayChg: -1.08, dayChgPct: -0.51, nav: 210.18, premDisc: 0.08, weight: 4.8, lastUpdated: "2026-03-17 16:00:01" },
];

export const positionSummary = {
  longMv: 43882660,
  shortMv: -4782700,
  netMv: 39099960,
  unrealPnl: 1532460,
  realPnl: 67650,
};
