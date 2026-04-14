import { Navigate, Outlet } from "react-router-dom";
import { getToken } from "../lib/auth";

export default function ProtectedRoute() {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <Outlet />;
}
