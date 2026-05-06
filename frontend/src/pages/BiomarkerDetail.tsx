import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { api } from "../lib/api";
import TrendChart from "../components/TrendChart";
import { formatDate, zoneColor, zoneLabel } from "../lib/utils";
import type { Zone } from "../lib/utils";

export default function BiomarkerDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const biomarkerId = Number(id);

  const qc = useQueryClient();
  const [changingUnit, setChangingUnit] = useState(false);
  const [visibleSupplements, setVisibleSupplements] = useState<Set<number>>(new Set());

  const { data, isLoading, isError } = useQuery({
    queryKey: ["biomarker", biomarkerId],
    queryFn: () => api.biomarkers.detail(biomarkerId),
    enabled: !isNaN(biomarkerId),
  });

  // Supplement query — enabled only after main data loads so we have the date range
  const { data: supplementsInRange = [] } = useQuery({
    queryKey: ["supplements-active", biomarkerId],
    queryFn: async () => {
      const allResults = data?.results ?? [];
      const dates = allResults.map((r) => r.sample_date).filter(Boolean) as string[];
      if (dates.length === 0) return [];
      return api.supplements.activeDuring(dates[0], dates[dates.length - 1]);
    },
    enabled: !!data && data.results.length > 0,
  });

  if (isLoading) return <p className="text-sm text-gray-500">Loading…</p>;
  if (isError || !data) return <p className="text-sm text-red-500">Failed to load biomarker.</p>;

  const { biomarker, results } = data;
  const latest = results[results.length - 1];

  const datesWithData = results.map((r) => r.sample_date).filter(Boolean) as string[];
  const chartFromDate = datesWithData.length > 0 ? datesWithData[0] : null;
  const chartToDate = datesWithData.length > 0 ? datesWithData[datesWithData.length - 1] : null;

  async function handleUnitChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const newUnit = e.target.value;
    setChangingUnit(true);
    try {
      await api.biomarkers.changeDefaultUnit(biomarkerId, newUnit);
      await qc.invalidateQueries({ queryKey: ["biomarker", biomarkerId] });
      await qc.invalidateQueries({ queryKey: ["biomarkers-summary"] });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to change unit";
      alert(msg);
    } finally {
      setChangingUnit(false);
    }
  }

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

      {/* Reference ranges + unit selector */}
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Reference ranges</p>
        {biomarker.alternate_units.length > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <span>Unit:</span>
            <select
              value={biomarker.default_unit ?? ""}
              onChange={handleUnitChange}
              disabled={changingUnit}
              className="px-1.5 py-0.5 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-xs disabled:opacity-50"
            >
              <option value={biomarker.default_unit ?? ""}>{biomarker.default_unit}</option>
              {biomarker.alternate_units.filter((u) => u !== biomarker.default_unit).map((u) => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
          </div>
        )}
      </div>
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

      {/* Supplement toggles */}
      {supplementsInRange.length > 0 && (
        <div className="mb-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">Supplements</p>
          <div className="flex flex-wrap gap-2">
            {supplementsInRange.map((s) => {
              const on = visibleSupplements.has(s.id);
              return (
                <button
                  key={s.id}
                  onClick={() => {
                    setVisibleSupplements((prev) => {
                      const next = new Set(prev);
                      if (on) next.delete(s.id);
                      else next.add(s.id);
                      return next;
                    });
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                    on
                      ? "bg-purple-100 dark:bg-purple-900/30 border-purple-300 dark:border-purple-700 text-purple-700 dark:text-purple-300"
                      : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:border-purple-300"
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${on ? "bg-purple-500" : "border border-gray-400"}`} />
                  {s.name}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Trend chart */}
      <div className="mb-8">
        <TrendChart
          biomarker={biomarker}
          results={results}
          supplementPeriods={
            supplementsInRange
              .filter((s) => visibleSupplements.has(s.id))
              .flatMap((s) =>
                s.doses.map((d) => ({
                  supplementName: s.name,
                  supplementId: s.id,
                  dose: d.dose,
                  unit: s.unit,
                  started_on: d.started_on,
                  ended_on: d.ended_on,
                }))
              )
          }
          chartFromDate={chartFromDate}
          chartToDate={chartToDate}
        />
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
