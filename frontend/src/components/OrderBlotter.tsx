import StatusBadge from "./StatusBadge";
import { formatCurrency, formatDateTime } from "../lib/formatters";
import { STATE_DISPLAY } from "../lib/constants";
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
    const units = ctx.units || 0;
    const unitSize = ctx.unit_size || 50000;
    const shares = units * unitSize;
    const methodVal = ctx.method || "Cash";
    const basketVal = ctx.basket_type || "Standard";
    const settlement = methodVal === "In-Kind" ? "T+1 / IK" : "T+1 / DVP";
    const actionLabel = (ctx.action || "CREATE") === "CREATE" ? "create" : "redeem";
    const displayLabel = (STATE_DISPLAY[o.current_state]?.label || o.current_state).toLowerCase();
    return (
      String(o.id).includes(q) ||
      actionLabel.includes(q) ||
      (ctx.ticker || "").toLowerCase().includes(q) ||
      String(units).includes(q) ||
      shares.toLocaleString().toLowerCase().includes(q) ||
      methodVal.toLowerCase().includes(q) ||
      basketVal.toLowerCase().includes(q) ||
      settlement.toLowerCase().includes(q) ||
      o.current_state.toLowerCase().includes(q) ||
      displayLabel.includes(q) ||
      (o.created_at || "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex-1 bg-surface-panel glass rounded-lg border border-border-subtle flex flex-col overflow-hidden">
      <div className="px-3 py-1.5 border-b border-border-subtle flex justify-between items-center bg-surface-input/20">
        <h3 className="font-extrabold text-[11px] uppercase text-white tracking-wide">Order History</h3>
        <span className="text-[10px] bg-surface-input px-2 py-0.5 rounded-full border border-border-subtle text-text-dim">
          {filtered.length} Orders
        </span>
      </div>
      <div className="overflow-auto thin-scrollbar flex-1">
        <table className="w-full text-left text-xs tabular-nums border-collapse">
          <thead className="bg-surface-input/50 text-white uppercase text-[10px] font-extrabold sticky top-0">
            <tr>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">ID</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Type</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Ticker</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Units</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Shares</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Method</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Basket</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Total Value</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Settlement</th>
              <th className="px-3 py-1.5 border-r border-border-subtle/30">Status</th>
              <th className="px-3 py-1.5">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle/10">
            {filtered.length === 0 && (
              <tr>
                <td colSpan={11} className="px-3 py-6 text-center text-text-dim text-sm">
                  No orders found. Submit an order to get started.
                </td>
              </tr>
            )}
            {filtered.map((order) => {
              const ctx = order.context || {};
              const isCreate = (ctx.action || "CREATE") === "CREATE";
              const units = ctx.units || 0;
              const unitSize = ctx.unit_size || 50000;
              const shares = units * unitSize;
              const value = shares * 210;
              const methodVal = ctx.method || "Cash";
              const basketVal = ctx.basket_type || "Standard";
              const settlement = methodVal === "In-Kind" ? "T+1 / IK" : "T+1 / DVP";
              return (
                <tr
                  key={order.id}
                  onClick={() => onSelectOrder(order)}
                  className={`hover:bg-white/[0.06] transition-colors cursor-pointer ${
                    selectedOrderId === order.id ? "bg-accent-blue/[0.15] border-l-2 border-l-accent-blue" : ""
                  }`}
                >
                  <td className="px-3 py-1">#{order.id}</td>
                  <td className="px-3 py-1">
                    <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full inline-block ${
                      isCreate
                        ? "bg-accent-green/15 text-accent-green"
                        : "bg-accent-red/15 text-accent-red"
                    }`}>
                      {isCreate ? "Create" : "Redeem"}
                    </span>
                  </td>
                  <td className="px-3 py-1 font-bold">{ctx.ticker || "—"}</td>
                  <td className="px-3 py-1">{units}</td>
                  <td className="px-3 py-1">{shares.toLocaleString()}</td>
                  <td className="px-3 py-1">{methodVal}</td>
                  <td className="px-3 py-1">{basketVal}</td>
                  <td className="px-3 py-1">{formatCurrency(value)}</td>
                  <td className="px-3 py-1">{settlement}</td>
                  <td className="px-3 py-1">
                    <StatusBadge state={order.current_state} />
                  </td>
                  <td className="px-3 py-1 text-text-dim">{formatDateTime(order.created_at)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
