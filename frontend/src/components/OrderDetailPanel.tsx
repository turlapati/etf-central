import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getOrder, getHistory, fireTrigger } from "../api/etfOrders";
import type { InstanceResponse, TriggerSchema } from "../api/types";
import StatusBadge from "./StatusBadge";

interface Props {
  order: InstanceResponse;
  onClose: () => void;
}

const TRIGGER_LABELS: Record<string, { label: string; color: string }> = {
  SUBMIT:              { label: "Submit",           color: "bg-accent-blue text-white" },
  PASS_VALIDATION:     { label: "Pass Validation",  color: "bg-accent-blue text-white" },
  AFFIRM:              { label: "Affirm",           color: "bg-accent-green text-bg-main" },
  PRICE:               { label: "Strike NAV",       color: "bg-accent-green text-bg-main" },
  GENERATE_SETTLEMENT: { label: "Gen. Settlement",  color: "bg-accent-blue text-white" },
  CONFIRM_SETTLEMENT:  { label: "Confirm Settle",   color: "bg-accent-green text-bg-main" },
  REJECT_SOFT:         { label: "Soft Reject",      color: "bg-yellow-500/20 text-yellow-400" },
  REJECT_HARD:         { label: "Hard Reject",      color: "bg-accent-red text-white" },
  REJECT:              { label: "Reject",           color: "bg-accent-red text-white" },
  SETTLEMENT_FAIL:     { label: "Settle Failed",    color: "bg-accent-red/20 text-accent-red" },
  RETRY_SETTLEMENT:    { label: "Retry Settle",     color: "bg-accent-blue text-white" },
  ESCALATE_CANCEL:     { label: "Escalate Cancel",  color: "bg-accent-red text-white" },
  AMEND_RESUBMIT:      { label: "Amend & Resubmit", color: "bg-yellow-500/20 text-yellow-400" },
  ABANDON:             { label: "Abandon",          color: "bg-accent-red/20 text-accent-red" },
  CANCEL:              { label: "Cancel",           color: "bg-accent-red/20 text-accent-red" },
};

/* ── Derive form fields from JSON Schema ── */

interface FieldDef {
  key: string;
  label: string;
  type: "text" | "number" | "select";
  options?: string[];
  placeholder?: string;
  isDate: boolean;
}

function schemaToFields(schema: TriggerSchema["payload_schema"]): FieldDef[] {
  const props = schema.properties;
  if (!props || Object.keys(props).length === 0) return [];

  return Object.entries(props).map(([key, prop]) => {
    const isDate = key.toLowerCase().includes("date");
    const isSelect = !!prop.enum && prop.enum.length > 0;
    const label = key
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());

    return {
      key,
      label,
      type: isSelect ? "select" : prop.type === "number" ? "number" : "text",
      options: prop.enum,
      placeholder: isDate ? "YYYY-MM-DD" : prop.type === "number" ? "0.00" : undefined,
      isDate,
    };
  });
}

/* ── Inline payload form ── */

function InlinePayloadForm({
  trigger,
  fields,
  onSubmit,
  onCancel,
  isPending,
}: {
  trigger: string;
  fields: FieldDef[];
  onSubmit: (payload: Record<string, any>) => void;
  onCancel: () => void;
  isPending: boolean;
}) {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    const today = new Date().toISOString().split("T")[0];
    for (const f of fields) init[f.key] = f.isDate ? today : "";
    return init;
  });

  function handleSubmit() {
    const payload: Record<string, any> = {};
    for (const f of fields) {
      const v = values[f.key]?.trim();
      if (!v) continue;
      payload[f.key] = f.type === "number" ? parseFloat(v) : v;
    }
    onSubmit(payload);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") { e.preventDefault(); handleSubmit(); }
    if (e.key === "Escape") { e.preventDefault(); onCancel(); }
  }

  const info = TRIGGER_LABELS[trigger];

  return (
    <div className="bg-surface-input/30 rounded-md border border-border-subtle p-2 space-y-1.5 animate-in">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold text-white uppercase">{info?.label || trigger}</span>
        <span className="text-[9px] text-text-dim">Enter to confirm &middot; Esc to cancel</span>
      </div>
      {fields.map((f) => (
        <div key={f.key} className="flex items-center gap-2">
          <label className="text-[10px] text-text-dim w-20 shrink-0 text-right">{f.label}</label>
          {f.type === "select" ? (
            <select
              value={values[f.key]}
              onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
              onKeyDown={handleKeyDown}
              className="flex-1 bg-surface-input border border-border-subtle rounded px-1.5 py-0.5 text-[11px] text-white outline-none focus:border-accent-blue/50"
            >
              <option value="">—</option>
              {f.options?.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          ) : (
            <input
              type="text"
              value={values[f.key]}
              onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
              onKeyDown={handleKeyDown}
              placeholder={f.placeholder}
              className="flex-1 bg-surface-input border border-border-subtle rounded px-1.5 py-0.5 text-[11px] text-white outline-none placeholder:text-text-dim/40 focus:border-accent-blue/50"
              autoFocus={fields[0].key === f.key}
            />
          )}
        </div>
      ))}
      <div className="flex gap-1.5 pt-0.5">
        <button
          onClick={handleSubmit}
          disabled={isPending}
          className={`flex-1 py-1 rounded text-[10px] font-bold ${info?.color || "bg-accent-blue text-white"} hover:brightness-110 disabled:opacity-50 transition-all`}
        >
          {isPending ? "..." : info?.label || trigger}
        </button>
        <button
          onClick={onCancel}
          className="px-3 py-1 rounded text-[10px] font-bold bg-surface-input text-text-dim border border-border-subtle hover:text-white transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

/* ── Main panel ── */

export default function OrderDetailPanel({ order, onClose }: Props) {
  const queryClient = useQueryClient();
  const [expandedTrigger, setExpandedTrigger] = useState<string | null>(null);

  const { data: detail } = useQuery({
    queryKey: ["order", order.id],
    queryFn: () => getOrder(order.id),
    refetchInterval: 5000,
  });

  const { data: history } = useQuery({
    queryKey: ["history", order.id],
    queryFn: () => getHistory(order.id),
    refetchInterval: 5000,
  });

  const triggerMutation = useMutation({
    mutationFn: ({ trigger, payload }: { trigger: string; payload?: Record<string, any> }) =>
      fireTrigger(order.id, trigger, payload),
    onSuccess: () => {
      setExpandedTrigger(null);
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["order", order.id] });
      queryClient.invalidateQueries({ queryKey: ["history", order.id] });
    },
  });

  // Build field definitions from API schemas
  const triggerFieldMap = useMemo(() => {
    const map: Record<string, FieldDef[]> = {};
    for (const t of detail?.available_triggers || []) {
      const fields = schemaToFields(t.payload_schema);
      if (fields.length > 0) map[t.name] = fields;
    }
    return map;
  }, [detail?.available_triggers]);

  const events = detail?.available_events || [];
  const ctx = detail?.context || order.context || {};
  const currentState = detail?.current_state || order.current_state;

  function handleTriggerClick(trigger: string) {
    if (triggerFieldMap[trigger]) {
      setExpandedTrigger(expandedTrigger === trigger ? null : trigger);
    } else {
      triggerMutation.mutate({ trigger });
    }
  }

  return (
    <div className="w-76 bg-surface-panel glass rounded-lg border border-border-subtle p-3 flex flex-col gap-2.5 overflow-y-auto no-scrollbar shrink-0">
      <div className="flex justify-between items-center">
        <h2 className="font-bold text-sm uppercase tracking-tight">Order #{order.id}</h2>
        <button onClick={onClose} className="text-text-dim hover:text-white transition-colors">
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>close</span>
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-text-dim text-[10px] uppercase font-bold">State</span>
          <div><StatusBadge state={currentState} /></div>
        </div>
        <div>
          <span className="text-text-dim text-[10px] uppercase font-bold">Action</span>
          <div className={ctx.action === "CREATE" ? "text-accent-green font-bold" : "text-accent-red font-bold"}>
            {ctx.action || "—"}
          </div>
        </div>
        <div>
          <span className="text-text-dim text-[10px] uppercase font-bold">Ticker</span>
          <div className="font-bold">{ctx.ticker || "—"}</div>
        </div>
        <div>
          <span className="text-text-dim text-[10px] uppercase font-bold">Units</span>
          <div>{ctx.units || "—"}</div>
        </div>
        <div>
          <span className="text-text-dim text-[10px] uppercase font-bold">Method</span>
          <div>{ctx.method || "—"}</div>
        </div>
        <div>
          <span className="text-text-dim text-[10px] uppercase font-bold">Basket</span>
          <div>{ctx.basket_type || "—"}</div>
        </div>
      </div>

      {events.length > 0 && (
        <div>
          <div className="text-[10px] font-bold text-text-dim uppercase mb-1.5">Actions</div>
          <div className="flex flex-wrap gap-1.5">
            {events.map((evt) => {
              const info = TRIGGER_LABELS[evt] || { label: evt, color: "bg-surface-input text-text-dim" };
              const hasFields = !!triggerFieldMap[evt];
              const isExpanded = expandedTrigger === evt;
              const isDimmed = expandedTrigger !== null;
              return (
                <button
                  key={evt}
                  onClick={() => handleTriggerClick(evt)}
                  disabled={triggerMutation.isPending || (isDimmed && !isExpanded)}
                  className={`px-2.5 py-1 rounded text-[11px] font-bold transition-all ${
                    isDimmed
                      ? "bg-surface-input/40 text-text-dim/40" + (isExpanded ? " cursor-pointer" : " cursor-not-allowed")
                      : `${info.color} hover:brightness-110 disabled:opacity-50`
                  }`}
                >
                  {info.label}{hasFields ? " ▾" : ""}
                </button>
              );
            })}
          </div>

          {/* Inline payload form — expands below the buttons */}
          {expandedTrigger && triggerFieldMap[expandedTrigger] && (
            <div className="mt-1.5">
              <InlinePayloadForm
                trigger={expandedTrigger}
                fields={triggerFieldMap[expandedTrigger]}
                onSubmit={(payload) => triggerMutation.mutate({ trigger: expandedTrigger, payload })}
                onCancel={() => setExpandedTrigger(null)}
                isPending={triggerMutation.isPending}
              />
            </div>
          )}
        </div>
      )}

      {triggerMutation.isError && (
        <div className="text-xs text-accent-red bg-accent-red/10 px-3 py-1.5 rounded">
          {(triggerMutation.error as Error).message}
        </div>
      )}

      <div className="flex-1">
        <div className="text-[10px] font-bold text-text-dim uppercase mb-1.5">History</div>
        <div className="space-y-1">
          {(history || []).map((h) => (
            <div key={h.id} className="flex items-center gap-2 text-xs bg-surface-input/20 rounded px-2 py-1">
              <StatusBadge state={h.from_state} />
              <span className="text-text-dim">→</span>
              <StatusBadge state={h.to_state} />
              <span className="text-text-dim ml-auto text-[10px]">
                {new Date(h.created_at).toLocaleTimeString("en-US", { hour12: false })}
              </span>
            </div>
          ))}
          {(!history || history.length === 0) && (
            <div className="text-xs text-text-dim">No transitions yet</div>
          )}
        </div>
      </div>
    </div>
  );
}
