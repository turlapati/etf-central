import { useMemo } from "react";
import {
  AreaChart,
  Area,
  ComposedChart,
  Bar,
  LineChart,
  Line,
  ResponsiveContainer,
  XAxis,
  YAxis,
  ReferenceLine,
  Tooltip,
} from "recharts";

const DATES = [
  "Jan 1", "Jan 8", "Jan 15", "Jan 22",
  "Feb 5", "Feb 12", "Feb 20", "Feb 26", "Mar 5",
];

function generatePremiumDiscount() {
  return DATES.map((date, i) => ({
    date,
    value: +(
      Math.sin(i * 0.9) * 0.28 +
      Math.cos(i * 0.5) * 0.12 +
      Math.sin(i * 1.8) * 0.06
    ).toFixed(2),
  }));
}

function generateShortInterest() {
  return DATES.map((date, i) => ({
    date,
    value: +(4.2 + Math.sin(i * 0.3) * 0.4 + i * 0.18 + Math.cos(i * 0.8) * 0.2).toFixed(1),
    trend: +(0.2 + i * 0.08 + Math.sin(i * 0.5) * 0.1).toFixed(2),
  }));
}

function generateSpreadVolume() {
  return DATES.map((date, i) => ({
    date,
    volume: Math.round(150000 + Math.sin(i * 0.5) * 200000 + i * 50000 + Math.cos(i * 0.8) * 80000),
    spread: +(0.03 + Math.sin(i * 0.6) * 0.04 + i * 0.008 + Math.cos(i * 1.1) * 0.015).toFixed(3),
  }));
}

function generateSharesOutstanding() {
  return DATES.map((date, i) => ({
    date,
    value: +(102.5 + i * 0.25 + Math.sin(i * 0.4) * 0.3 + Math.cos(i * 0.9) * 0.15).toFixed(1),
  }));
}

const AXIS_TICK = { fontSize: 9, fill: "#8a94a6" };
const AXIS_LABEL_STYLE = { fontSize: 9, fill: "#8a94a6" };

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1">
      <span className="inline-block w-2.5 h-2.5 rounded-[2px]" style={{ backgroundColor: color }} />
      <span className="text-[9px] text-white/70">{label}</span>
    </span>
  );
}

function ChartPanel({
  title,
  badge,
  legend,
  children,
}: {
  title: string;
  badge: string;
  legend: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-surface-panel glass rounded-lg border border-border-subtle p-2.5 flex flex-col">
      <div className="flex justify-between items-center mb-0.5">
        <h3 className="font-bold text-[12px] text-white tracking-wide">{title}</h3>
        <span className="text-[9px] bg-surface-input px-1.5 py-0.5 rounded border border-border-subtle text-white/60">
          {badge}
        </span>
      </div>
      <div className="flex items-center gap-3 mb-1">{legend}</div>
      <div className="flex-1 min-h-0">{children}</div>
    </div>
  );
}

export default function MarketColorRow() {
  const premiumData = useMemo(generatePremiumDiscount, []);
  const shortData = useMemo(generateShortInterest, []);
  const spreadData = useMemo(generateSpreadVolume, []);
  const outData = useMemo(generateSharesOutstanding, []);

  return (
    <div className="grid grid-cols-4 gap-1.5 shrink-0">
      {/* ── Premium / Discount ── */}
      <ChartPanel
        title="ETF Premium / Discount"
        badge="Real-time / Daily"
        legend={<LegendItem color="#f59e0b" label="Premium / Discount ($)" />}
      >
        <ResponsiveContainer width="100%" height={148}>
          <LineChart data={premiumData} margin={{ top: 4, right: 4, bottom: 2, left: -8 }}>
            <XAxis
              dataKey="date"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={{ stroke: "#1e293b" }}
              interval={0}
              angle={-40}
              textAnchor="end"
              height={32}
            />
            <YAxis
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              width={30}
              tickFormatter={(v: number) => v.toFixed(1)}
              label={{ value: "Premium/Discount ($)", angle: -90, position: "insideLeft", ...AXIS_LABEL_STYLE, dx: 6 }}
            />
            <ReferenceLine y={0} stroke="#334155" strokeDasharray="3 3" />
            <Tooltip
              contentStyle={{ background: "#141a21", border: "1px solid #1e293b", borderRadius: 6, fontSize: 10 }}
              labelStyle={{ color: "#8a94a6" }}
              formatter={(v: number) => [`$${v.toFixed(2)}`, "P/D"]}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={{ r: 2.5, fill: "#f59e0b", stroke: "#f59e0b" }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartPanel>

      {/* ── Short Interest ── */}
      <ChartPanel
        title="ETF Short Interest"
        badge="Weekly"
        legend={<LegendItem color="#42a5f5" label="Short Interest (%)" />}
      >
        <ResponsiveContainer width="100%" height={148}>
          <AreaChart data={shortData} margin={{ top: 4, right: 4, bottom: 2, left: -8 }}>
            <defs>
              <linearGradient id="grad-short" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#42a5f5" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#42a5f5" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={{ stroke: "#1e293b" }}
              interval={0}
              angle={-40}
              textAnchor="end"
              height={32}
            />
            <YAxis
              yAxisId="left"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              width={30}
              domain={["dataMin - 0.5", "dataMax + 0.5"]}
              tickFormatter={(v: number) => v.toFixed(1)}
              label={{ value: "Short Interest (%)", angle: -90, position: "insideLeft", ...AXIS_LABEL_STYLE, dx: 6 }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              width={24}
              domain={[0, 1]}
              tickFormatter={(v: number) => v.toFixed(1)}
            />
            <Tooltip
              contentStyle={{ background: "#141a21", border: "1px solid #1e293b", borderRadius: 6, fontSize: 10 }}
              labelStyle={{ color: "#8a94a6" }}
              formatter={(v: number, name: string) => [name === "value" ? `${v}%` : v.toFixed(2), name === "value" ? "SI" : "Trend"]}
            />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="value"
              stroke="#42a5f5"
              strokeWidth={2}
              fill="url(#grad-short)"
              dot={{ r: 2, fill: "#42a5f5", stroke: "#42a5f5" }}
              isAnimationActive={false}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="trend"
              stroke="#80d8ff"
              strokeWidth={1.5}
              strokeDasharray="4 2"
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </ChartPanel>

      {/* ── Bid/Ask Spread & Volume ── */}
      <ChartPanel
        title="Bid/Ask Spread & Volume"
        badge="Dual Axis"
        legend={
          <>
            <LegendItem color="#64748b" label="Volume" />
            <LegendItem color="#22d3ee" label="Spread ($)" />
          </>
        }
      >
        <ResponsiveContainer width="100%" height={148}>
          <ComposedChart data={spreadData} margin={{ top: 4, right: 4, bottom: 2, left: -4 }}>
            <XAxis
              dataKey="date"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={{ stroke: "#1e293b" }}
              interval={0}
              angle={-40}
              textAnchor="end"
              height={32}
            />
            <YAxis
              yAxisId="left"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              width={34}
              tickFormatter={(v: number) => v >= 1000 ? `${Math.round(v / 1000)}k` : `${v}`}
              label={{ value: "Volume", angle: -90, position: "insideLeft", ...AXIS_LABEL_STYLE, dx: 8 }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              width={34}
              tickFormatter={(v: number) => `$${v.toFixed(2)}`}
              label={{ value: "Spread ($)", angle: 90, position: "insideRight", ...AXIS_LABEL_STYLE, dx: -8 }}
            />
            <Tooltip
              contentStyle={{ background: "#141a21", border: "1px solid #1e293b", borderRadius: 6, fontSize: 10 }}
              labelStyle={{ color: "#8a94a6" }}
              formatter={(v: number, name: string) => [name === "volume" ? v.toLocaleString() : `$${v.toFixed(3)}`, name === "volume" ? "Vol" : "Spread"]}
            />
            <Bar
              yAxisId="left"
              dataKey="volume"
              fill="#64748b"
              opacity={0.5}
              radius={[2, 2, 0, 0]}
              isAnimationActive={false}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="spread"
              stroke="#22d3ee"
              strokeWidth={2}
              dot={{ r: 2, fill: "#22d3ee", stroke: "#22d3ee" }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </ChartPanel>

      {/* ── Shares Outstanding ── */}
      <ChartPanel
        title="Shares Outstanding"
        badge="Longitudinal"
        legend={<LegendItem color="#00e676" label="Shares (M)" />}
      >
        <ResponsiveContainer width="100%" height={148}>
          <AreaChart data={outData} margin={{ top: 4, right: 4, bottom: 2, left: -8 }}>
            <defs>
              <linearGradient id="grad-outstanding" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00e676" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#00e676" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={{ stroke: "#1e293b" }}
              interval={0}
              angle={-40}
              textAnchor="end"
              height={32}
            />
            <YAxis
              yAxisId="left"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              width={30}
              domain={["dataMin - 0.5", "dataMax + 0.5"]}
              tickFormatter={(v: number) => v.toFixed(1)}
              label={{ value: "Shares (M)", angle: -90, position: "insideLeft", ...AXIS_LABEL_STYLE, dx: 6 }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              width={24}
              domain={[0, 1]}
              tickFormatter={(v: number) => v.toFixed(1)}
            />
            <Tooltip
              contentStyle={{ background: "#141a21", border: "1px solid #1e293b", borderRadius: 6, fontSize: 10 }}
              labelStyle={{ color: "#8a94a6" }}
              formatter={(v: number) => [`${v.toFixed(1)}M`, "Shares"]}
            />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="value"
              stroke="#00e676"
              strokeWidth={2}
              fill="url(#grad-outstanding)"
              dot={{ r: 2, fill: "#00e676", stroke: "#00e676" }}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </ChartPanel>
    </div>
  );
}
