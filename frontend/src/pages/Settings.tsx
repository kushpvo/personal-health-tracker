import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export default function Settings() {
  const qc = useQueryClient();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [sexSaving, setSexSaving] = useState(false);
  const [sexMsg, setSexMsg] = useState<string | null>(null);

  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: api.auth.me,
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword !== confirm) {
      setError("New passwords do not match");
      return;
    }
    setError(null);
    setSuccess(false);
    setLoading(true);
    try {
      await api.auth.changePassword(currentPassword, newPassword);
      setSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirm("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to change password");
    } finally {
      setLoading(false);
    }
  }

  async function handleSexChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value;
    const sex = val === "" ? null : (val as "male" | "female" | "other");
    setSexSaving(true);
    setSexMsg(null);
    try {
      await api.auth.updateProfile(sex);
      qc.invalidateQueries({ queryKey: ["me"] });
      setSexMsg("Saved.");
    } catch {
      setSexMsg("Failed to save.");
    } finally {
      setSexSaving(false);
    }
  }

  return (
    <div className="max-w-md space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <section className="space-y-4 rounded-lg border p-6">
        <h2 className="text-base font-medium">Biological Sex</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Used to show sex-appropriate reference ranges for hormones and related biomarkers.
        </p>
        <div className="flex items-center gap-3">
          <select
            value={me?.sex ?? ""}
            onChange={handleSexChange}
            disabled={sexSaving}
            className="rounded border px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 disabled:opacity-50"
          >
            <option value="">Not specified</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
          {sexMsg && (
            <span className={`text-sm ${sexMsg === "Saved." ? "text-green-600" : "text-red-500"}`}>
              {sexMsg}
            </span>
          )}
        </div>
      </section>

      <section className="space-y-4 rounded-lg border p-6">
        <h2 className="text-base font-medium">Change password</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium">Current password</label>
            <input
              type="password"
              className="w-full rounded border px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">New password</label>
            <input
              type="password"
              className="w-full rounded border px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Confirm new password</label>
            <input
              type="password"
              className="w-full rounded border px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          {success && <p className="text-sm text-green-600">Password updated.</p>}
          <button
            type="submit"
            disabled={loading}
            className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-gray-900"
          >
            {loading ? "Saving..." : "Update password"}
          </button>
        </form>
      </section>
    </div>
  );
}