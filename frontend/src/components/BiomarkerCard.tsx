import { useNavigate } from "react-router-dom";
import type { BiomarkerSummary } from "../lib/api";
import { formatDate, zoneColor, zoneLabel } from "../lib/utils";
import type { Zone } from "../lib/utils";

interface Props {
  summary: BiomarkerSummary;
}

export default function BiomarkerCard({ summary }: Props) {
  const navigate = useNavigate();
  const { biomarker, latest_value, latest_unit, latest_date, latest_zone, result_count } = summary;
  const color = zoneColor(latest_zone as Zone);

  return (
    <button
      onClick={() => navigate(`/biomarkers/${biomarker.id}`)}
      className="relative text-left w-full p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
    >
      {summary.trend_alert && (
        <span
          title={`${summary.trend_delta !== null ? (summary.trend_delta > 0 ? "+" : "") + summary.trend_delta + "%" : "Zone changed"} from previous`}
          className="absolute top-2 right-2 flex h-2 w-2"
        >
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-orange-500" />
        </span>
      )}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wide">
            {biomarker.category}
          </p>
          <p className="font-semibold text-sm mt-0.5">{biomarker.name}</p>
        </div>
        <span
          className="text-xs px-2 py-0.5 rounded-full font-medium shrink-0"
          style={{ backgroundColor: `${color}22`, color }}
        >
          {zoneLabel(latest_zone as Zone)}
        </span>
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="text-2xl font-bold" style={{ color }}>
          {latest_value % 1 === 0 ? latest_value : latest_value.toFixed(1)}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">{latest_unit}</span>
      </div>
      {summary.trend_delta !== null && (
        <p className="text-xs mt-0.5" style={{ color: summary.trend_delta > 0 ? "#f97316" : "#22c55e" }}>
          {summary.trend_delta > 0 ? "▲" : "▼"} {Math.abs(summary.trend_delta)}% vs previous
        </p>
      )}
      <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
        {formatDate(latest_date)} · {result_count} {result_count === 1 ? "test" : "tests"}
      </p>
    </button>
  );
}
