import { STATE_DISPLAY } from "../lib/constants";

export default function StatusBadge({ state }: { state: string }) {
  const display = STATE_DISPLAY[state] ?? { label: state, color: "text-text-dim", bg: "bg-white/10" };
  return (
    <span className={`${display.color} ${display.bg} font-bold text-[10px] px-2.5 py-0.5 rounded-full inline-block`}>
      {display.label}
    </span>
  );
}
