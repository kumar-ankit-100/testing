/**
 * Auth login API call (E1-S6/E2-S5).
 *
 * API layer.
 */

import { apiFetch } from "./client";
import type {
  LoginRequest,
  LoginResponse,
  RegisterStaffRequest,
  RegisterStaffResponse,
} from "../types/api";

export async function login(request: LoginRequest): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function registerStaff(
  request: RegisterStaffRequest,
): Promise<RegisterStaffResponse> {
  return apiFetch<RegisterStaffResponse>("/api/auth/register-staff", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
