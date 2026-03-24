import { useState } from "react";
import { mockPositions, positionSummary, type Position } from "../data/mockPositions";
import { formatCurrency, formatPnl, formatPct, formatNumber } from "../lib/formatters";

export default function PositionsPanel() {
  const [filter, setFilter] = useState<"All" | "L" | "S">("All");
  const [search, setSearch] = useState("");

  const filtered = mockPositions.filter((p) => {
    if (filter === "L" && p.side !== "Long") return false;
    if (filter === "S" && p.side !== "Short") return false;
    if (search && !p.ticker.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex-1 bg-surface-panel glass rounded-lg border border-border-subtle flex flex-col overflow-hidden">
      <div className="p-3 border-b border-border-subtle">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-xs uppercase">Positions</h3>
            <span className="text-[10px] bg-surface-input px-2 py-0.5 rounded-full text-text-dim border border-border-subtle">
              {filtered.length}
            </span>
            <span className="text-[9px] italic text-text-dim">Sample Data</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex bg-surface-input rounded border border-border-subtle p-0.5">
              <input
                className="bg-transparent border-none text-[11px] px-2 outline-none w-36 placeholder:text-text-dim"
                placeholder="Search ticker..."
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex gap-1 p-0.5 bg-bg-main rounded border border-border-subtle">
              {(["All", "L", "S"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-2.5 py-0.5 text-[11px] font-bold rounded transition-colors ${
                    filter === f ? "bg-accent-blue/20 text-accent-blue" : "text-text-dim hover:text-white"
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-5 gap-4 border-t border-border-subtle/30 pt-2">
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
      </div>

      <div className="overflow-auto flex-1 thin-scrollbar">
        <table className="w-full text-left text-xs tabular-nums border-collapse">
          <thead className="bg-surface-input/40 text-text-dim uppercase text-[10px] font-bold sticky top-0 z-10">
            <tr>
              <th className="px-3 py-1.5">Ticker</th>
              <th className="px-3 py-1.5">Side</th>
              <th className="px-3 py-1.5 text-right">Shares</th>
              <th className="px-3 py-1.5 text-right">Avg Cost</th>
              <th className="px-3 py-1.5 text-right">Price</th>
              <th className="px-3 py-1.5 text-right">Mkt Value</th>
              <th className="px-3 py-1.5 text-right">Unreal. P&L</th>
              <th className="px-3 py-1.5 text-right">P&L %</th>
              <th className="px-3 py-1.5 text-right">Real. P&L</th>
              <th className="px-3 py-1.5 text-right">Day Chg</th>
              <th className="px-3 py-1.5 text-right">NAV</th>
              <th className="px-3 py-1.5 text-right">Weight</th>
              <th className="px-3 py-1.5 text-right">Last Updated</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle/10">
            {filtered.map((p) => (
              <tr key={p.ticker} className="hover:bg-white/[0.04] transition-colors">
                <td className="px-3 py-1 font-bold">{p.ticker}</td>
                <td className="px-3 py-1">
                  {p.side === "Long" ? (
                    <span className="text-accent-green font-bold text-[11px]">Long</span>
                  ) : (
                    <span className="bg-accent-red/15 text-accent-red px-1.5 py-0.5 rounded font-bold text-[11px]">Short</span>
                  )}
                </td>
                <td className="px-3 py-1 text-right">{formatNumber(p.shares)}</td>
                <td className="px-3 py-1 text-right">{p.avgCost.toFixed(2)}</td>
                <td className="px-3 py-1 text-right font-bold">{p.price.toFixed(2)}</td>
                <td className="px-3 py-1 text-right">{formatCurrency(p.mktValue)}</td>
                <td className={`px-3 py-1 text-right ${p.unrealPnl >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                  {formatPnl(p.unrealPnl)}
                </td>
                <td className={`px-3 py-1 text-right ${p.pnlPct >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                  {formatPct(p.pnlPct)}
                </td>
                <td className={`px-3 py-1 text-right ${p.realPnl >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                  {formatPnl(p.realPnl)}
                </td>
                <td className={`px-3 py-1 text-right ${p.dayChg >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                  {p.dayChg >= 0 ? "+" : ""}${p.dayChg.toFixed(2)} ({formatPct(p.dayChgPct)})
                </td>
                <td className="px-3 py-1 text-right">{p.nav.toFixed(2)}</td>
                <td className="px-3 py-1 text-right">{p.weight.toFixed(1)}%</td>
                <td className="px-3 py-1 text-right text-text-dim">{p.lastUpdated}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
