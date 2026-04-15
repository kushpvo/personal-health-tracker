export const TOKEN_KEY = "auth_token";
export const ADMIN_TOKEN_KEY = "admin_token";
export const IMPERSONATED_USERNAME_KEY = "impersonated_username";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ADMIN_TOKEN_KEY);
  localStorage.removeItem(IMPERSONATED_USERNAME_KEY);
}

export function getAdminToken(): string | null {
  return localStorage.getItem(ADMIN_TOKEN_KEY);
}

export function getImpersonatedUsername(): string | null {
  return localStorage.getItem(IMPERSONATED_USERNAME_KEY);
}

export function startImpersonation(impersonationToken: string, username: string): void {
  const current = getToken();
  if (current) {
    localStorage.setItem(ADMIN_TOKEN_KEY, current);
  }
  setToken(impersonationToken);
  localStorage.setItem(IMPERSONATED_USERNAME_KEY, username);
}

export function stopImpersonation(): void {
  const adminToken = getAdminToken();
  if (adminToken) {
    setToken(adminToken);
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    localStorage.removeItem(IMPERSONATED_USERNAME_KEY);
  }
}

export function isImpersonating(): boolean {
  return !!getAdminToken();
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
  clearTokens();
}

export interface TokenPayload {
  sub: string;
  role: "admin" | "user";
  acting_as: string | null;
  exp: number;
}

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  return atob(padded);
}

export function parseToken(token: string): TokenPayload | null {
  try {
    const [, payload] = token.split(".");
    if (!payload) return null;
    return JSON.parse(decodeBase64Url(payload)) as TokenPayload;
  } catch {
    return null;
  }
}
