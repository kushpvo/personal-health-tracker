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
      className="text-left w-full p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
    >
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
      <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
        {formatDate(latest_date)} · {result_count} {result_count === 1 ? "test" : "tests"}
      </p>
    </button>
  );
}
