import StatusBadge from "./StatusBadge";
import { formatCurrencyCompact, formatTime } from "../lib/formatters";
import type { InstanceResponse } from "../api/types";

interface Props {
  orders: InstanceResponse[];
  searchQuery: string;
  onSelectOrder: (order: InstanceResponse) => void;
  selectedOrderId: number | null;
}

export default function OrderBlotter({ orders, searchQuery, onSelectOrder, selectedOrderId }: Props) {
  const filtered = orders.filter((o) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    const ctx = o.context || {};
    return (
      String(o.id).includes(q) ||
      (ctx.ticker || "").toLowerCase().includes(q) ||
      (ctx.action || "").toLowerCase().includes(q) ||
      o.current_state.toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex-1 bg-surface-panel glass rounded-lg border border-border-subtle flex flex-col overflow-hidden">
      <div className="px-3 py-1.5 border-b border-border-subtle flex justify-between items-center bg-surface-input/20">
        <h3 className="font-bold text-[11px] uppercase text-text-dim tracking-wide">Order History</h3>
        <span className="text-[10px] bg-surface-input px-2 py-0.5 rounded-full border border-border-subtle text-text-dim">
          {filtered.length} Items
        </span>
      </div>
      <div className="overflow-auto thin-scrollbar flex-1">
        <table className="w-full text-left text-xs tabular-nums border-collapse">
          <thead className="bg-surface-input/50 text-text-dim uppercase text-[10px] font-bold sticky top-0">
            <tr>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">ID</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Side</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Ticker</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Units</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Value</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Settlement</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Status</th>
              <th className="px-3 py-1.5">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle/10">
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-text-dim text-sm">
                  No orders found. Submit an order to get started.
                </td>
              </tr>
            )}
            {filtered.map((order) => {
              const ctx = order.context || {};
              const isCreate = (ctx.action || "CREATE") === "CREATE";
              const units = ctx.units || 0;
              const unitSize = ctx.unit_size || 50000;
              const value = units * unitSize * 210;
              return (
                <tr
                  key={order.id}
                  onClick={() => onSelectOrder(order)}
                  className={`hover:bg-white/[0.04] transition-colors cursor-pointer ${
                    selectedOrderId === order.id ? "bg-accent-blue/[0.06]" : ""
                  }`}
                >
                  <td className="px-3 py-1">#{order.id}</td>
                  <td className={`px-3 py-1 font-bold ${isCreate ? "text-accent-green" : "text-accent-red"}`}>
                    {isCreate ? "C" : "R"}
                  </td>
                  <td className="px-3 py-1 font-bold">{ctx.ticker || "—"}</td>
                  <td className="px-3 py-1">{units}</td>
                  <td className="px-3 py-1">{formatCurrencyCompact(value)}</td>
                  <td className="px-3 py-1">{ctx.method === "In-Kind" ? "T+1/IK" : "T+1/DVP"}</td>
                  <td className="px-3 py-1">
                    <StatusBadge state={order.current_state} />
                  </td>
                  <td className="px-3 py-1 text-text-dim">{formatTime(order.created_at)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
