import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileDown, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import type { BiomarkerSummary } from "../lib/api";

export default function ExportPage() {
  const { data: biomarkers = [], isLoading: bioLoading } = useQuery({
    queryKey: ["biomarkers-summary"],
    queryFn: () => api.biomarkers.summary(),
    staleTime: 60_000,
  });

  const { data: supplements = [], isLoading: suppLoading } = useQuery({
    queryKey: ["supplements"],
    queryFn: api.supplements.list,
    staleTime: 60_000,
  });

  const [selectedBiomarkers, setSelectedBiomarkers] = useState<Set<number>>(new Set());
  const [selectedSupplements, setSelectedSupplements] = useState<Set<number>>(new Set());
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const grouped = useMemo(() => {
    const map = new Map<string, BiomarkerSummary[]>();
    for (const b of biomarkers) {
      const cat = b.biomarker.category || "Uncategorized";
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat)!.push(b);
    }
    return new Map([...map.entries()].sort((a, b) => a[0].localeCompare(b[0])));
  }, [biomarkers]);

  function toggleCategory(cat: string, checked: boolean) {
    const ids = grouped.get(cat)?.map((b) => b.biomarker.id) || [];
    setSelectedBiomarkers((prev) => {
      const next = new Set(prev);
      for (const id of ids) {
        if (checked) next.add(id);
        else next.delete(id);
      }
      return next;
    });
  }

  function toggleBiomarker(id: number, checked: boolean) {
    setSelectedBiomarkers((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  function toggleAllSupplements(checked: boolean) {
    setSelectedSupplements(() => {
      if (checked) return new Set(supplements.map((s) => s.id));
      return new Set();
    });
  }

  function toggleSupplement(id: number, checked: boolean) {
    setSelectedSupplements((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  async function handleGenerate() {
    setError(null);
    setExporting(true);
    try {
      await api.export.customPdf(
        Array.from(selectedBiomarkers),
        Array.from(selectedSupplements)
      );
    } catch (e: any) {
      setError(e.message || "Export failed");
    } finally {
      setExporting(false);
    }
  }

  const isLoading = bioLoading || suppLoading;
  const hasSelection = selectedBiomarkers.size > 0 || selectedSupplements.size > 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Custom Export</h1>
        <button
          onClick={handleGenerate}
          disabled={!hasSelection || exporting || isLoading}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {exporting ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <FileDown size={16} />
          )}
          Generate PDF
        </button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      <section>
        <h2 className="mb-3 text-lg font-semibold">Biomarkers</h2>
        {isLoading ? (
          <p className="text-gray-500 dark:text-gray-400">Loading...</p>
        ) : biomarkers.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400">
            No biomarkers with data available.
          </p>
        ) : (
          <div className="space-y-4">
            {Array.from(grouped.entries()).map(([cat, items]) => {
              const catIds = items.map((i) => i.biomarker.id);
              const selectedCount = catIds.filter((id) =>
                selectedBiomarkers.has(id)
              ).length;
              const allSelected =
                selectedCount === catIds.length && catIds.length > 0;
              const someSelected = selectedCount > 0 && !allSelected;

              return (
                <div
                  key={cat}
                  className="rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex items-center gap-3 bg-gray-50 px-4 py-2 dark:bg-gray-800">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      ref={(el) => {
                        if (el) el.indeterminate = someSelected;
                      }}
                      onChange={(e) => toggleCategory(cat, e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-blue-600"
                    />
                    <span className="font-medium">{cat}</span>
                    <span className="ml-auto rounded-full bg-gray-200 px-2 py-0.5 text-xs dark:bg-gray-700">
                      {selectedCount}/{catIds.length}
                    </span>
                  </div>
                  <div className="divide-y divide-gray-100 dark:divide-gray-800">
                    {items.map((b) => (
                      <label
                        key={b.biomarker.id}
                        className="flex cursor-pointer items-center gap-3 px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                      >
                        <input
                          type="checkbox"
                          checked={selectedBiomarkers.has(b.biomarker.id)}
                          onChange={(e) =>
                            toggleBiomarker(b.biomarker.id, e.target.checked)
                          }
                          className="h-4 w-4 rounded border-gray-300 text-blue-600"
                        />
                        <span className="flex-1">{b.biomarker.name}</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          ({b.result_count} results)
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {supplements.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Supplements</h2>
          <div className="rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3 bg-gray-50 px-4 py-2 dark:bg-gray-800">
              <input
                type="checkbox"
                checked={
                  selectedSupplements.size === supplements.length &&
                  supplements.length > 0
                }
                onChange={(e) => toggleAllSupplements(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600"
              />
              <span className="font-medium">Select all supplements</span>
              <span className="ml-auto rounded-full bg-gray-200 px-2 py-0.5 text-xs dark:bg-gray-700">
                {selectedSupplements.size}/{supplements.length}
              </span>
            </div>
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              {supplements.map((s) => (
                <label
                  key={s.id}
                  className="flex cursor-pointer items-center gap-3 px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                >
                  <input
                    type="checkbox"
                    checked={selectedSupplements.has(s.id)}
                    onChange={(e) => toggleSupplement(s.id, e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-blue-600"
                  />
                  <span className="flex-1">{s.name}</span>
                  {s.doses.some((d) => d.ended_on === null) && (
                    <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-300">
                      Active
                    </span>
                  )}
                </label>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
