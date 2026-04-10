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
  alternate_units: string[];
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

export interface ReportResultItem {
  id: number;
  raw_name: string;
  value: number;
  unit: string;
  is_flagged_unknown: boolean;
  human_matched: boolean;
  sort_order: number | null;
  biomarker_id: number | null;
  biomarker_name: string | null;
}

export interface BiomarkerListItem {
  id: number;
  name: string;
  category: string | null;
  default_unit: string | null;
  alternate_units: string[];
}

export interface ReviewResultInput {
  id: number;
  value: number;
  unit: string;
  biomarker_id?: number;
}

export interface NewResultInput {
  biomarker_id: number;
  value: number;
  unit: string;
}

export interface ReviewReportInput {
  report_name: string;
  sample_date: string | null;
  results: ReviewResultInput[];
  new_results?: NewResultInput[];
  deleted_result_ids?: number[];
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

export const api = {
  reports: {
    list: () => get<ReportListItem[]>("/reports"),
    summary: (id: number) => get<BiomarkerSummary[]>(`/reports/${id}/summary`),
    status: (id: number) => get<ReportStatus>(`/reports/${id}/status`),
    results: (id: number) => get<ReportResultItem[]>(`/reports/${id}/results`),
    review: (id: number, body: ReviewReportInput) =>
      fetch(`${BASE}/reports/${id}/review`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(async (res) => {
        if (!res.ok) throw new Error(`Review failed: ${res.status}`);
        return res.json();
      }),
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
    list: () => get<BiomarkerListItem[]>("/biomarkers/list"),
    changeDefaultUnit: (id: number, unit: string) =>
      fetch(`${BASE}/biomarkers/${id}/default-unit`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ unit }),
      }).then(async (res) => {
        if (!res.ok) throw new Error(`Change unit failed: ${res.status}`);
        return res.json() as Promise<BiomarkerInfo>;
      }),
  },
};
