/**
 * Auth token storage (E1-S6/E2-S5). Config layer — the single source of
 * truth both api/client.ts (reads, to attach the bearer header) and
 * service/useAuth.ts (writes, on login/logout) rely on, so client.ts
 * never has to import upward from service/.
 */

import type { Role } from "../types/domain";

const TOKEN_KEY = "telcolane_access_token";
const ROLE_KEY = "telcolane_role";
const SUBSCRIBER_ID_KEY = "telcolane_subscriber_id";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredRole(): Role | null {
  return localStorage.getItem(ROLE_KEY) as Role | null;
}

export function getStoredSubscriberId(): string | null {
  return localStorage.getItem(SUBSCRIBER_ID_KEY);
}

export function setStoredSession(
  token: string,
  role: Role,
  subscriberId: string | null,
): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(ROLE_KEY, role);
  if (subscriberId === null) {
    localStorage.removeItem(SUBSCRIBER_ID_KEY);
  } else {
    localStorage.setItem(SUBSCRIBER_ID_KEY, subscriberId);
  }
}

export function clearStoredSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(SUBSCRIBER_ID_KEY);
}
