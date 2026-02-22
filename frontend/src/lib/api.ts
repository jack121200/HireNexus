import { getAuthToken } from "./auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

type RequestOptions = RequestInit & {
  auth?: boolean;
};

const buildHeaders = (options?: RequestOptions) => {
  const headers = new Headers(options?.headers || {});
  if (!headers.has("Content-Type") && !(options?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (options?.auth !== false) {
    const token = getAuthToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }
  return headers;
};

export const apiFetch = async <T>(path: string, options: RequestOptions = {}): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: buildHeaders(options),
  });

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const nestedErrors =
      typeof payload === "object" && payload !== null
        ? (payload as { error?: { data?: { errors?: Array<{ msg?: string }> } } })?.error?.data?.errors
        : null;
    const detailMessage =
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      Array.isArray((payload as { detail?: unknown }).detail)
        ? (payload as { detail: Array<{ msg?: string }> }).detail
            .map((item) => item?.msg)
            .filter(Boolean)
            .join(", ")
        : null;
    const nestedMessage = Array.isArray(nestedErrors)
      ? nestedErrors
          .map((item) => item?.msg)
          .filter(Boolean)
          .join(", ")
      : null;
    const message =
      typeof payload === "string"
        ? payload
        : detailMessage ||
          nestedMessage ||
          (payload as { error?: { detail?: string } })?.error?.detail ||
          "Request failed";
    throw new ApiError(message, response.status, payload);
  }

  return payload as T;
};

export const apiUpload = async <T>(path: string, formData: FormData): Promise<T> => {
  return apiFetch<T>(path, {
    method: "POST",
    body: formData,
  });
};
