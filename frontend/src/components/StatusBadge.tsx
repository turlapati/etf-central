import { STATE_DISPLAY } from "../lib/constants";

export default function StatusBadge({ state }: { state: string }) {
  const display = STATE_DISPLAY[state] ?? { label: state, color: "text-text-dim" };
  return <span className={`${display.color} font-bold`}>{display.label}</span>;
}
