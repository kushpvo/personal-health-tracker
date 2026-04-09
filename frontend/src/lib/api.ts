const BASE = "/api";

export interface ReportListItem {
  id: number;
  report_name: string | null;
  original_filename: string;
  sample_date: string | null;
  uploaded_at: string;
  status: string;
  result_count: number;
}

export interface ReportStatus {
  id: number;
  status: string;
  error_message: string | null;
}

export interface BiomarkerInfo {
  id: number;
  name: string;
  category: string | null;
  default_unit: string | null;
  optimal_min: number | null;
  optimal_max: number | null;
  sufficient_min: number | null;
  sufficient_max: number | null;
}

export interface BiomarkerSummary {
  biomarker: BiomarkerInfo;
  latest_value: number;
  latest_unit: string;
  latest_date: string | null;
  latest_zone: "optimal" | "sufficient" | "out_of_range" | "unknown";
  result_count: number;
}

export interface ResultPoint {
  id: number;
  report_id: number;
  report_name: string | null;
  sample_date: string | null;
  value: number;
  unit: string;
  zone: "optimal" | "sufficient" | "out_of_range" | "unknown";
}

export interface BiomarkerDetail {
  biomarker: BiomarkerInfo;
  results: ResultPoint[];
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

export const api = {
  reports: {
    list: () => get<ReportListItem[]>("/reports"),
    status: (id: number) => get<ReportStatus>(`/reports/${id}/status`),
    downloadUrl: (id: number) => `${BASE}/reports/${id}/download`,
    delete: (id: number) =>
      fetch(`${BASE}/reports/${id}`, { method: "DELETE" }),
    upload: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return fetch(`${BASE}/reports`, { method: "POST", body: form }).then(
        async (res) => {
          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail ?? "Upload failed");
          }
          return res.json() as Promise<{ id: number; status: string }>;
        }
      );
    },
  },
  biomarkers: {
    summary: () => get<BiomarkerSummary[]>("/biomarkers/summary"),
    detail: (id: number) => get<BiomarkerDetail>(`/biomarkers/${id}`),
  },
};
