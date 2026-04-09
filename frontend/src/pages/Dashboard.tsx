import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { api } from "../lib/api";
import type { BiomarkerSummary } from "../lib/api";
import BiomarkerCard from "../components/BiomarkerCard";

export default function Dashboard() {
  const { data: summaries = [], isLoading } = useQuery({
    queryKey: ["biomarkers-summary"],
    queryFn: api.biomarkers.summary,
  });

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
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
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
