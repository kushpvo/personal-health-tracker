import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Reports from "./pages/Reports";
import Upload from "./pages/Upload";
import BiomarkerDetail from "./pages/BiomarkerDetail";
import ReviewReport from "./pages/ReviewReport";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="reports" element={<Reports />} />
          <Route path="reports/upload" element={<Upload />} />
          <Route path="reports/:id/review" element={<ReviewReport />} />
          <Route path="biomarkers/:id" element={<BiomarkerDetail />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
