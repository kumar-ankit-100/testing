/**
 * Auth session hook (E1-S6/E2-S5): calls POST /api/auth/login and stores
 * the returned token/role/subscriber_id, so other api/*.ts calls attach
 * it as a bearer token automatically (via api/client.ts) rather than
 * calling the API unauthenticated.
 *
 * Service layer — imports Types, Config, and api/.
 */

import { useCallback, useState } from "react";

import { login as loginApi } from "../api/authApi";
import {
  clearStoredSession,
  getStoredRole,
  getStoredSubscriberId,
  getStoredToken,
  setStoredSession,
} from "../config/authStorage";
import type { Role } from "../types/domain";
import type { LoginRequest } from "../types/api";

export interface AuthState {
  token: string | null;
  role: Role | null;
  subscriberId: string | null;
  isAuthenticated: boolean;
}

export interface UseAuthResult extends AuthState {
  login: (request: LoginRequest) => Promise<boolean>;
  logout: () => void;
}

function readState(): AuthState {
  const token = getStoredToken();
  return {
    token,
    role: getStoredRole(),
    subscriberId: getStoredSubscriberId(),
    isAuthenticated: token !== null,
  };
}

export function useAuth(): UseAuthResult {
  const [state, setState] = useState<AuthState>(readState);

  const login = useCallback(async (request: LoginRequest): Promise<boolean> => {
    try {
      const response = await loginApi(request);
      setStoredSession(response.access_token, response.role, response.subscriber_id);
      setState({
        token: response.access_token,
        role: response.role,
        subscriberId: response.subscriber_id,
        isAuthenticated: true,
      });
      return true;
    } catch {
      return false;
    }
  }, []);

  const logout = useCallback((): void => {
    clearStoredSession();
    setState({ token: null, role: null, subscriberId: null, isAuthenticated: false });
  }, []);

  return { ...state, login, logout };
}
