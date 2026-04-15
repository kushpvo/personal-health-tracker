import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { BiomarkerListItem } from "../lib/api";

const SEX_SPECIFIC_NAMES = new Set([
  "testosterone", "shbg", "lh", "fsh",
  "estradiol", "progesterone", "prolactin", "dhea-s",
]);

export default function UnknownBiomarkers() {
  const qc = useQueryClient();

  const { data: unknowns = [] } = useQuery({
    queryKey: ["unknowns"],
    queryFn: api.unknowns.list,
  });

  const { data: biomarkers = [] } = useQuery({
    queryKey: ["biomarkers-list"],
    queryFn: api.biomarkers.list,
  });

  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: api.auth.me,
  });

  const hasSexRelatedUnknowns = unknowns.some((u) =>
    SEX_SPECIFIC_NAMES.has(u.raw_name.toLowerCase())
  );
  const needsSexForMatching = me != null && me.sex !== "male" && me.sex !== "female";

  const resolve = useMutation({
    mutationFn: ({ id, biomarker_id }: { id: number; biomarker_id: number }) =>
      api.unknowns.resolve(id, biomarker_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["unknowns"] });
      qc.invalidateQueries({ queryKey: ["biomarkers-summary"] });
    },
  });

  if (unknowns.length === 0) {
    return (
      <div className="max-w-3xl">
        <h1 className="text-2xl font-semibold mb-6">Unrecognised Biomarkers</h1>
        <p className="text-sm text-gray-500">No unrecognised biomarkers — all OCR results matched successfully.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold">Unrecognised Biomarkers</h1>
      {hasSexRelatedUnknowns && needsSexForMatching && (
        <div className="rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 px-4 py-3 text-sm text-yellow-800 dark:text-yellow-200">
          Some markers may be unmatched because your biological sex is not set to Male or Female.{" "}
          <Link to="/settings" className="font-medium underline">Set it in Settings</Link>,
          then reprocess the report. Matching is only sex-aware when set to Male or Female.
        </div>
      )}
      <p className="text-sm text-gray-500">
        Link each name to a known biomarker. Future reports with the same name will match automatically.
      </p>
      <table className="w-full text-sm border rounded-lg overflow-hidden">
        <thead className="bg-gray-100 dark:bg-gray-800">
          <tr>
            <th className="px-4 py-2 text-left">OCR Name</th>
            <th className="px-4 py-2 text-left">Unit</th>
            <th className="px-4 py-2 text-left">Seen</th>
            <th className="px-4 py-2 text-left">Link to</th>
          </tr>
        </thead>
        <tbody>
          {unknowns.map((u) => (
            <tr key={u.id} className="border-t dark:border-gray-700">
              <td className="px-4 py-2 font-mono">{u.raw_name}</td>
              <td className="px-4 py-2 text-gray-500">{u.raw_unit ?? "—"}</td>
              <td className="px-4 py-2 text-gray-500">{u.times_seen}×</td>
              <td className="px-4 py-2">
                <select
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value)
                      resolve.mutate({ id: u.id, biomarker_id: Number(e.target.value) });
                  }}
                  className="rounded border px-2 py-1 text-sm dark:bg-gray-800 dark:border-gray-600"
                >
                  <option value="">Match to…</option>
                  {biomarkers.map((b: BiomarkerListItem) => (
                    <option key={b.id} value={b.id}>{b.name} ({b.category})</option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
