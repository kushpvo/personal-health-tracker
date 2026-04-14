import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { setToken } from "../lib/auth";

export default function Setup() {
  const navigate = useNavigate();
  const [checking, setChecking] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.auth.setupRequired().then(({ required }) => {
      if (!required) {
        navigate("/", { replace: true });
      } else {
        setChecking(false);
      }
    });
  }, [navigate]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const { access_token } = await api.auth.setup(username, password);
      setToken(access_token);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Setup failed");
    } finally {
      setLoading(false);
    }
  }

  if (checking) return null;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="w-full max-w-sm space-y-6 rounded-lg bg-white p-8 shadow dark:bg-gray-800">
        <div>
          <h1 className="text-center text-xl font-semibold">Set up Lab Tracker</h1>
          <p className="mt-1 text-center text-sm text-gray-500">
            Create your admin account
          </p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Username</label>
            <input
              className="w-full rounded border px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Password</label>
            <input
              type="password"
              className="w-full rounded border px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Confirm password</label>
            <input
              type="password"
              className="w-full rounded border px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-gray-900"
          >
            {loading ? "Creating..." : "Create admin account"}
          </button>
        </form>
      </div>
    </div>
  );
}
