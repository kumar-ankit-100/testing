/**
 * Shared fetch wrapper — the only module that calls fetch() directly
 * (E3-S4 introduces this; every later UI story's api/*.ts reuses it).
 *
 * API layer (this is the frontend's Repository-equivalent boundary, per
 * folder-structure.md's "Layering note").
 */

import { API_BASE_URL } from "../config/env";
import type { ApiErrorEnvelope } from "../types/api";

export class ApiError extends Error {
  readonly reasonCode: string;
  readonly status: number;

  constructor(status: number, reasonCode: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.reasonCode = reasonCode;
  }
}

function isApiErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof (value as { error?: unknown }).error === "object"
  );
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  const body: unknown = await response.json();

  if (!response.ok) {
    if (isApiErrorEnvelope(body)) {
      throw new ApiError(response.status, body.error.reason_code, body.error.message);
    }
    throw new ApiError(response.status, "UNKNOWN", "Request failed");
  }

  return body as T;
}
