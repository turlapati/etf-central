import { useState, useRef, useCallback, useEffect } from "react";
import { TICKERS, METHODS, BASKET_TYPES } from "../lib/constants";
import { useClock } from "../hooks/useClock";

interface Props {
  onSubmit: (order: OrderFormData) => void;
  isSubmitting: boolean;
}

export interface OrderFormData {
  action: "CREATE" | "REDEEM";
  ticker: string;
  units: number;
  unit_size: number;
  method: string;
  basket_type: string;
}

/* ── Token aliases for natural language parsing ── */

const ACTION_ALIASES: Record<string, "CREATE" | "REDEEM"> = {
  create: "CREATE", c: "CREATE", buy: "CREATE", cr: "CREATE",
  redeem: "REDEEM", r: "REDEEM", sell: "REDEEM", rd: "REDEEM",
};

const TICKER_SET = new Set(TICKERS.map((t) => t.toLowerCase()));

const METHOD_ALIASES: Record<string, string> = {
  cash: "Cash", c: "Cash", "$": "Cash",
  "in-kind": "In-Kind", inkind: "In-Kind", ik: "In-Kind", kind: "In-Kind", k: "In-Kind",
};

const BASKET_ALIASES: Record<string, string> = {
  standard: "Standard", std: "Standard", s: "Standard",
  custom: "Custom", cust: "Custom", cus: "Custom",
};

function parseUnitSize(token: string): number | null {
  const cleaned = token.replace(/,/g, "").toLowerCase();
  const match = cleaned.match(/^(\d+(?:\.\d+)?)(k|m)?$/);
  if (!match) return null;
  const num = parseFloat(match[1]);
  const suffix = match[2];
  if (suffix === "k") return num * 1000;
  if (suffix === "m") return num * 1000000;
  return num;
}

interface ParsedFields {
  action?: "CREATE" | "REDEEM";
  ticker?: string;
  units?: number;
  unit_size?: number;
  method?: string;
  basket_type?: string;
}

function parseCommand(input: string): ParsedFields {
  const tokens = input.trim().split(/\s+/).filter(Boolean);
  const result: ParsedFields = {};
  const unmatched: string[] = [];

  for (const raw of tokens) {
    const t = raw.toLowerCase();

    if (!result.action && ACTION_ALIASES[t]) {
      result.action = ACTION_ALIASES[t];
    } else if (!result.ticker && TICKER_SET.has(t)) {
      result.ticker = t.toUpperCase();
    } else if (!result.method && METHOD_ALIASES[t]) {
      result.method = METHOD_ALIASES[t];
    } else if (!result.basket_type && BASKET_ALIASES[t]) {
      result.basket_type = BASKET_ALIASES[t];
    } else {
      unmatched.push(raw);
    }
  }

  // Assign unmatched numbers: first = units, second = unit_size
  const nums = unmatched.map((u) => parseUnitSize(u)).filter((n): n is number => n !== null);
  if (nums.length >= 1) result.units = nums[0];
  if (nums.length >= 2) result.unit_size = nums[1];

  return result;
}

/* ── Hint / ghost text logic ── */

const FIELD_ORDER = ["action", "ticker", "units", "unit_size", "method", "basket_type"] as const;
const FIELD_HINTS: Record<string, string> = {
  action: "CREATE or REDEEM",
  ticker: "ticker (SPY, QQQ...)",
  units: "units",
  unit_size: "unit size (50k)",
  method: "cash or in-kind",
  basket_type: "std or custom",
};

function getHint(parsed: ParsedFields): string {
  for (const f of FIELD_ORDER) {
    if (!parsed[f]) return FIELD_HINTS[f];
  }
  return "ready — press Enter";
}

/* ── Suggestion dropdown items ── */

interface Suggestion {
  label: string;
  insert: string;
  category: string;
}

function getSuggestions(input: string, parsed: ParsedFields): Suggestion[] {
  const lastToken = input.trim().split(/\s+/).pop()?.toLowerCase() || "";
  const suggestions: Suggestion[] = [];

  if (!parsed.action) {
    for (const [alias, val] of Object.entries(ACTION_ALIASES)) {
      if (alias.length > 1 && alias.startsWith(lastToken)) {
        suggestions.push({ label: val, insert: val, category: "Action" });
      }
    }
    // dedupe
    const seen = new Set<string>();
    return suggestions.filter((s) => { if (seen.has(s.label)) return false; seen.add(s.label); return true; });
  }

  if (!parsed.ticker) {
    for (const t of TICKERS) {
      if (t.toLowerCase().startsWith(lastToken)) {
        suggestions.push({ label: t, insert: t, category: "Ticker" });
      }
    }
    return suggestions.slice(0, 6);
  }

  if (!parsed.method) {
    for (const m of METHODS) {
      if (m.toLowerCase().startsWith(lastToken)) {
        suggestions.push({ label: m, insert: m, category: "Method" });
      }
    }
  }

  if (!parsed.basket_type) {
    for (const b of BASKET_TYPES) {
      if (b.toLowerCase().startsWith(lastToken)) {
        suggestions.push({ label: b, insert: b, category: "Basket" });
      }
    }
  }

  return suggestions.slice(0, 6);
}

/* ── Component ── */

const SETTLEMENT_PERIODS = ["T+1", "T+2", "T+3"];
const SETTLEMENT_METHODS = ["DVP", "RVP", "FOP"];
const TRANSFER_AGENTS = ["BNY Mellon", "State Street", "Computershare"];
const CLEARING_SETTLEMENTS = ["NSCC", "DTC", "Euroclear"];
const BOOK_ENTRIES = ["DTC", "Physical", "Fed Book-Entry"];

export default function OrderEntryPanel({ onSubmit, isSubmitting }: Props) {
  const [action, setAction] = useState<"CREATE" | "REDEEM">("CREATE");
  const [ticker, setTicker] = useState("IWM");
  const [units, setUnits] = useState("1000");
  const [unitSize, setUnitSize] = useState("50000");
  const [method, setMethod] = useState("Cash");
  const [basketType, setBasketType] = useState("Standard");
  const [settlementPeriod, setSettlementPeriod] = useState("T+1");
  const [settlementMethod, setSettlementMethod] = useState("DVP");
  const [transferAgent, setTransferAgent] = useState("BNY Mellon");
  const [clearingSettlement, setClearingSettlement] = useState("NSCC");
  const [bookEntry, setBookEntry] = useState("DTC");
  const { time12: stageTime } = useClock();

  const [cmdInput, setCmdInput] = useState("");
  const [cmdFocused, setCmdFocused] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);

  const parsed = parseCommand(cmdInput);
  const hint = getHint(parsed);
  const suggestions = cmdFocused && cmdInput.trim() ? getSuggestions(cmdInput, parsed) : [];

  // Sync parsed fields into form state in real time
  useEffect(() => {
    if (!cmdInput.trim()) return;
    if (parsed.action) setAction(parsed.action);
    if (parsed.ticker) setTicker(parsed.ticker);
    if (parsed.units !== undefined) setUnits(String(parsed.units));
    if (parsed.unit_size !== undefined) setUnitSize(String(parsed.unit_size));
    if (parsed.method) setMethod(parsed.method);
    if (parsed.basket_type) setBasketType(parsed.basket_type);
  }, [cmdInput, parsed.action, parsed.ticker, parsed.units, parsed.unit_size, parsed.method, parsed.basket_type]);

  const shares = (parseInt(units.replace(/,/g, "")) || 0) * (parseInt(unitSize.replace(/,/g, "")) || 0);
  const totalValue = shares * 210.34;

  const applySuggestion = useCallback((s: Suggestion) => {
    const tokens = cmdInput.trim().split(/\s+/);
    tokens[tokens.length - 1] = s.insert;
    setCmdInput(tokens.join(" ") + " ");
    setSelectedIdx(-1);
    inputRef.current?.focus();
  }, [cmdInput]);

  function handleSubmit() {
    onSubmit({
      action,
      ticker,
      units: parseInt(units.replace(/,/g, "")) || 0,
      unit_size: parseInt(unitSize.replace(/,/g, "")) || 0,
      method,
      basket_type: basketType,
    });
    setCmdInput("");
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, -1));
    } else if (e.key === "Tab" && suggestions.length > 0) {
      e.preventDefault();
      applySuggestion(suggestions[Math.max(selectedIdx, 0)]);
    } else if (e.key === "Enter") {
      if (selectedIdx >= 0 && suggestions[selectedIdx]) {
        e.preventDefault();
        applySuggestion(suggestions[selectedIdx]);
      } else {
        e.preventDefault();
        handleSubmit();
      }
    } else if (e.key === "Escape") {
      setCmdInput("");
      setSelectedIdx(-1);
    }
  }

  // Which fields have been resolved from the command bar
  const resolved = {
    action: !!parsed.action,
    ticker: !!parsed.ticker,
    units: parsed.units !== undefined,
    unit_size: parsed.unit_size !== undefined,
    method: !!parsed.method,
    basket_type: !!parsed.basket_type,
  };

  const highlightRing = (field: keyof typeof resolved) =>
    resolved[field] && cmdInput.trim()
      ? "ring-1 ring-accent-blue/40"
      : "";

  return (
    <aside className="w-72 flex flex-col bg-surface-panel glass rounded-lg border border-border-subtle shrink-0 overflow-hidden">
      {/* Scrollable form area */}
      <div className="flex-1 overflow-y-auto thin-scrollbar p-3 flex flex-col gap-1.5">
        <h2 className="font-extrabold text-xs uppercase tracking-tight text-white mb-0.5">New Order</h2>

        {/* ── Command Bar ── */}
        <div className="relative">
          <div className="flex items-center bg-surface-input border border-border-subtle rounded-md px-2 py-1 gap-1.5 focus-within:border-accent-blue/50 transition-colors">
            <span className="text-accent-blue text-xs font-bold select-none">&gt;</span>
            <input
              ref={inputRef}
              type="text"
              value={cmdInput}
              onChange={(e) => { setCmdInput(e.target.value); setSelectedIdx(-1); }}
              onFocus={() => setCmdFocused(true)}
              onBlur={() => setTimeout(() => setCmdFocused(false), 150)}
              onKeyDown={handleKeyDown}
              placeholder={hint}
              className="bg-transparent flex-1 text-xs text-white outline-none placeholder:text-text-dim/50"
              spellCheck={false}
              autoComplete="off"
            />
          </div>
          {cmdInput.trim() && (
            <div className="flex flex-wrap gap-1 mt-1">
              {parsed.action && (
                <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${parsed.action === "CREATE" ? "bg-accent-green/15 text-accent-green" : "bg-accent-red/15 text-accent-red"}`}>
                  {parsed.action}
                </span>
              )}
              {parsed.ticker && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent-blue/15 text-accent-blue font-bold">{parsed.ticker}</span>
              )}
              {parsed.units !== undefined && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-white/70 font-medium">{parsed.units}u</span>
              )}
              {parsed.unit_size !== undefined && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-white/70 font-medium">{parsed.unit_size.toLocaleString()}/u</span>
              )}
              {parsed.method && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-white/70 font-medium">{parsed.method}</span>
              )}
              {parsed.basket_type && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-white/70 font-medium">{parsed.basket_type}</span>
              )}
            </div>
          )}

          {/* Suggestions dropdown */}
          {cmdFocused && suggestions.length > 0 && (
            <div className="absolute z-50 left-0 right-0 top-full mt-1 bg-[#1a222c] border border-border-subtle rounded-md shadow-xl overflow-hidden">
              {suggestions.map((s, i) => (
                <button
                  key={`${s.category}-${s.label}`}
                  onMouseDown={(e) => { e.preventDefault(); applySuggestion(s); }}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 text-xs transition-colors ${
                    i === selectedIdx
                      ? "bg-accent-blue/15 text-white"
                      : "text-white/80 hover:bg-white/5"
                  }`}
                >
                  <span className="font-medium">{s.label}</span>
                  <span className="text-[9px] text-text-dim">{s.category}</span>
                </button>
              ))}
              <div className="px-2.5 py-1 border-t border-border-subtle">
                <span className="text-[9px] text-text-dim">Tab to complete &middot; Enter to submit &middot; Esc to clear</span>
              </div>
            </div>
          )}
        </div>

        {/* ── Traditional Form ── */}
        <div className="flex gap-1.5">
          <button
            onClick={() => setAction("CREATE")}
            className={`flex-1 py-1.5 rounded font-bold text-xs border transition-all ${highlightRing("action")} ${
              action === "CREATE"
                ? "bg-accent-green/15 text-accent-green border-accent-green/30"
                : "bg-surface-input text-text-dim border-border-subtle hover:bg-surface-input/80"
            }`}
          >
            Create
          </button>
          <button
            onClick={() => setAction("REDEEM")}
            className={`flex-1 py-1.5 rounded font-bold text-xs border transition-all ${highlightRing("action")} ${
              action === "REDEEM"
                ? "bg-accent-red/15 text-accent-red border-accent-red/30"
                : "bg-surface-input text-text-dim border-border-subtle hover:bg-surface-input/80"
            }`}
          >
            Redeem
          </button>
        </div>

        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-1.5">
            <div className="flex flex-col gap-0.5">
              <label className="text-[10px] font-extrabold text-white uppercase">ETF Ticker</label>
              <select
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className={`bg-surface-input border border-border-subtle rounded px-2 text-xs outline-none ${highlightRing("ticker")}`}
              >
                {TICKERS.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-0.5">
              <label className="text-[10px] font-extrabold text-white uppercase">Units</label>
              <input
                className={`bg-surface-input border border-border-subtle rounded px-2 text-xs outline-none ${highlightRing("units")}`}
                type="text"
                value={units}
                onChange={(e) => setUnits(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            <div className="flex flex-col gap-0.5">
              <label className="text-[10px] font-extrabold text-white uppercase">Unit Size</label>
              <input
                className={`bg-surface-input border border-border-subtle rounded px-2 text-xs outline-none ${highlightRing("unit_size")}`}
                type="text"
                value={unitSize}
                onChange={(e) => setUnitSize(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-0.5">
              <label className="text-[10px] font-extrabold text-white uppercase">Shares</label>
              <input
                className="bg-surface-input border border-border-subtle rounded px-2 text-xs outline-none"
                type="text"
                value={shares.toLocaleString()}
                readOnly
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            <div className="flex flex-col gap-0.5">
              <label className="text-[10px] font-extrabold text-white uppercase">Method</label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                className={`bg-surface-input border border-border-subtle rounded px-2 text-xs outline-none ${highlightRing("method")}`}
              >
                <option value="Cash">Cash</option>
                <option value="In-Kind" disabled className="text-text-dim">In-Kind</option>
                <option value="Hybrid" disabled className="text-text-dim">Hybrid</option>
              </select>
            </div>
            <div className="flex flex-col gap-0.5">
              <label className="text-[10px] font-extrabold text-white uppercase">Basket Type</label>
              <select
                value={basketType}
                onChange={(e) => setBasketType(e.target.value)}
                className={`bg-surface-input border border-border-subtle rounded px-2 text-xs outline-none ${highlightRing("basket_type")}`}
              >
                {BASKET_TYPES.map((b) => (
                  <option key={b}>{b}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            <div className="flex flex-col gap-0.5">
              <label className="text-[10px] font-extrabold text-white uppercase">Stage Time</label>
              <input
                className="bg-surface-input border border-border-subtle rounded px-2 text-xs outline-none"
                type="text"
                value={stageTime}
                readOnly
              />
            </div>
            <div className="flex flex-col gap-0.5">
              <label className="text-[10px] font-extrabold text-white uppercase">Total Value</label>
              <input
                className="bg-surface-input border border-border-subtle rounded px-1.5 text-[11px] text-accent-blue font-bold outline-none"
                readOnly
                type="text"
                value={`$${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                title={`$${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2 })}`}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            <div className="flex flex-col gap-0.5">
              <label className="text-[10px] font-extrabold text-white uppercase">Transfer Agent</label>
              <select
                value={transferAgent}
                onChange={(e) => setTransferAgent(e.target.value)}
                className="bg-surface-input border border-border-subtle rounded px-2 text-xs outline-none"
              >
                {TRANSFER_AGENTS.map((a) => (
                  <option key={a}>{a}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-0.5">
              <label className="text-[10px] font-extrabold text-white uppercase">Clearing Settlement</label>
              <select
                value={clearingSettlement}
                onChange={(e) => setClearingSettlement(e.target.value)}
                className="bg-surface-input border border-border-subtle rounded px-2 text-xs outline-none"
              >
                {CLEARING_SETTLEMENTS.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            <div className="flex flex-col gap-0.5">
              <label className="text-[10px] font-extrabold text-white uppercase">Settlement Period</label>
              <select
                value={settlementPeriod}
                onChange={(e) => setSettlementPeriod(e.target.value)}
                className="bg-surface-input border border-border-subtle rounded px-2 text-xs outline-none"
              >
                {SETTLEMENT_PERIODS.map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-0.5">
              <label className="text-[10px] font-extrabold text-white uppercase">Settlement Method</label>
              <select
                value={settlementMethod}
                onChange={(e) => setSettlementMethod(e.target.value)}
                className="bg-surface-input border border-border-subtle rounded px-2 text-xs outline-none"
              >
                {SETTLEMENT_METHODS.map((m) => (
                  <option key={m}>{m}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-extrabold text-white uppercase">Book Entry</label>
            <select
              value={bookEntry}
              onChange={(e) => setBookEntry(e.target.value)}
              className="bg-surface-input border border-border-subtle rounded px-2 text-xs outline-none"
            >
              {BOOK_ENTRIES.map((b) => (
                <option key={b}>{b}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Pinned submit button */}
      <div className="p-3 pt-2 shrink-0">
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className={`w-full font-extrabold py-2.5 rounded shadow-lg hover:brightness-110 active:scale-[0.98] transition-all text-xs tracking-wider ${
            action === "CREATE"
              ? "bg-accent-green text-bg-main shadow-accent-green/10"
              : "bg-accent-red text-white shadow-accent-red/10"
          } disabled:opacity-50`}
        >
          {isSubmitting ? "SUBMITTING..." : `Submit ${action === "CREATE" ? "Create" : "Redeem"} Order`}
        </button>
      </div>
    </aside>
  );
}
