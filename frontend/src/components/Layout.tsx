import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Activity, FileText, LogOut, Settings, Shield, Upload } from "lucide-react";
import { cn } from "../lib/utils";
import {
  clearTokens,
  getImpersonatedUsername,
  getToken,
  isImpersonating,
  parseToken,
  stopImpersonation,
} from "../lib/auth";

export default function Layout() {
  const navigate = useNavigate();
  const token = getToken();
  const payload = token ? parseToken(token) : null;
  const impersonating = isImpersonating();
  const impersonatedUsername = getImpersonatedUsername();

  function handleLogout() {
    clearTokens();
    navigate("/login", { replace: true });
  }

  function handleExitImpersonation() {
    stopImpersonation();
    navigate("/admin");
    window.location.reload();
  }

  const navItems = [
    { to: "/", label: "Dashboard", icon: Activity, end: true },
    { to: "/reports", label: "Reports", icon: FileText, end: false },
    { to: "/reports/upload", label: "Upload", icon: Upload, end: false },
    { to: "/settings", label: "Settings", icon: Settings, end: false },
    ...(payload?.role === "admin"
      ? [{ to: "/admin", label: "Admin", icon: Shield, end: false }]
      : []),
  ];

  return (
    <div className="flex h-screen flex-col">
      {impersonating && payload?.acting_as && (
        <div className="flex w-full items-center justify-between bg-yellow-400 px-4 py-2 text-sm font-medium text-yellow-900">
          <span>Viewing as {impersonatedUsername}</span>
          <button className="font-semibold underline" onClick={handleExitImpersonation}>
            Exit
          </button>
        </div>
      )}
      <div className="flex flex-1">
        <aside className="flex w-56 shrink-0 flex-col border-r border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
          <div className="px-5 py-6">
            <h1 className="text-lg font-semibold tracking-tight">Lab Tracker</h1>
            {payload && (
              <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                {payload.role === "admin" ? "Admin" : "User"}
              </p>
            )}
          </div>
          <nav className="flex-1 space-y-1 px-3">
            {navItems.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-gray-200 text-gray-900 dark:bg-gray-700 dark:text-white"
                      : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
                  )
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="px-3 pb-4">
            <button
              onClick={handleLogout}
              className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
            >
              <LogOut size={16} />
              Log out
            </button>
          </div>
        </aside>
        <main className="flex-1 overflow-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
