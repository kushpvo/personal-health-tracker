import {
  CartesianGrid,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Dot,
} from "recharts";
import type { BiomarkerInfo, ResultPoint } from "../lib/api";
import { formatDate, zoneColor } from "../lib/utils";
import type { Zone } from "../lib/utils";

interface Props {
  biomarker: BiomarkerInfo;
  results: ResultPoint[];
}

interface ChartPoint {
  date: string;
  value: number;
  zone: Zone;
  reportName: string | null;
  unit: string;
}

function CustomDot(props: any) {
  const { cx, cy, payload } = props;
  const color = zoneColor(payload.zone);
  return (
    <Dot cx={cx} cy={cy} r={6} fill="#0b1020" stroke={color} strokeWidth={3} />
  );
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const p: ChartPoint = payload[0].payload;
  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 text-xs">
      <p className="font-semibold text-sm mb-1" style={{ color: zoneColor(p.zone) }}>
        {p.value} {p.unit}
      </p>
      <p className="text-gray-500 dark:text-gray-400">{formatDate(p.date)}</p>
      {p.reportName && (
        <p className="text-gray-400 dark:text-gray-500 mt-0.5">{p.reportName}</p>
      )}
    </div>
  );
}

function fmtTick(v: number): string {
  if (!isFinite(v) || Math.abs(v) > 1e6) return "";
  return parseFloat(v.toFixed(1)).toString();
}

export default function TrendChart({ biomarker, results }: Props) {
  if (results.length === 0) {
    return <p className="text-sm text-gray-400">No data points yet.</p>;
  }

  const data: ChartPoint[] = results.map((r) => ({
    date: r.sample_date ?? String(r.report_id),
    value: r.value,
    zone: r.zone as Zone,
    reportName: r.report_name,
    unit: r.unit,
  }));

  const { optimal_min, optimal_max, sufficient_min, sufficient_max } = biomarker;
  const hasOptimal = optimal_min != null && optimal_max != null;
  const hasSufficient = sufficient_min != null && sufficient_max != null;

  // Build domain from data values AND all reference range boundaries so
  // ticks are always clean numbers — no ifOverflow surprises.
  const allBoundaries: number[] = [
    ...data.map((d) => d.value),
    ...(hasOptimal ? [optimal_min!, optimal_max!] : []),
    ...(hasSufficient ? [sufficient_min!, sufficient_max!] : []),
  ];
  const rawMin = Math.min(...allBoundaries);
  const rawMax = Math.max(...allBoundaries);
  const padding = (rawMax - rawMin) * 0.25 || 5;
  const yMin = Math.max(0, rawMin - padding);
  const yMax = rawMax + padding;

  // Zone band boundaries
  const lowerOorEnd   = hasOptimal ? optimal_min! : hasSufficient ? sufficient_min! : yMin;
  const upperOorStart = hasSufficient ? sufficient_max! : hasOptimal ? optimal_max! : yMax;

  // Boundary lines to draw (between zones)
  const boundaryLines: { y: number; color: string }[] = [];
  if (hasOptimal) {
    boundaryLines.push({ y: optimal_min!, color: "#22c55e" });
    boundaryLines.push({ y: optimal_max!, color: "#22c55e" });
  }
  if (hasSufficient) {
    boundaryLines.push({ y: sufficient_min!, color: "#06b6d4" });
    boundaryLines.push({ y: sufficient_max!, color: "#06b6d4" });
  }

  return (
    <div className="rounded-[28px] border border-slate-800/80 bg-[#050914] px-4 py-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
      {/* Legend */}
      <div className="mb-4 flex flex-wrap items-center gap-3 text-xs">
        {(
          [
            { zone: "optimal" as Zone, label: "Optimal" },
            { zone: "sufficient" as Zone, label: "Sufficient" },
            { zone: "out_of_range" as Zone, label: "Out of Range" },
          ] as const
        ).map(({ zone, label }) => (
          <span
            key={zone}
            className="flex items-center gap-2 rounded-full border border-white/6 bg-white/[0.03] px-3 py-1.5 text-slate-200"
          >
            <span
              className="h-2.5 w-2.5 rounded-full border-2"
              style={{ borderColor: zoneColor(zone), boxShadow: `0 0 12px ${zoneColor(zone)}55` }}
            />
            {label}
          </span>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 12, right: 24, left: 4, bottom: 8 }}>

          {/* Zone bands — solid fills, no horizontal gradient */}
          {lowerOorEnd > yMin && (
            <ReferenceArea
              y1={yMin} y2={lowerOorEnd}
              fill="#f97316" fillOpacity={0.07}
              stroke="none"
            />
          )}
          {hasSufficient && (
            <ReferenceArea
              y1={sufficient_min!} y2={sufficient_max!}
              fill="#06b6d4" fillOpacity={0.10}
              stroke="none"
            />
          )}
          {hasOptimal && (
            <ReferenceArea
              y1={optimal_min!} y2={optimal_max!}
              fill="#22c55e" fillOpacity={0.12}
              stroke="none"
            />
          )}
          {upperOorStart < yMax && (
            <ReferenceArea
              y1={upperOorStart} y2={yMax}
              fill="#f97316" fillOpacity={0.07}
              stroke="none"
            />
          )}

          {/* Thin boundary lines at zone edges */}
          {boundaryLines.map(({ y, color }) => (
            <ReferenceLine
              key={`${y}-${color}`}
              y={y}
              stroke={color}
              strokeOpacity={0.35}
              strokeWidth={1}
              strokeDasharray="4 3"
            />
          ))}

          <CartesianGrid vertical={false} stroke="rgba(148, 163, 184, 0.08)" strokeDasharray="0" />

          <XAxis
            dataKey="date"
            axisLine={{ stroke: "rgba(148, 163, 184, 0.2)" }}
            tickLine={false}
            tick={{ fontSize: 11, fill: "#7c8598" }}
            tickFormatter={(v) => formatDate(v)}
            minTickGap={60}
          />
          <YAxis
            domain={[yMin, yMax]}
            width={55}
            axisLine={{ stroke: "rgba(148, 163, 184, 0.2)" }}
            tickLine={false}
            tick={{ fontSize: 11, fill: "#7c8598" }}
            tickFormatter={fmtTick}
          />
          <Tooltip content={<CustomTooltip />} />

          <Line
            type="monotone"
            dataKey="value"
            stroke="rgba(226, 232, 240, 0.3)"
            strokeWidth={2}
            dot={<CustomDot />}
            activeDot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
