/**
 * Staff registration hook: submits username/password/role to the
 * dynamic staff-account-creation endpoint, so CSR/admin/dealer users
 * are no longer limited to the 3 seeded demo accounts.
 *
 * Service layer — imports Types, Config, and api/.
 */

import { useCallback, useState } from "react";

import { ApiError } from "../api/client";
import { registerStaff } from "../api/authApi";
import type { RegisterStaffRequest, RegisterStaffResponse } from "../types/api";

export interface UseStaffRegistrationResult {
  error: string | null;
  isSubmitting: boolean;
  register: (request: RegisterStaffRequest) => Promise<RegisterStaffResponse | null>;
}

export function useStaffRegistration(): UseStaffRegistrationResult {
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const register = useCallback(
    async (request: RegisterStaffRequest): Promise<RegisterStaffResponse | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        return await registerStaff(request);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Registration failed");
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [],
  );

  return { error, isSubmitting, register };
}
