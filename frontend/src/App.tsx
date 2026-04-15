import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import AdminRoute from "./components/AdminRoute";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Admin from "./pages/Admin";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";
import Setup from "./pages/Setup";
import Upload from "./pages/Upload";
import BiomarkerDetail from "./pages/BiomarkerDetail";
import ReportDashboard from "./pages/ReportDashboard";
import ReviewReport from "./pages/ReviewReport";
import UnknownBiomarkers from "./pages/UnknownBiomarkers";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="login" element={<Login />} />
        <Route path="setup" element={<Setup />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="reports" element={<Reports />} />
            <Route path="reports/upload" element={<Upload />} />
            <Route path="reports/:id" element={<ReportDashboard />} />
            <Route path="reports/:id/review" element={<ReviewReport />} />
            <Route path="biomarkers/:id" element={<BiomarkerDetail />} />
            <Route path="settings" element={<Settings />} />
            <Route path="unknown-biomarkers" element={<UnknownBiomarkers />} />
            <Route element={<AdminRoute />}>
              <Route path="admin" element={<Admin />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
