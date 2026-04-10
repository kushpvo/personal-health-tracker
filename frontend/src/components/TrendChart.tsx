import {
  CartesianGrid,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceArea,
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

  const allValues = data.map((d) => d.value);
  const dataMin = Math.min(...allValues);
  const dataMax = Math.max(...allValues);
  const padding = (dataMax - dataMin) * 0.3 || 10;
  const yMin = Math.max(0, dataMin - padding);
  const yMax = dataMax + padding;

  const { optimal_min, optimal_max, sufficient_min, sufficient_max } = biomarker;
  const hasOptimal = optimal_min != null && optimal_max != null;
  const hasSufficient = sufficient_min != null && sufficient_max != null;

  const lowerOutOfRangeEnd = hasOptimal ? optimal_min : hasSufficient ? sufficient_min : yMin;
  const upperOutOfRangeStart = hasSufficient ? sufficient_max : hasOptimal ? optimal_max : yMax;

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
          <defs>
            <linearGradient id="chartSurfaceGlow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0b1220" />
              <stop offset="100%" stopColor="#060913" />
            </linearGradient>
            <linearGradient id="optimalBand" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#22c55e" stopOpacity="0.14" />
              <stop offset="100%" stopColor="#22c55e" stopOpacity="0.08" />
            </linearGradient>
            <linearGradient id="sufficientBand" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.08" />
            </linearGradient>
            <linearGradient id="outOfRangeBand" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#f97316" stopOpacity="0.14" />
              <stop offset="100%" stopColor="#f97316" stopOpacity="0.07" />
            </linearGradient>
          </defs>

          <ReferenceArea y1={yMin} y2={yMax} fill="url(#chartSurfaceGlow)" fillOpacity={1} />

          {lowerOutOfRangeEnd > yMin && (
            <ReferenceArea
              y1={yMin}
              y2={lowerOutOfRangeEnd}
              fill="url(#outOfRangeBand)"
              ifOverflow="extendDomain"
            />
          )}
          {hasSufficient && (
            <ReferenceArea
              y1={sufficient_min!}
              y2={sufficient_max!}
              fill="url(#sufficientBand)"
              ifOverflow="extendDomain"
            />
          )}
          {hasOptimal && (
            <ReferenceArea
              y1={optimal_min!}
              y2={optimal_max!}
              fill="url(#optimalBand)"
              ifOverflow="extendDomain"
            />
          )}
          {upperOutOfRangeStart < yMax && (
            <ReferenceArea
              y1={upperOutOfRangeStart}
              y2={yMax}
              fill="url(#outOfRangeBand)"
              ifOverflow="extendDomain"
            />
          )}

          <CartesianGrid vertical={false} stroke="rgba(148, 163, 184, 0.12)" strokeDasharray="0" />

          <XAxis
            dataKey="date"
            axisLine={{ stroke: "rgba(148, 163, 184, 0.28)" }}
            tickLine={false}
            tick={{ fontSize: 11, fill: "#7c8598" }}
            tickFormatter={(v) => formatDate(v)}
            minTickGap={60}
          />
          <YAxis
            domain={[yMin, yMax]}
            width={55}
            axisLine={{ stroke: "rgba(148, 163, 184, 0.28)" }}
            tickLine={false}
            tick={{ fontSize: 11, fill: "#7c8598" }}
          />
          <Tooltip content={<CustomTooltip />} />

          <Line
            type="monotone"
            dataKey="value"
            stroke="rgba(226, 232, 240, 0.24)"
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
