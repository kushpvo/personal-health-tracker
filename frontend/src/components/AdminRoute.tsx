import { Navigate, Outlet } from "react-router-dom";
import { getToken, parseToken } from "../lib/auth";

export default function AdminRoute() {
  const token = getToken();
  if (!token) return <Navigate to="/login" replace />;
  const payload = parseToken(token);
  if (!payload || payload.role !== "admin") return <Navigate to="/" replace />;
  return <Outlet />;
}
