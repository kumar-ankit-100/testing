/**
 * Subscription termination hook (E6-S4, CSR/admin-only): terminates a
 * subscription by subscription_id with a mandatory reason_code.
 *
 * Service layer — imports Types, Config, and api/.
 */

import { useCallback, useState } from "react";

import { ApiError } from "../api/client";
import { terminateSubscription } from "../api/lifecycleApi";

export interface UseTerminateResult {
  result: string | null;
  error: string | null;
  isSubmitting: boolean;
  terminate: (subscriptionId: string, reasonCode: string) => Promise<void>;
}

export function useTerminate(): UseTerminateResult {
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const terminate = useCallback(
    async (subscriptionId: string, reasonCode: string): Promise<void> => {
      setIsSubmitting(true);
      setError(null);
      setResult(null);
      try {
        const response = await terminateSubscription(subscriptionId, {
          reason_code: reasonCode,
        });
        setResult(`Subscription ${response.subscription_id} is now ${response.state}`);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Termination failed");
      } finally {
        setIsSubmitting(false);
      }
    },
    [],
  );

  return { result, error, isSubmitting, terminate };
}
