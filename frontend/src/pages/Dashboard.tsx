import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { api } from "../lib/api";
import type { BiomarkerSummary } from "../lib/api";
import BiomarkerCard from "../components/BiomarkerCard";

export default function Dashboard() {
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

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {parsedResultsCount} parsed results / {recognizedCount} recognized
        </p>
      </div>
      <div className="space-y-8">
        {Object.entries(byCategory).map(([category, items]) => (
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
        ))}
      </div>
    </div>
  );
}
