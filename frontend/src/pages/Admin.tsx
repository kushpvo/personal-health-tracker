import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { startImpersonation } from "../lib/auth";

export default function Admin() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState<"user" | "admin">("user");
  const [createError, setCreateError] = useState<string | null>(null);

  const { data: users = [] } = useQuery({
    queryKey: ["admin-users"],
    queryFn: api.admin.listUsers,
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      api.admin.updateUser(id, { is_active }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const resetPassword = useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) =>
      api.admin.updateUser(id, { password }),
  });

  const impersonate = useMutation({
    mutationFn: ({ userId }: { userId: number; username: string }) =>
      api.admin.impersonate(userId),
    onSuccess: (data, { username }) => {
      startImpersonation(data.access_token, username);
      navigate("/");
      window.location.reload();
    },
  });

  const createUser = useMutation({
    mutationFn: () => api.admin.createUser(newUsername, newPassword, newRole),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      setNewUsername("");
      setNewPassword("");
      setNewRole("user");
      setCreateError(null);
    },
    onError: (err) =>
      setCreateError(err instanceof Error ? err.message : "Failed"),
  });

  function handleResetPassword(id: number, username: string) {
    const pw = window.prompt(`New password for ${username}:`);
    if (!pw) return;
    if (pw.length < 8) {
      alert("Password must be at least 8 characters");
      return;
    }
    resetPassword.mutate({ id, password: pw });
  }

  return (
    <div className="max-w-3xl space-y-8">
      <h1 className="text-2xl font-semibold">Admin - Users</h1>
      <table className="w-full overflow-hidden rounded-lg border text-sm">
        <thead className="bg-gray-100 dark:bg-gray-800">
          <tr>
            <th className="px-4 py-2 text-left">Username</th>
            <th className="px-4 py-2 text-left">Role</th>
            <th className="px-4 py-2 text-left">Status</th>
            <th className="px-4 py-2 text-left">Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} className="border-t dark:border-gray-700">
              <td className="px-4 py-2">{u.username}</td>
              <td className="px-4 py-2 capitalize">{u.role}</td>
              <td className="px-4 py-2">{u.is_active ? "Active" : "Inactive"}</td>
              <td className="flex gap-2 px-4 py-2">
                <button
                  className="rounded border px-2 py-1 text-xs"
                  onClick={() =>
                    toggleActive.mutate({ id: u.id, is_active: !u.is_active })
                  }
                >
                  {u.is_active ? "Deactivate" : "Reactivate"}
                </button>
                <button
                  className="rounded border px-2 py-1 text-xs"
                  onClick={() => handleResetPassword(u.id, u.username)}
                >
                  Reset password
                </button>
                <button
                  className="rounded border px-2 py-1 text-xs"
                  onClick={() => impersonate.mutate({ userId: u.id, username: u.username })}
                >
                  View as
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <section className="space-y-4 rounded-lg border p-6">
        <h2 className="text-base font-medium">Create user</h2>
        <div className="flex flex-wrap gap-3">
          <input
            placeholder="Username"
            className="rounded border px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            className="rounded border px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          <select
            className="rounded border px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
            value={newRole}
            onChange={(e) => setNewRole(e.target.value as "user" | "admin")}
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
          <button
            className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-gray-900"
            disabled={createUser.isPending}
            onClick={() => createUser.mutate()}
          >
            {createUser.isPending ? "Creating..." : "Create"}
          </button>
        </div>
        {createError && <p className="text-sm text-red-500">{createError}</p>}
      </section>
    </div>
  );
}
