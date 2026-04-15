import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Activity, ArrowLeft } from "lucide-react";
import { api } from "../lib/api";
import type { BiomarkerSummary } from "../lib/api";
import BiomarkerCard from "../components/BiomarkerCard";
import { formatDate, zoneColor, zoneLabel } from "../lib/utils";
import type { Zone } from "../lib/utils";

const STATUS_ORDER: Zone[] = ["out_of_range", "sufficient", "optimal", "unknown"];

export default function ReportDashboard() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const reportId = Number(id);
  const [groupBy, setGroupBy] = useState<"category" | "status">("category");

  const { data: summaries = [], isLoading } = useQuery({
    queryKey: ["report-summary", reportId],
    queryFn: () => api.reports.summary(reportId),
    enabled: !isNaN(reportId),
  });
  const { data: reports = [] } = useQuery({
    queryKey: ["reports"],
    queryFn: () => api.reports.list(),
  });

  const report = reports.find((r) => r.id === reportId);

  if (isLoading) return <p className="text-sm text-gray-500">Loading…</p>;

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

  if (summaries.length === 0) {
    return (
      <div>
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 dark:hover:text-white mb-6"
        >
          <ArrowLeft size={15} /> Back
        </button>
        <div className="text-center py-20">
          <Activity size={40} className="mx-auto text-gray-300 dark:text-gray-700 mb-3" />
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            No recognized biomarkers in this report. Use the Review button to manually
            match unrecognized results.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 dark:hover:text-white mb-6"
      >
        <ArrowLeft size={15} /> Back
      </button>

      <div className="mb-6 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">
            {report?.report_name ?? report?.original_filename ?? `Report #${reportId}`}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Sampled {formatDate(report?.sample_date)} / {summaries.length} biomarkers
          </p>
        </div>
        <div className="flex rounded-md border border-gray-200 dark:border-gray-700 overflow-hidden text-sm shrink-0">
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
