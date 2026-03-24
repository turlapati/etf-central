import { useClock } from "../hooks/useClock";

interface Props {
  connected: boolean;
  latencyMs: number;
}

export default function StatusBar({ connected, latencyMs }: Props) {
  const { time, date } = useClock();

  return (
    <footer className="h-6 bg-surface-panel glass border-t border-border-subtle flex items-center px-3 justify-between text-[11px] text-text-dim shrink-0">
      <div className="flex gap-4">
        <span className="flex items-center gap-1.5">
          <span
            className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-accent-green animate-pulse" : "bg-accent-red"}`}
          />
          {connected ? "TRIDENT CONNECTED" : "DISCONNECTED"}
        </span>
        <span>LATENCY: {latencyMs}ms</span>
      </div>
      <div className="flex gap-5 items-center">
        <span className="font-bold text-text-primary uppercase tracking-tight">Units: Shares</span>
        <span className="tabular-nums">{time}</span>
        <span className="font-black text-accent-blue tabular-nums tracking-widest uppercase">{date}</span>
      </div>
    </footer>
  );
}
