import { clearTokens, getToken, setToken } from "./auth";

const BASE = "/api";

export interface ReportListItem {
  id: number;
  report_name: string | null;
  original_filename: string;
  sample_date: string | null;
  uploaded_at: string;
  status: string;
  result_count: number;
  tags: string | null;
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
  trend_delta: number | null;
  trend_alert: boolean;
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
  notes: string | null;
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
  tags?: string;
  result_notes?: Record<number, string>;
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

export interface SupplementDoseItem {
  id: number;
  dose: number;
  started_on: string;      // YYYY-MM-DD
  ended_on: string | null; // YYYY-MM-DD or null = active
  is_active: boolean;
  date_notes: string | null;
  is_date_approximate: boolean;
}

export interface SupplementLogItem {
  id: number;
  name: string;
  unit: string;
  frequency: string;
  notes: string | null;
  created_at: string;
  doses: SupplementDoseItem[];
}

export interface CreateSupplementInput {
  name: string;
  unit: string;
  frequency: string;
  dose: number;
  started_on: string;
  notes?: string;
  date_notes?: string;
  is_date_approximate?: boolean;
}

export interface UpdateSupplementInput {
  name?: string;
  unit?: string;
  frequency?: string;
  notes?: string;
}

export interface AddDoseInput {
  dose: number;
  started_on: string;
  date_notes?: string;
  is_date_approximate?: boolean;
}

export interface UpdateDoseInput {
  dose?: number;
  started_on?: string;
  ended_on?: string;
  date_notes?: string;
  is_date_approximate?: boolean;
}

export interface UserInfo {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  sex: "male" | "female" | "other" | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

let _refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) return false;
    const data = await res.json();
    setToken(data.access_token);
    return true;
  } catch {
    return false;
  }
}

async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...authHeaders(),
      ...((init.headers as Record<string, string> | undefined) ?? {}),
    },
  });

  if (res.status === 401) {
    if (!_refreshing) {
      _refreshing = tryRefresh().finally(() => { _refreshing = null; });
    }
    const refreshed = await _refreshing;
    if (refreshed) {
      return fetch(`${BASE}${path}`, {
        ...init,
        credentials: "include",
        headers: {
          ...authHeaders(),
          ...((init.headers as Record<string, string> | undefined) ?? {}),
        },
      });
    }
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
    updateProfile: (sex: "male" | "female" | "other" | null) =>
      authFetch("/auth/me/profile", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sex }),
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
        return r.json() as Promise<UserInfo>;
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
      body: { is_active?: boolean; password?: string; sex?: "male" | "female" | "other" | null },
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
    list: (params?: { from_date?: string; to_date?: string }) => {
      const qs = new URLSearchParams();
      if (params?.from_date) qs.set("from_date", params.from_date);
      if (params?.to_date) qs.set("to_date", params.to_date);
      const query = qs.toString();
      return get<ReportListItem[]>(`/reports${query ? `?${query}` : ""}`);
    },
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
    reprocess: (id: number) =>
      authFetch(`/reports/${id}/reprocess`, { method: "POST" }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
        return r.json() as Promise<{ id: number; status: string }>;
      }),
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
    createManual: (): Promise<{ id: number; status: string }> =>
      authFetch("/reports/manual", { method: "POST" }).then(async (res) => {
        if (!res.ok) throw new Error((await res.json()).detail ?? "Failed");
        return res.json() as Promise<{ id: number; status: string }>;
      }),
  },
  export: {
    pdf: async () => {
      const res = await authFetch("/export/pdf");
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `health-summary-${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    },
    customPdf: async (biomarkerIds: number[], supplementIds: number[]) => {
      const res = await authFetch("/export/custom-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ biomarker_ids: biomarkerIds, supplement_ids: supplementIds }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Export failed" }));
        throw new Error(err.detail ?? "Export failed");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `health-custom-export-${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
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
  supplements: {
    list: () => get<SupplementLogItem[]>("/supplements"),
    activeDuring: (from_date: string, to_date: string) =>
      get<SupplementLogItem[]>(`/supplements/active-during?from_date=${from_date}&to_date=${to_date}`),
    create: (body: CreateSupplementInput) =>
      authFetch("/supplements", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
        return r.json() as Promise<SupplementLogItem>;
      }),
    update: (id: number, body: UpdateSupplementInput) =>
      authFetch(`/supplements/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
        return r.json() as Promise<SupplementLogItem>;
      }),
    delete: (id: number) =>
      authFetch(`/supplements/${id}`, { method: "DELETE" }),
    addDose: (id: number, body: AddDoseInput) =>
      authFetch(`/supplements/${id}/doses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
        return r.json() as Promise<SupplementLogItem>;
      }),
    updateDose: (id: number, doseId: number, body: UpdateDoseInput) =>
      authFetch(`/supplements/${id}/doses/${doseId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
        return r.json() as Promise<SupplementLogItem>;
      }),
    deleteDose: (id: number, doseId: number) =>
      authFetch(`/supplements/${id}/doses/${doseId}`, { method: "DELETE" }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail ?? "Failed");
        return r.json() as Promise<SupplementLogItem>;
      }),
  },
  biomarkers: {
    summary: (params?: { search?: string; category?: string }) => {
      const qs = new URLSearchParams();
      if (params?.search) qs.set("search", params.search);
      if (params?.category) qs.set("category", params.category);
      const query = qs.toString();
      return get<BiomarkerSummary[]>(`/biomarkers/summary${query ? `?${query}` : ""}`);
    },
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
