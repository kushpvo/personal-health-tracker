import {
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
    <Dot cx={cx} cy={cy} r={6} fill="transparent" stroke={color} strokeWidth={2.5} />
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

  return (
    <div>
      {/* Legend */}
      <div className="flex items-center gap-5 mb-4 text-xs">
        {(
          [
            { zone: "optimal" as Zone, label: "Optimal" },
            { zone: "sufficient" as Zone, label: "Sufficient" },
            { zone: "out_of_range" as Zone, label: "Out of Range" },
          ] as const
        ).map(({ zone, label }) => (
          <span key={zone} className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-full border-2"
              style={{ borderColor: zoneColor(zone) }}
            />
            {label}
          </span>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 8, right: 24, left: 0, bottom: 8 }}>
          {/* Zone bands */}
          {sufficient_min != null && sufficient_max != null && (
            <ReferenceArea
              y1={sufficient_min}
              y2={sufficient_max}
              fill={zoneColor("sufficient")}
              fillOpacity={0.08}
            />
          )}
          {optimal_min != null && optimal_max != null && (
            <ReferenceArea
              y1={optimal_min}
              y2={optimal_max}
              fill={zoneColor("optimal")}
              fillOpacity={0.12}
            />
          )}

          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            tickFormatter={(v) => formatDate(v)}
            minTickGap={60}
          />
          <YAxis domain={[yMin, yMax]} tick={{ fontSize: 11 }} width={55} />
          <Tooltip content={<CustomTooltip />} />

          <Line
            type="monotone"
            dataKey="value"
            stroke="#94a3b8"
            strokeWidth={1.5}
            dot={<CustomDot />}
            activeDot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
