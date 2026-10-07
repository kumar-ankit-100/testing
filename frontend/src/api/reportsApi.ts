/**
 * Admin reporting dashboard API call (E7-S3).
 *
 * API layer.
 */

import { apiFetch } from "./client";
import type { AdminDashboardResponse } from "../types/api";

export async function getAdminDashboard(): Promise<AdminDashboardResponse> {
  return apiFetch<AdminDashboardResponse>("/api/admin/reports/dashboard");
}
