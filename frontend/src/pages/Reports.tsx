import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Trash2, FileText } from "lucide-react";
import { api } from "../lib/api";
import type { ReportListItem } from "../lib/api";
import { formatDate } from "../lib/utils";

const STATUS_BADGE: Record<string, string> = {
  done: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  processing: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  pending: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

export default function Reports() {
  const qc = useQueryClient();
  const { data: reports = [], isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: api.reports.list,
  });

  async function handleDelete(id: number) {
    if (!confirm("Delete this report and all its extracted data?")) return;
    await api.reports.delete(id);
    qc.invalidateQueries({ queryKey: ["reports"] });
    qc.invalidateQueries({ queryKey: ["biomarkers-summary"] });
  }

  if (isLoading) return <p className="text-sm text-gray-500">Loading…</p>;

  if (reports.length === 0) {
    return (
      <div className="text-center py-20">
        <FileText size={40} className="mx-auto text-gray-300 dark:text-gray-700 mb-3" />
        <p className="text-gray-500 dark:text-gray-400 text-sm">No reports uploaded yet.</p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Reports</h2>
      <div className="space-y-3">
        {reports.map((r: ReportListItem) => (
          <div
            key={r.id}
            className="flex items-center justify-between gap-4 p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900"
          >
            <div className="min-w-0">
              <p className="font-medium text-sm truncate">
                {r.report_name ?? r.original_filename}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Sampled {formatDate(r.sample_date)} · Uploaded {formatDate(r.uploaded_at)} ·{" "}
                {r.result_count} biomarkers
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  STATUS_BADGE[r.status] ?? STATUS_BADGE.pending
                }`}
              >
                {r.status}
              </span>
              <a
                href={api.reports.downloadUrl(r.id)}
                download={r.original_filename}
                className="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
                title="Download original"
              >
                <Download size={15} />
              </a>
              <button
                onClick={() => handleDelete(r.id)}
                className="p-1.5 rounded-md hover:bg-red-50 dark:hover:bg-red-950 text-gray-400 hover:text-red-500"
                title="Delete report"
              >
                <Trash2 size={15} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
