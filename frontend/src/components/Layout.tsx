import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Activity, AlertCircle, ChevronLeft, ChevronRight, FileDown, FileText, LogOut, Moon, Pill, Settings, Shield, Sun, Upload } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { cn } from "../lib/utils";
import { api } from "../lib/api";
import {
  getImpersonatedUsername,
  getToken,
  isImpersonating,
  logout,
  parseToken,
  stopImpersonation,
} from "../lib/auth";

export default function Layout() {
  const navigate = useNavigate();
  const [isDark, setIsDark] = useState(
    document.documentElement.classList.contains("dark")
  );
  const [isCollapsed, setIsCollapsed] = useState(
    localStorage.getItem("sidebarCollapsed") === "true"
  );

  function handleCollapseToggle() {
    const next = !isCollapsed;
    setIsCollapsed(next);
    localStorage.setItem("sidebarCollapsed", String(next));
  }

  function handleThemeToggle() {
    const next = !isDark;
    setIsDark(next);
    if (next) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }
  const { data: unknowns = [] } = useQuery({
    queryKey: ["unknowns"],
    queryFn: api.unknowns.list,
    staleTime: 60_000,
  });

  const token = getToken();
  const payload = token ? parseToken(token) : null;
  const impersonating = isImpersonating();
  const impersonatedUsername = getImpersonatedUsername();

  function handleLogout() {
    logout().then(() => navigate("/login", { replace: true }));
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
    { to: "/supplements", label: "Supplements", icon: Pill, end: false },
    { to: "/export", label: "Custom Export", icon: FileDown, end: false },
    { to: "/settings", label: "Settings", icon: Settings, end: false },
    ...(unknowns.length > 0
      ? [{ to: "/unknown-biomarkers", label: `Unknowns (${unknowns.length})`, icon: AlertCircle, end: false }]
      : []),
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
        <aside className={cn(
          "flex shrink-0 flex-col border-r border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-900 transition-all duration-200",
          isCollapsed ? "w-14" : "w-56"
        )}>
          <div className={cn("flex items-center py-6", isCollapsed ? "justify-center px-0" : "justify-between px-5")}>
            {!isCollapsed && (
              <div>
                <h1 className="text-lg font-semibold tracking-tight">Lab Tracker</h1>
                {payload && (
                  <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                    {payload.role === "admin" ? "Admin" : "User"}
                  </p>
                )}
              </div>
            )}
            <button
              onClick={handleCollapseToggle}
              title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              className="rounded-md p-1.5 text-gray-500 transition-colors hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-700"
            >
              {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </button>
          </div>
          <nav className="flex-1 space-y-1 px-2">
            {navItems.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                title={isCollapsed ? label : undefined}
                className={({ isActive }) =>
                  cn(
                    "flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isCollapsed ? "justify-center gap-0" : "gap-3",
                    isActive
                      ? "bg-gray-200 text-gray-900 dark:bg-gray-700 dark:text-white"
                      : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
                  )
                }
              >
                <Icon size={16} />
                {!isCollapsed && label}
              </NavLink>
            ))}
          </nav>
          <div className="px-2 pb-4 space-y-1">
            <button
              onClick={handleThemeToggle}
              title={isCollapsed ? (isDark ? "Light mode" : "Dark mode") : undefined}
              className={cn(
                "flex w-full items-center rounded-md px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800",
                isCollapsed ? "justify-center gap-0" : "gap-3"
              )}
            >
              {isDark ? <Sun size={16} /> : <Moon size={16} />}
              {!isCollapsed && (isDark ? "Light mode" : "Dark mode")}
            </button>
            <button
              onClick={handleLogout}
              title={isCollapsed ? "Log out" : undefined}
              className={cn(
                "flex w-full items-center rounded-md px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800",
                isCollapsed ? "justify-center gap-0" : "gap-3"
              )}
            >
              <LogOut size={16} />
              {!isCollapsed && "Log out"}
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
