import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { api } from "../lib/api";
import TrendChart from "../components/TrendChart";
import { formatDate, zoneColor, zoneLabel } from "../lib/utils";
import type { Zone } from "../lib/utils";

export default function BiomarkerDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const biomarkerId = Number(id);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["biomarker", biomarkerId],
    queryFn: () => api.biomarkers.detail(biomarkerId),
    enabled: !isNaN(biomarkerId),
  });

  if (isLoading) return <p className="text-sm text-gray-500">Loading…</p>;
  if (isError || !data) return <p className="text-sm text-red-500">Failed to load biomarker.</p>;

  const { biomarker, results } = data;
  const latest = results[results.length - 1];

  return (
    <div className="max-w-3xl">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 dark:hover:text-white mb-6"
      >
        <ArrowLeft size={15} /> Back
      </button>

      <div className="mb-6">
        <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-1">
          {biomarker.category}
        </p>
        <h2 className="text-2xl font-bold">{biomarker.name}</h2>
        {latest && (
          <div className="flex items-baseline gap-2 mt-3">
            <span
              className="text-4xl font-bold"
              style={{ color: zoneColor(latest.zone as Zone) }}
            >
              {latest.value % 1 === 0 ? latest.value : latest.value.toFixed(2)}
            </span>
            <span className="text-gray-500 dark:text-gray-400 text-sm">{latest.unit}</span>
            <span
              className="text-xs px-2 py-0.5 rounded-full font-medium ml-1"
              style={{
                backgroundColor: `${zoneColor(latest.zone as Zone)}22`,
                color: zoneColor(latest.zone as Zone),
              }}
            >
              {zoneLabel(latest.zone as Zone)}
            </span>
          </div>
        )}
      </div>

      {/* Reference ranges */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
          <p className="text-xs text-gray-500 mb-0.5">Optimal range</p>
          <p className="text-sm font-medium">
            {biomarker.optimal_min} – {biomarker.optimal_max}{" "}
            <span className="text-gray-400">{biomarker.default_unit}</span>
          </p>
        </div>
        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
          <p className="text-xs text-gray-500 mb-0.5">Sufficient range</p>
          <p className="text-sm font-medium">
            {biomarker.sufficient_min} – {biomarker.sufficient_max}{" "}
            <span className="text-gray-400">{biomarker.default_unit}</span>
          </p>
        </div>
      </div>

      {/* Trend chart */}
      <div className="mb-8">
        <TrendChart biomarker={biomarker} results={results} />
      </div>

      {/* History table */}
      <h3 className="text-sm font-semibold mb-3">History</h3>
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Value</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Zone</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Report</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {[...results].reverse().map((r) => (
              <tr key={r.id} className="bg-white dark:bg-gray-950">
                <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                  {formatDate(r.sample_date)}
                </td>
                <td className="px-4 py-3 font-medium">
                  {r.value % 1 === 0 ? r.value : r.value.toFixed(2)} {r.unit}
                </td>
                <td className="px-4 py-3">
                  <span
                    className="text-xs px-2 py-0.5 rounded-full font-medium"
                    style={{
                      backgroundColor: `${zoneColor(r.zone as Zone)}22`,
                      color: zoneColor(r.zone as Zone),
                    }}
                  >
                    {zoneLabel(r.zone as Zone)}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs truncate max-w-[200px]">
                  {r.report_name ?? `Report #${r.report_id}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
