import { useState } from "react";
import { api } from "../lib/api";

export default function Settings() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

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

  return (
    <div className="max-w-md space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>
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
