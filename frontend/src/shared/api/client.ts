/**
 * Klien API. Token akses disimpan di memori (bukan localStorage) dan diperbarui lewat cookie penyegar
 * HttpOnly; 401 memicu satu kali penyegaran lalu pengulangan permintaan.
 */
export const API = "/api/v1";

export interface GalatDetail {
  kolom?: string;
  pesan?: string;
  [k: string]: unknown;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: GalatDetail[] = [],
    public requestId?: string,
  ) {
    super(message);
  }
}

let accessToken: string | null = null;
let onSessionExpired: (() => void) | null = null;
let refreshing: Promise<boolean> | null = null;

export const setAccessToken = (t: string | null) => {
  accessToken = t;
};
export const getAccessToken = () => accessToken;
export const setOnSessionExpired = (fn: (() => void) | null) => {
  onSessionExpired = fn;
};

export type Query = Record<string, string | number | boolean | null | undefined>;

function url(path: string, query?: Query): string {
  const q = new URLSearchParams();
  Object.entries(query ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
  });
  const s = q.toString();
  return `${API}${path}${s ? `?${s}` : ""}`;
}

async function parseError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json();
    const e = body.error ?? {};
    return new ApiError(res.status, e.code ?? "GALAT", e.message ?? res.statusText, e.details ?? [], e.request_id);
  } catch {
    return new ApiError(res.status, "GALAT", res.statusText || "Terjadi kesalahan pada server.");
  }
}

/** Menukar cookie penyegar dengan token akses baru. Satu permintaan bersama bila dipanggil bersamaan. */
export function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = fetch(`${API}/auth/refresh`, { method: "POST", credentials: "same-origin" })
      .then(async (res) => {
        if (!res.ok) return false;
        const body = await res.json();
        accessToken = body.access_token;
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

interface Options {
  method?: string;
  body?: unknown;
  query?: Query;
  form?: FormData;
  retry?: boolean;
}

export async function request<T = unknown>(path: string, opts: Options = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  const res = await fetch(url(path, opts.query), { method: opts.method ?? "GET", headers, body, credentials: "same-origin" });
  if (res.status === 401 && opts.retry !== false && !path.startsWith("/auth/")) {
    if (await refreshSession()) return request<T>(path, { ...opts, retry: false });
    onSessionExpired?.();
  }
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T = any>(path: string, query?: Query) => request<T>(path, { query }),
  post: <T = any>(path: string, body?: unknown, query?: Query) => request<T>(path, { method: "POST", body: body ?? {}, query }),
  put: <T = any>(path: string, body?: unknown, query?: Query) => request<T>(path, { method: "PUT", body: body ?? {}, query }),
  patch: <T = any>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  del: <T = any>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T = any>(path: string, form: FormData, query?: Query) => request<T>(path, { method: "POST", form, query }),
};

/** Unggah langsung ke penyimpanan lewat URL sementara bertanda tangan (berkas tidak melewati API). */
export async function putToStorage(url_: string, file: File, mime: string): Promise<void> {
  const res = await fetch(url_, { method: "PUT", body: file, headers: { "Content-Type": mime } });
  if (!res.ok) throw new ApiError(res.status, "UNGGAH_GAGAL", "Berkas gagal diunggah ke penyimpanan.");
}
