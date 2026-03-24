import { useState } from "react";
import { mockPositions, positionSummary, type Position } from "../data/mockPositions";
import { formatCurrency, formatPnl, formatPct, formatNumber } from "../lib/formatters";

export default function PositionsPanel() {
  const [filter, setFilter] = useState<"All" | "L" | "S">("All");
  const [search, setSearch] = useState("");
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  const filtered = mockPositions.filter((p) => {
    if (filter === "L" && p.side !== "Long") return false;
    if (filter === "S" && p.side !== "Short") return false;
    if (search && !p.ticker.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex-[2] min-h-0 bg-surface-panel glass rounded-lg border border-border-subtle flex flex-col overflow-hidden">
      <div className="px-3 py-2 border-b border-border-subtle">
        <div className="flex items-center justify-between mb-1.5">
          <h3 className="font-bold text-xs uppercase">Positions</h3>
          <span className="text-[10px] bg-surface-input px-2 py-0.5 rounded-full text-text-dim border border-border-subtle">
            {filtered.length} positions
          </span>
        </div>

        <div className="flex items-end justify-between">
          <div className="flex gap-6">
            <div>
              <div className="text-[10px] font-bold text-text-dim uppercase mb-0.5">Long MV</div>
              <div className="text-sm font-black text-accent-green tabular-nums">
                {formatCurrency(positionSummary.longMv)}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-bold text-text-dim uppercase mb-0.5">Short MV</div>
              <div className="text-sm font-black text-accent-red tabular-nums">
                {formatCurrency(positionSummary.shortMv)}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-bold text-text-dim uppercase mb-0.5">Net MV</div>
              <div className="text-sm font-black text-accent-green tabular-nums">
                {formatCurrency(positionSummary.netMv)}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-bold text-text-dim uppercase mb-0.5">Unrealized P&L</div>
              <div className="text-sm font-black text-accent-green tabular-nums">
                {formatPnl(positionSummary.unrealPnl)}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-bold text-text-dim uppercase mb-0.5">Realized P&L</div>
              <div className="text-sm font-black text-accent-green tabular-nums">
                {formatPnl(positionSummary.realPnl)}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <div className="flex gap-0.5 p-0.5 bg-bg-main rounded border border-border-subtle">
              {([["All", "All"], ["L", "Long"], ["S", "Short"]] as const).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setFilter(key)}
                  className={`px-2 py-0.5 text-[11px] font-bold rounded transition-colors ${
                    filter === key ? "bg-accent-blue/20 text-accent-blue" : "text-text-dim hover:text-white"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="flex bg-surface-input rounded border border-border-subtle p-0.5">
              <input
                className="bg-transparent border-none text-[11px] px-2 outline-none w-28 placeholder:text-text-dim"
                placeholder="Search ticker..."
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="overflow-auto flex-1 thin-scrollbar">
        <table className="w-full text-left text-xs tabular-nums border-collapse">
          <thead className="bg-surface-input/40 text-text-dim uppercase text-[10px] font-bold sticky top-0 z-10 whitespace-nowrap">
            <tr>
              <th className="px-2 py-1">Ticker ↕</th>
              <th className="px-2 py-1">Side</th>
              <th className="px-2 py-1 text-right">Shares ↕</th>
              <th className="px-2 py-1 text-right">Avg Cost ↕</th>
              <th className="px-2 py-1 text-right">Price ↕</th>
              <th className="px-2 py-1 text-right">Mkt Value ▼</th>
              <th className="px-2 py-1 text-right">Unreal. P&L ↕</th>
              <th className="px-2 py-1 text-right">P&L % ↕</th>
              <th className="px-2 py-1 text-right">Real. P&L ↕</th>
              <th className="px-2 py-1 text-right">Day Chg ↕</th>
              <th className="px-2 py-1 text-right">NAV ↕</th>
              <th className="px-2 py-1 text-right">Prem/Disc ↕</th>
              <th className="px-2 py-1 text-right">Weight ↕</th>
              <th className="px-2 py-1 text-right">Last Updated</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle/10">
            {filtered.map((p) => (
              <tr
                key={p.ticker}
                onClick={() => setSelectedTicker(selectedTicker === p.ticker ? null : p.ticker)}
                className={`hover:bg-white/[0.06] transition-colors whitespace-nowrap cursor-pointer ${
                  selectedTicker === p.ticker ? "bg-accent-blue/[0.15] border-l-2 border-l-accent-blue" : ""
                }`}
              >
                <td className="px-2 py-1 font-bold">{p.ticker}</td>
                <td className="px-2 py-1">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full inline-block ${
                    p.side === "Long"
                      ? "bg-accent-green/15 text-accent-green"
                      : "bg-accent-red/15 text-accent-red"
                  }`}>
                    {p.side}
                  </span>
                </td>
                <td className="px-2 py-1 text-right">{formatNumber(p.shares)}</td>
                <td className="px-2 py-1 text-right">${p.avgCost.toFixed(2)}</td>
                <td className="px-2 py-1 text-right font-bold">${p.price.toFixed(2)}</td>
                <td className="px-2 py-1 text-right">{formatCurrency(p.mktValue)}</td>
                <td className={`px-2 py-1 text-right ${p.unrealPnl >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                  {p.unrealPnl >= 0 ? "▲" : "▼"} {formatPnl(p.unrealPnl)}
                </td>
                <td className={`px-2 py-1 text-right ${p.pnlPct >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                  {formatPct(p.pnlPct)}
                </td>
                <td className={`px-2 py-1 text-right ${p.realPnl >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                  {formatPnl(p.realPnl)}
                </td>
                <td className={`px-2 py-1 text-right ${p.dayChg >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                  {p.dayChg >= 0 ? "▲" : "▼"} ${Math.abs(p.dayChg).toFixed(2)} ({formatPct(p.dayChgPct)})
                </td>
                <td className="px-2 py-1 text-right">${p.nav.toFixed(2)}</td>
                <td className="px-2 py-1 text-right">{p.premDisc >= 0 ? "+" : ""}{p.premDisc.toFixed(2)}%</td>
                <td className="px-2 py-1 text-right">{p.weight.toFixed(1)}%</td>
                <td className="px-2 py-1 text-right text-text-dim">{p.lastUpdated}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
