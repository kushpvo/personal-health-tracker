import { useState, useEffect, useMemo, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Trash2, Plus } from "lucide-react";
import { api } from "../lib/api";
import type { BiomarkerListItem, ReportResultItem } from "../lib/api";

const COMMON_UNITS = [
  "g/L", "g/dL", "mg/dL", "mg/L", "mmol/L", "umol/L", "nmol/L", "pmol/L",
  "U/L", "IU/L", "mIU/L", "%", "ng/mL", "ng/dL", "ng/L", "pg/mL", "ug/L",
  "x10e9/L", "x10e12/L", "fL", "pg", "mm/Hour", "mL/min/1.73m2", "ratio",
];

type DraftResult = {
  id: number;               // negative for user-added rows
  raw_name: string;
  is_flagged_unknown: boolean;
  biomarker_id: number | null;
  draftValue: string;
  draftUnit: string;
  draftBiomarkerId: number | null;
  draftBiomarkerName: string | null;
  valueError: string | null;
  isNew: boolean;
};

function unitOptionsFor(
  draft: DraftResult,
  allBiomarkers: BiomarkerListItem[],
): string[] {
  const matchedId = draft.draftBiomarkerId ?? draft.biomarker_id;
  if (matchedId) {
    const bm = allBiomarkers.find((b) => b.id === matchedId);
    if (bm) {
      const opts = [bm.default_unit ?? "", ...bm.alternate_units].filter(Boolean);
      if (!opts.includes(draft.draftUnit)) opts.unshift(draft.draftUnit);
      return opts;
    }
  }
  const opts = [...COMMON_UNITS];
  if (draft.draftUnit && !opts.includes(draft.draftUnit)) opts.unshift(draft.draftUnit);
  return opts;
}

export default function ReviewReport() {
  const { id } = useParams<{ id: string }>();
  const reportId = Number(id);
  const navigate = useNavigate();
  const newIdCounter = useRef(-1);

  const { data: rawResults, isLoading: loadingResults } = useQuery({
    queryKey: ["report-results", reportId],
    queryFn: () => api.reports.results(reportId),
  });

  const { data: allBiomarkers = [], isLoading: loadingBiomarkers } = useQuery({
    queryKey: ["biomarkers-list"],
    queryFn: api.biomarkers.list,
  });

  const { data: reports = [] } = useQuery({
    queryKey: ["reports"],
    queryFn: api.reports.list,
  });

  const report = reports.find((r) => r.id === reportId);

  const [draftTitle, setDraftTitle] = useState("");
  const [draftDate, setDraftDate] = useState("");
  const [tags, setTags] = useState("");
  const [drafts, setDrafts] = useState<DraftResult[]>([]);
  const [deletedIds, setDeletedIds] = useState<number[]>([]);
  const [resultNotes, setResultNotes] = useState<Record<number, string>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (rawResults && drafts.length === 0) {
      setDrafts(
        rawResults.map((r: ReportResultItem) => ({
          id: r.id,
          raw_name: r.raw_name,
          is_flagged_unknown: r.is_flagged_unknown,
          biomarker_id: r.biomarker_id,
          draftValue: String(r.value),
          draftUnit: r.unit,
          draftBiomarkerId: null,
          draftBiomarkerName: null,
          valueError: null,
          isNew: false,
        }))
      );
      const notesInit: Record<number, string> = {};
      for (const r of rawResults) {
        if (r.notes) notesInit[r.id] = r.notes;
      }
      setResultNotes(notesInit);
    }
  }, [rawResults]);

  useEffect(() => {
    if (report && !draftTitle) setDraftTitle(report.report_name ?? report.original_filename);
    if (report && !draftDate) setDraftDate(report.sample_date ?? "");
    if (report && !tags) setTags(report.tags ?? "");
  }, [report]);

  const byCategory = useMemo(() => {
    return allBiomarkers.reduce<Record<string, BiomarkerListItem[]>>((acc, b) => {
      const cat = b.category ?? "Other";
      (acc[cat] ??= []).push(b);
      return acc;
    }, {});
  }, [allBiomarkers]);

  if (loadingResults || loadingBiomarkers) {
    return <p className="text-sm text-gray-500 p-6">Loading…</p>;
  }

  const recognised = drafts.filter(
    (d) => !d.isNew && (!d.is_flagged_unknown || d.draftBiomarkerId !== null)
  ).length;
  const unrecognised = drafts.filter(
    (d) => !d.isNew && d.is_flagged_unknown && d.draftBiomarkerId === null
  ).length;
  const added = drafts.filter((d) => d.isNew).length;

  function updateDraft(id: number, patch: Partial<DraftResult>) {
    setDrafts((prev) => prev.map((d) => (d.id === id ? { ...d, ...patch } : d)));
  }

  function deleteDraft(id: number) {
    if (id > 0) setDeletedIds((prev) => [...prev, id]);
    setDrafts((prev) => prev.filter((d) => d.id !== id));
  }

  function addNewRow() {
    const newId = newIdCounter.current--;
    setDrafts((prev) => [
      ...prev,
      {
        id: newId,
        raw_name: "",
        is_flagged_unknown: false,
        biomarker_id: null,
        draftValue: "",
        draftUnit: "",
        draftBiomarkerId: null,
        draftBiomarkerName: null,
        valueError: null,
        isNew: true,
      },
    ]);
  }

  function selectBiomarkerForNew(draftId: number, biomarkerId: number) {
    const bm = allBiomarkers.find((b) => b.id === biomarkerId);
    if (!bm) return;
    updateDraft(draftId, {
      draftBiomarkerId: bm.id,
      draftBiomarkerName: bm.name,
      draftUnit: bm.default_unit ?? "",
    });
  }

  async function handleSave() {
    let hasError = false;
    const validated = drafts.map((d) => {
      if (isNaN(parseFloat(d.draftValue))) {
        hasError = true;
        return { ...d, valueError: "Must be a number" };
      }
      return { ...d, valueError: null };
    });
    setDrafts(validated);
    if (hasError) return;

    setSaving(true);
    try {
      const existing = validated.filter((d) => !d.isNew);
      const newRows = validated.filter((d) => d.isNew && d.draftBiomarkerId !== null);

      await api.reports.review(reportId, {
        report_name: draftTitle,
        sample_date: draftDate || null,
        results: existing.map((d) => ({
          id: d.id,
          value: parseFloat(d.draftValue),
          unit: d.draftUnit,
          ...(d.draftBiomarkerId ? { biomarker_id: d.draftBiomarkerId } : {}),
        })),
        new_results: newRows.map((d) => ({
          biomarker_id: d.draftBiomarkerId!,
          value: parseFloat(d.draftValue),
          unit: d.draftUnit,
        })),
        deleted_result_ids: deletedIds,
        tags: tags || undefined,
        result_notes: resultNotes,
      });
      navigate("/");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-5xl">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 mb-4">
        <Link to="/reports/upload" className="hover:underline">
          Upload Lab Report
        </Link>
        <span className="mx-2">›</span>
        <span className="text-gray-900 dark:text-gray-100">Review Results</span>
      </nav>

      {/* Report metadata */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Report title</label>
          <input
            type="text"
            value={draftTitle}
            onChange={(e) => setDraftTitle(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Sample date</label>
          <input
            type="date"
            value={draftDate}
            onChange={(e) => setDraftDate(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm"
          />
        </div>
      </div>
      <div className="mb-6">
        <label className="block text-sm font-medium mb-1">Tags (comma-separated)</label>
        <input
          type="text"
          placeholder="Annual Physical, Fasting"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          className="w-full rounded border px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-600"
        />
      </div>

      {/* Summary + top action */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">
          {drafts.length} extracted · {recognised} recognised · {unrecognised} unrecognised
          {added > 0 && ` · ${added} added`}
        </p>
        <button
          onClick={handleSave}
          disabled={saving}
          className="text-sm px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Confirm & Save"}
        </button>
      </div>

      {/* Results table */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-900 text-xs text-gray-500 uppercase tracking-wide">
            <tr>
              <th className="px-4 py-3 text-left w-8">#</th>
              <th className="px-4 py-3 text-left">Biomarker (OCR name)</th>
              <th className="px-4 py-3 text-left w-32">Value</th>
              <th className="px-4 py-3 text-left w-44">Unit</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Notes</th>
              <th className="px-4 py-3 w-10"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {drafts.map((d, idx) => {
              const isRecognised = !d.isNew && !d.is_flagged_unknown;
              const isMatched = !d.isNew && d.is_flagged_unknown && d.draftBiomarkerId !== null;
              const isUnrecognised = !d.isNew && d.is_flagged_unknown && d.draftBiomarkerId === null;
              const unitOpts = unitOptionsFor(d, allBiomarkers);

              return (
                <tr key={d.id} className={`bg-white dark:bg-gray-950 ${d.isNew ? "bg-blue-50/30 dark:bg-blue-950/20" : ""}`}>
                  <td className="px-4 py-3 text-gray-400 text-xs">{d.isNew ? "+" : idx + 1}</td>

                  {/* Biomarker name / picker */}
                  <td className="px-4 py-3 font-medium">
                    {d.isNew ? (
                      <select
                        value={d.draftBiomarkerId ?? ""}
                        onChange={(e) => selectBiomarkerForNew(d.id, Number(e.target.value))}
                        className="w-full px-2 py-1 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm"
                      >
                        <option value="" disabled>Select biomarker…</option>
                        {Object.entries(byCategory)
                          .sort(([a], [b]) => a.localeCompare(b))
                          .map(([cat, bms]) => (
                            <optgroup key={cat} label={cat}>
                              {bms.map((b) => (
                                <option key={b.id} value={b.id}>{b.name}</option>
                              ))}
                            </optgroup>
                          ))}
                      </select>
                    ) : (
                      d.raw_name
                    )}
                  </td>

                  {/* Value */}
                  <td className="px-4 py-3">
                    <input
                      type="text"
                      value={d.draftValue}
                      onChange={(e) =>
                        updateDraft(d.id, { draftValue: e.target.value, valueError: null })
                      }
                      className={`w-full px-2 py-1 rounded border text-sm bg-white dark:bg-gray-900 ${
                        d.valueError
                          ? "border-red-400 dark:border-red-500"
                          : "border-gray-300 dark:border-gray-700"
                      }`}
                    />
                    {d.valueError && (
                      <p className="text-xs text-red-500 mt-0.5">{d.valueError}</p>
                    )}
                  </td>

                  {/* Unit */}
                  <td className="px-4 py-3">
                    <select
                      value={d.draftUnit}
                      onChange={(e) => updateDraft(d.id, { draftUnit: e.target.value })}
                      className="w-full px-2 py-1 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm"
                    >
                      {unitOpts.map((u) => (
                        <option key={u} value={u}>{u}</option>
                      ))}
                    </select>
                  </td>

                  {/* Status */}
                  <td className="px-4 py-3">
                    {isRecognised && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                        Recognised
                      </span>
                    )}
                    {isMatched && (
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400">
                        {d.draftBiomarkerName}
                        <button
                          onClick={() =>
                            updateDraft(d.id, {
                              draftBiomarkerId: null,
                              draftBiomarkerName: null,
                            })
                          }
                          className="hover:text-teal-900 dark:hover:text-teal-200 leading-none"
                          aria-label="Remove match"
                        >
                          ×
                        </button>
                      </span>
                    )}
                    {isUnrecognised && (
                      <div className="space-y-1.5">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                          Unrecognised
                        </span>
                        <select
                          defaultValue=""
                          onChange={(e) => {
                            const bm = allBiomarkers.find(
                              (b) => b.id === Number(e.target.value)
                            );
                            if (bm)
                              updateDraft(d.id, {
                                draftBiomarkerId: bm.id,
                                draftBiomarkerName: bm.name,
                              });
                          }}
                          className="w-full px-2 py-1 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-xs"
                        >
                          <option value="" disabled>
                            Match to…
                          </option>
                          {Object.entries(byCategory)
                            .sort(([a], [b]) => a.localeCompare(b))
                            .map(([cat, bms]) => (
                              <optgroup key={cat} label={cat}>
                                {bms.map((b) => (
                                  <option key={b.id} value={b.id}>
                                    {b.name}
                                  </option>
                                ))}
                              </optgroup>
                            ))}
                        </select>
                      </div>
                    )}
                    {d.isNew && d.draftBiomarkerId !== null && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                        Added
                      </span>
                    )}
                  </td>

                  {/* Notes */}
                  <td className="px-4 py-3">
                    <textarea
                      value={d.id > 0 ? (resultNotes[d.id] ?? "") : ""}
                      onChange={(e) => {
                        if (d.id > 0) {
                          setResultNotes((prev) => ({ ...prev, [d.id]: e.target.value }));
                        }
                      }}
                      placeholder="Optional note…"
                      rows={1}
                      className="w-full px-2 py-1 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-xs resize-none"
                    />
                  </td>

                  {/* Delete */}
                  <td className="px-2 py-3">
                    <button
                      onClick={() => deleteDraft(d.id)}
                      className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-950 text-gray-300 hover:text-red-500 dark:text-gray-700 dark:hover:text-red-400 transition-colors"
                      aria-label="Delete row"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {/* Add row button */}
        <div className="px-4 py-2 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900">
          <button
            onClick={addNewRow}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors py-1"
          >
            <Plus size={13} />
            Add biomarker
          </button>
        </div>
      </div>

      {/* Footer actions */}
      <div className="flex justify-end gap-3 mt-6">
        <button
          onClick={() => navigate("/")}
          className="text-sm px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-900"
        >
          Skip review
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="text-sm px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Confirm & Save"}
        </button>
      </div>
    </div>
  );
}
