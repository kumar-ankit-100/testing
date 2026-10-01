/**
 * Registration hook (E2-S5): submits mobile_number/identity_proof_ref/
 * plan_type to the registration endpoint and exposes the resulting
 * subscriber_id/subscription_id/state so a caller can move on to the
 * activation status page.
 *
 * Service layer — imports Types, Config, and api/.
 */

import { useCallback, useState } from "react";

import { ApiError } from "../api/client";
import { registerSubscriber } from "../api/subscriberApi";
import type { PlanType } from "../types/domain";
import type { RegisterSubscriberResponse } from "../types/api";

export interface UseRegistrationResult {
  result: RegisterSubscriberResponse | null;
  error: string | null;
  isSubmitting: boolean;
  register: (
    mobileNumber: string,
    identityProofRef: string,
    planType: PlanType,
  ) => Promise<RegisterSubscriberResponse | null>;
}

export function useRegistration(): UseRegistrationResult {
  const [result, setResult] = useState<RegisterSubscriberResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const register = useCallback(
    async (
      mobileNumber: string,
      identityProofRef: string,
      planType: PlanType,
    ): Promise<RegisterSubscriberResponse | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const response = await registerSubscriber({
          mobile_number: mobileNumber,
          identity_proof_ref: identityProofRef,
          plan_type: planType,
        });
        setResult(response);
        return response;
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Registration failed");
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [],
  );

  return { result, error, isSubmitting, register };
}
