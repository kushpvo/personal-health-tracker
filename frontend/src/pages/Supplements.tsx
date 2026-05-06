import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2, Plus, ChevronDown, ChevronUp } from "lucide-react";
import { api } from "../lib/api";
import type {
  SupplementLogItem,
  SupplementDoseItem,
  CreateSupplementInput,
  UpdateSupplementInput,
  AddDoseInput,
  UpdateDoseInput,
} from "../lib/api";

const FREQUENCIES = [
  { value: "daily", label: "Daily" },
  { value: "twice_daily", label: "Twice Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "every_other_day", label: "Every Other Day" },
  { value: "as_needed", label: "As Needed" },
];

function freqLabel(value: string): string {
  return FREQUENCIES.find((f) => f.value === value)?.label ?? value;
}

function formatDateStr(d: string | null): string {
  if (!d) return "present";
  const [year, month, day] = d.split("-");
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${months[parseInt(month) - 1]} ${day}, ${year}`;
}

function computeDays(startedOn: string, endedOn: string | null): number {
  const start = new Date(startedOn + "T00:00:00");
  const end = endedOn ? new Date(endedOn + "T00:00:00") : new Date();
  const diff = Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
  return diff + 1; // inclusive
}

// ── Create / Edit form ───────────────────────────────────────────────────────

interface FormState {
  name: string;
  unit: string;
  frequency: string;
  dose: string;
  started_on: string;
  notes: string;
  date_notes: string;
  is_date_approximate: boolean;
}

const EMPTY_FORM: FormState = {
  name: "",
  unit: "",
  frequency: "daily",
  dose: "",
  started_on: new Date().toISOString().slice(0, 10),
  notes: "",
  date_notes: "",
  is_date_approximate: false,
};

interface SupplementFormProps {
  initial?: FormState;
  editingId?: number | null;
  onSubmit: (form: FormState) => Promise<void>;
  onCancel?: () => void;
}

function SupplementForm({ initial, editingId, onSubmit, onCancel }: SupplementFormProps) {
  const [form, setForm] = useState<FormState>(initial ?? EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set(key: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim() || !form.unit.trim() || !form.dose || !form.started_on) {
      setError("Name, unit, dose, and start date are required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit(form);
      if (!editingId) setForm(EMPTY_FORM);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 p-5 space-y-4">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
        {editingId ? "Edit supplement" : "Add supplement / medication"}
      </h3>
      {error && <p className="text-xs text-red-500">{error}</p>}
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2 sm:col-span-1">
          <label className="block text-xs text-gray-500 mb-1">Name</label>
          <input
            className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-1.5 text-sm"
            placeholder="e.g. Vitamin D3, Levothyroxine"
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Unit</label>
          <input
            className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-1.5 text-sm"
            placeholder="mcg, mg, IU…"
            value={form.unit}
            onChange={(e) => set("unit", e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Frequency</label>
          <select
            className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-1.5 text-sm"
            value={form.frequency}
            onChange={(e) => set("frequency", e.target.value)}
          >
            {FREQUENCIES.map((f) => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>
        </div>
        {!editingId && (
          <>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Initial dose</label>
              <input
                type="number"
                min="0"
                step="any"
                className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-1.5 text-sm"
                placeholder="50"
                value={form.dose}
                onChange={(e) => set("dose", e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Start date</label>
              <input
                type="date"
                className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-1.5 text-sm"
                value={form.started_on}
                onChange={(e) => set("started_on", e.target.value)}
              />
            </div>
            <div className="col-span-2 flex items-center gap-2">
              <input
                id="approx-date"
                type="checkbox"
                className="rounded border-gray-300 dark:border-gray-700"
                checked={form.is_date_approximate}
                onChange={(e) => setForm((prev) => ({ ...prev, is_date_approximate: e.target.checked }))}
              />
              <label htmlFor="approx-date" className="text-xs text-gray-500">
                Date is approximate / I don't remember exactly
              </label>
            </div>
            {form.is_date_approximate && (
              <div className="col-span-2">
                <label className="block text-xs text-gray-500 mb-1">Date notes</label>
                <input
                  className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-1.5 text-sm"
                  placeholder="e.g. Around 2021, not sure exactly"
                  value={form.date_notes}
                  onChange={(e) => set("date_notes", e.target.value)}
                />
              </div>
            )}
          </>
        )}
        <div className="col-span-2">
          <label className="block text-xs text-gray-500 mb-1">Notes (optional)</label>
          <textarea
            rows={2}
            className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-1.5 text-sm resize-none"
            placeholder="With food, doctor prescribed, etc."
            value={form.notes}
            onChange={(e) => set("notes", e.target.value)}
          />
        </div>
      </div>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-1.5 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Saving…" : editingId ? "Save changes" : "Add"}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="px-4 py-1.5 rounded-md text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}

// ── Add-dose inline form ─────────────────────────────────────────────────────

interface AddDoseFormProps {
  supplementId: number;
  onDone: () => void;
}

function AddDoseForm({ supplementId, onDone }: AddDoseFormProps) {
  const qc = useQueryClient();
  const [dose, setDose] = useState("");
  const [startedOn, setStartedOn] = useState(new Date().toISOString().slice(0, 10));
  const [dateNotes, setDateNotes] = useState("");
  const [isApprox, setIsApprox] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!dose || !startedOn) { setError("Dose and date required."); return; }
    setSaving(true);
    setError(null);
    try {
      const body: AddDoseInput = {
        dose: parseFloat(dose),
        started_on: startedOn,
        date_notes: isApprox ? dateNotes.trim() || undefined : undefined,
        is_date_approximate: isApprox,
      };
      await api.supplements.addDose(supplementId, body);
      qc.invalidateQueries({ queryKey: ["supplements"] });
      onDone();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 ml-6 space-y-2">
      {error && <p className="text-xs text-red-500">{error}</p>}
      <div className="flex items-end gap-2 flex-wrap">
        <div>
          <label className="block text-xs text-gray-500 mb-1">New dose</label>
          <input
            type="number" min="0" step="any"
            className="w-24 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-2 py-1 text-sm"
            placeholder="75"
            value={dose}
            onChange={(e) => setDose(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Starting</label>
          <input
            type="date"
            className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-2 py-1 text-sm"
            value={startedOn}
            onChange={(e) => setStartedOn(e.target.value)}
          />
        </div>
        <button type="submit" disabled={saving}
          className="px-3 py-1 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {saving ? "…" : "Save"}
        </button>
        <button type="button" onClick={onDone} className="px-3 py-1 rounded-md text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800">
          Cancel
        </button>
      </div>
      <div className="flex items-center gap-2">
        <input
          id="add-approx"
          type="checkbox"
          className="rounded border-gray-300 dark:border-gray-700"
          checked={isApprox}
          onChange={(e) => setIsApprox(e.target.checked)}
        />
        <label htmlFor="add-approx" className="text-xs text-gray-500">
          Date is approximate / I don't remember exactly
        </label>
      </div>
      {isApprox && (
        <input
          className="w-full max-w-sm rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-2 py-1 text-sm"
          placeholder="e.g. Around 2021, not sure exactly"
          value={dateNotes}
          onChange={(e) => setDateNotes(e.target.value)}
        />
      )}
    </form>
  );
}

// ── Edit-dose inline form ────────────────────────────────────────────────────

interface EditDoseFormProps {
  supplementId: number;
  dose: SupplementDoseItem;
  onDone: () => void;
}

function EditDoseForm({ supplementId, dose, onDone }: EditDoseFormProps) {
  const qc = useQueryClient();
  const [doseVal, setDoseVal] = useState(String(dose.dose));
  const [startedOn, setStartedOn] = useState(dose.started_on);
  const [endedOn, setEndedOn] = useState(dose.ended_on ?? "");
  const [dateNotes, setDateNotes] = useState(dose.date_notes ?? "");
  const [isApprox, setIsApprox] = useState(dose.is_date_approximate);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const body: UpdateDoseInput = {
        dose: parseFloat(doseVal),
        started_on: startedOn,
        ended_on: endedOn || undefined,
        date_notes: isApprox ? dateNotes.trim() || undefined : undefined,
        is_date_approximate: isApprox,
      };
      await api.supplements.updateDose(supplementId, dose.id, body);
      qc.invalidateQueries({ queryKey: ["supplements"] });
      onDone();
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 mt-1">
      <div className="flex items-end gap-2 flex-wrap">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Dose</label>
          <input type="number" min="0" step="any"
            className="w-20 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-2 py-1 text-xs"
            value={doseVal} onChange={(e) => setDoseVal(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Started</label>
          <input type="date"
            className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-2 py-1 text-xs"
            value={startedOn} onChange={(e) => setStartedOn(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Ended (blank = active)</label>
          <input type="date"
            className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-2 py-1 text-xs"
            value={endedOn} onChange={(e) => setEndedOn(e.target.value)} />
        </div>
        <button type="submit" disabled={saving}
          className="px-2 py-1 rounded bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 disabled:opacity-50">
          {saving ? "…" : "Save"}
        </button>
        <button type="button" onClick={onDone} className="px-2 py-1 rounded text-xs text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800">
          Cancel
        </button>
      </div>
      <div className="flex items-center gap-2">
        <input
          id="edit-approx"
          type="checkbox"
          className="rounded border-gray-300 dark:border-gray-700"
          checked={isApprox}
          onChange={(e) => setIsApprox(e.target.checked)}
        />
        <label htmlFor="edit-approx" className="text-xs text-gray-500">
          Date is approximate / I don't remember exactly
        </label>
      </div>
      {isApprox && (
        <input
          className="w-full max-w-sm rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-2 py-1 text-xs"
          placeholder="e.g. Around 2021, not sure exactly"
          value={dateNotes}
          onChange={(e) => setDateNotes(e.target.value)}
        />
      )}
    </form>
  );
}

// ── Supplement card ──────────────────────────────────────────────────────────

interface SupplementCardProps {
  supplement: SupplementLogItem;
  onEdit: (s: SupplementLogItem) => void;
}

function SupplementCard({ supplement, onEdit }: SupplementCardProps) {
  const qc = useQueryClient();
  const [showAddDose, setShowAddDose] = useState(false);
  const [editingDoseId, setEditingDoseId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [expanded, setExpanded] = useState(true);

  const isActive = supplement.doses.some((d) => d.is_active);

  async function handleDeleteSupplement() {
    if (!confirm(`Delete "${supplement.name}" and all its dose history?`)) return;
    setDeleting(true);
    try {
      await api.supplements.delete(supplement.id);
      qc.invalidateQueries({ queryKey: ["supplements"] });
    } finally {
      setDeleting(false);
    }
  }

  async function handleDeleteDose(doseId: number) {
    if (!confirm("Delete this dose period?")) return;
    await api.supplements.deleteDose(supplement.id, doseId);
    qc.invalidateQueries({ queryKey: ["supplements"] });
  }

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-900">
        <div className="flex items-center gap-3 min-w-0">
          <button onClick={() => setExpanded((v) => !v)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 shrink-0">
            {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>
          <div className="min-w-0">
            <span className="font-medium text-sm">{supplement.name}</span>
            <span className="text-xs text-gray-400 dark:text-gray-500 ml-1.5">({supplement.unit})</span>
          </div>
          <span className="shrink-0 text-xs px-2 py-0.5 rounded-full border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400">
            {freqLabel(supplement.frequency)}
          </span>
          {isActive && (
            <span className="shrink-0 text-xs px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 font-medium">
              Active
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0 ml-2">
          <button
            onClick={() => onEdit(supplement)}
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            title="Edit"
          >
            <Pencil size={13} />
          </button>
          <button
            onClick={handleDeleteSupplement}
            disabled={deleting}
            className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 disabled:opacity-50"
            title="Delete"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-4 py-3">
          {supplement.notes && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 italic">{supplement.notes}</p>
          )}

          {/* Vertical dose timeline */}
          <div className="relative ml-2">
            {supplement.doses.map((dose, idx) => (
              <div key={dose.id} className="relative flex gap-3 pb-4 last:pb-0">
                {/* Timeline line + dot */}
                <div className="flex flex-col items-center">
                  <div className={`w-2.5 h-2.5 rounded-full border-2 mt-0.5 shrink-0 ${
                    dose.is_active
                      ? "border-green-500 bg-green-500"
                      : "border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-950"
                  }`} />
                  {idx < supplement.doses.length - 1 && (
                    <div className="w-px flex-1 bg-gray-200 dark:bg-gray-700 mt-1" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  {editingDoseId === dose.id ? (
                    <EditDoseForm
                      supplementId={supplement.id}
                      dose={dose}
                      onDone={() => setEditingDoseId(null)}
                    />
                  ) : (
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="text-sm font-medium">{dose.dose} {supplement.unit}</span>
                        {dose.is_date_approximate ? (
                          <>
                            <span className="text-xs text-gray-400 dark:text-gray-500 ml-2">
                              ~ {formatDateStr(dose.started_on)} → {formatDateStr(dose.ended_on)}
                            </span>
                            {dose.date_notes && (
                              <span className="block text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                                {dose.date_notes}
                              </span>
                            )}
                          </>
                        ) : (
                          <>
                            <span className="text-xs text-gray-400 dark:text-gray-500 ml-2">
                              {formatDateStr(dose.started_on)} → {formatDateStr(dose.ended_on)}
                            </span>
                            <span className="text-xs text-gray-400 dark:text-gray-500 ml-2">
                              · {computeDays(dose.started_on, dose.ended_on)} days
                            </span>
                          </>
                        )}
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <button
                          onClick={() => setEditingDoseId(dose.id)}
                          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600"
                          title="Edit dose"
                        >
                          <Pencil size={11} />
                        </button>
                        <button
                          onClick={() => handleDeleteDose(dose.id)}
                          className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500"
                          title="Delete dose"
                        >
                          <Trash2 size={11} />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Add dose change */}
          {showAddDose ? (
            <AddDoseForm
              supplementId={supplement.id}
              onDone={() => setShowAddDose(false)}
            />
          ) : (
            <button
              onClick={() => setShowAddDose(true)}
              className="mt-2 ml-6 flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400 hover:underline"
            >
              <Plus size={12} /> Add dose change
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function Supplements() {
  const qc = useQueryClient();
  const [editingSupp, setEditingSupp] = useState<SupplementLogItem | null>(null);

  const { data: supplements = [], isLoading } = useQuery({
    queryKey: ["supplements"],
    queryFn: api.supplements.list,
  });

  async function handleCreate(form: FormState) {
    const body: CreateSupplementInput = {
      name: form.name.trim(),
      unit: form.unit.trim(),
      frequency: form.frequency,
      dose: parseFloat(form.dose),
      started_on: form.started_on,
      notes: form.notes.trim() || undefined,
      date_notes: form.is_date_approximate ? form.date_notes.trim() || undefined : undefined,
      is_date_approximate: form.is_date_approximate,
    };
    await api.supplements.create(body);
    qc.invalidateQueries({ queryKey: ["supplements"] });
  }

  async function handleUpdate(form: FormState) {
    if (!editingSupp) return;
    const body: UpdateSupplementInput = {
      name: form.name.trim(),
      unit: form.unit.trim(),
      frequency: form.frequency,
      notes: form.notes.trim() || undefined,
    };
    await api.supplements.update(editingSupp.id, body);
    qc.invalidateQueries({ queryKey: ["supplements"] });
    setEditingSupp(null);
  }

  // Sort: active first, then stopped; within each group by most recent started_on
  const sorted = [...supplements].sort((a, b) => {
    const aActive = a.doses.some((d) => d.is_active) ? 1 : 0;
    const bActive = b.doses.some((d) => d.is_active) ? 1 : 0;
    if (aActive !== bActive) return bActive - aActive;
    const aDate = a.doses.at(-1)?.started_on ?? "";
    const bDate = b.doses.at(-1)?.started_on ?? "";
    return bDate.localeCompare(aDate);
  });

  return (
    <div className="max-w-2xl space-y-6">
      <h2 className="text-2xl font-bold">Supplements & Medications</h2>

      {editingSupp ? (
        <SupplementForm
          editingId={editingSupp.id}
          initial={{
            name: editingSupp.name,
            unit: editingSupp.unit,
            frequency: editingSupp.frequency,
            dose: "",
            started_on: new Date().toISOString().slice(0, 10),
            notes: editingSupp.notes ?? "",
            date_notes: "",
            is_date_approximate: false,
          }}
          onSubmit={handleUpdate}
          onCancel={() => setEditingSupp(null)}
        />
      ) : (
        <SupplementForm onSubmit={handleCreate} />
      )}

      {isLoading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : sorted.length === 0 ? (
        <p className="text-sm text-gray-400">No supplements logged yet.</p>
      ) : (
        <div className="space-y-3">
          {sorted.map((s) => (
            <SupplementCard
              key={s.id}
              supplement={s}
              onEdit={setEditingSupp}
            />
          ))}
        </div>
      )}
    </div>
  );
}
