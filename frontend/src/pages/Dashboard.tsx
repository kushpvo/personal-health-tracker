import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, FileDown } from "lucide-react";
import { api } from "../lib/api";
import type { BiomarkerSummary } from "../lib/api";
import BiomarkerCard from "../components/BiomarkerCard";
import { zoneLabel, zoneColor } from "../lib/utils";
import type { Zone } from "../lib/utils";

const STATUS_ORDER: Zone[] = ["out_of_range", "sufficient", "optimal", "unknown"];

export default function Dashboard() {
  const [groupBy, setGroupBy] = useState<"category" | "status">("status");
  const [exporting, setExporting] = useState(false);

  async function handleExport() {
    setExporting(true);
    try {
      await api.export.pdf();
    } finally {
      setExporting(false);
    }
  }
  const { data: summaries = [], isLoading: isLoadingSummaries } = useQuery({
    queryKey: ["biomarkers-summary"],
    queryFn: api.biomarkers.summary,
  });
  const { data: reports = [], isLoading: isLoadingReports } = useQuery({
    queryKey: ["reports"],
    queryFn: api.reports.list,
  });

  const isLoading = isLoadingSummaries || isLoadingReports;
  const parsedResultsCount = reports.reduce((total, report) => total + report.result_count, 0);
  const recognizedCount = summaries.length;

  if (isLoading) return <p className="text-sm text-gray-500">Loading…</p>;

  if (summaries.length === 0) {
    return (
      <div className="text-center py-20">
        <Activity size={40} className="mx-auto text-gray-300 dark:text-gray-700 mb-3" />
        <p className="text-gray-500 dark:text-gray-400 text-sm">
          No data yet. Upload a lab report to get started.
        </p>
      </div>
    );
  }

  // Group by category
  const byCategory = summaries.reduce<Record<string, BiomarkerSummary[]>>((acc, s) => {
    const cat = s.biomarker.category ?? "Other";
    (acc[cat] ??= []).push(s);
    return acc;
  }, {});

  const byStatus = STATUS_ORDER.reduce<Record<string, BiomarkerSummary[]>>((acc, zone) => {
    const items = summaries.filter((s) => s.latest_zone === zone);
    if (items.length > 0) acc[zone] = items;
    return acc;
  }, {});

  return (
    <div>
      <div className="mb-6 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Dashboard</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {parsedResultsCount} parsed results / {recognizedCount} recognized
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleExport}
            disabled={exporting || summaries.length === 0}
            className="flex items-center gap-1.5 rounded border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:border-gray-700 dark:hover:bg-gray-800 disabled:opacity-40"
          >
            <FileDown size={14} />
            {exporting ? "Generating…" : "Export PDF"}
          </button>
        <div className="flex rounded-md border border-gray-200 dark:border-gray-700 overflow-hidden text-sm">
          {(["category", "status"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setGroupBy(mode)}
              className={`px-3 py-1.5 capitalize transition-colors ${
                groupBy === mode
                  ? "bg-gray-900 text-white dark:bg-white dark:text-gray-900"
                  : "text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
        </div>
      </div>
      <div className="space-y-8">
        {groupBy === "category"
          ? Object.entries(byCategory).map(([category, items]) => (
              <section key={category}>
                <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500 mb-3">
                  {category}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                  {items.map((s) => (
                    <BiomarkerCard key={s.biomarker.id} summary={s} />
                  ))}
                </div>
              </section>
            ))
          : Object.entries(byStatus).map(([zone, items]) => (
              <section key={zone}>
                <h3
                  className="text-xs font-semibold uppercase tracking-widest mb-3"
                  style={{ color: zoneColor(zone as Zone) }}
                >
                  {zoneLabel(zone as Zone)} ({items.length})
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                  {items.map((s) => (
                    <BiomarkerCard key={s.biomarker.id} summary={s} />
                  ))}
                </div>
              </section>
            ))}
      </div>
    </div>
  );
}
