import { clearTokens, getToken } from "./auth";

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

export interface UnknownBiomarkerItem {
  id: number;
  raw_name: string;
  raw_unit: string | null;
  times_seen: number;
  first_seen_at: string;
  last_seen_at: string;
  resolved_biomarker_id: number | null;
}

export interface UserInfo {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...authHeaders(),
      ...((init.headers as Record<string, string> | undefined) ?? {}),
    },
  });
  if (res.status === 401) {
    clearTokens();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  return res;
}

async function get<T>(path: string): Promise<T> {
  const res = await authFetch(path);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

export const api = {
  auth: {
    setupRequired: (): Promise<{ required: boolean }> =>
      fetch(`${BASE}/auth/setup-required`).then((r) => r.json()),
    setup: (username: string, password: string): Promise<TokenResponse> =>
      fetch(`${BASE}/auth/setup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? "Setup failed");
        return r.json();
      }),
    login: (username: string, password: string): Promise<TokenResponse> =>
      fetch(`${BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? "Login failed");
        return r.json();
      }),
    me: (): Promise<UserInfo> => get("/auth/me"),
    changePassword: (current_password: string, new_password: string) =>
      authFetch("/auth/me/password", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password, new_password }),
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
        return r.json();
      }),
  },
  admin: {
    listUsers: (): Promise<UserInfo[]> => get("/admin/users"),
    createUser: (
      username: string,
      password: string,
      role: string,
    ): Promise<UserInfo> =>
      authFetch("/admin/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, role }),
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
        return r.json();
      }),
    updateUser: (
      id: number,
      body: { is_active?: boolean; password?: string },
    ): Promise<UserInfo> =>
      authFetch(`/admin/users/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
        return r.json();
      }),
    impersonate: (userId: number): Promise<TokenResponse> =>
      authFetch(`/admin/impersonate/${userId}`, { method: "POST" }).then(
        async (r) => {
          if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
          return r.json();
        },
      ),
  },
  reports: {
    list: () => get<ReportListItem[]>("/reports"),
    summary: (id: number) => get<BiomarkerSummary[]>(`/reports/${id}/summary`),
    status: (id: number) => get<ReportStatus>(`/reports/${id}/status`),
    results: (id: number) => get<ReportResultItem[]>(`/reports/${id}/results`),
    review: (id: number, body: ReviewReportInput) =>
      authFetch(`/reports/${id}/review`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(async (res) => {
        if (!res.ok) throw new Error(`Review failed: ${res.status}`);
        return res.json();
      }),
    download: async (id: number, filename: string) => {
      const res = await authFetch(`/reports/${id}/download`);
      if (!res.ok) throw new Error(`Download failed: ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    },
    delete: (id: number) => authFetch(`/reports/${id}`, { method: "DELETE" }),
    upload: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return authFetch("/reports", { method: "POST", body: form }).then(
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
  unknowns: {
    list: () => get<UnknownBiomarkerItem[]>("/unknowns"),
    resolve: (id: number, biomarker_id: number) =>
      authFetch(`/unknowns/${id}/resolve`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ biomarker_id }),
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
        return r.json() as Promise<UnknownBiomarkerItem>;
      }),
  },
  biomarkers: {
    summary: () => get<BiomarkerSummary[]>("/biomarkers/summary"),
    detail: (id: number) => get<BiomarkerDetail>(`/biomarkers/${id}`),
    list: () => get<BiomarkerListItem[]>("/biomarkers/list"),
    changeDefaultUnit: (id: number, unit: string) =>
      authFetch(`/biomarkers/${id}/default-unit`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ unit }),
      }).then(async (res) => {
        if (!res.ok) throw new Error(`Change unit failed: ${res.status}`);
        return res.json() as Promise<BiomarkerInfo>;
      }),
  },
};
