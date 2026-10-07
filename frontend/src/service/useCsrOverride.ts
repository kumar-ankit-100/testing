/**
 * CSR override hook (E6-S4): submits an override for a rejected
 * activation or plan-change, surfacing the resulting state/error.
 *
 * Service layer — imports Types, Config, and api/.
 */

import { useCallback, useState } from "react";

import { ApiError } from "../api/client";
import { overrideActivation, overridePlanChange } from "../api/csrApi";

export interface UseCsrOverrideResult {
  result: string | null;
  error: string | null;
  isSubmitting: boolean;
  overrideActivationAction: (
    subscriberId: string,
    dealerCode: string,
    reasonCode: string,
    originalRejectionReason: string,
  ) => Promise<void>;
  overridePlanChangeAction: (
    subscriptionId: string,
    targetPlanVersionId: string,
    reasonCode: string,
    originalRejectionReason: string,
  ) => Promise<void>;
}

export function useCsrOverride(): UseCsrOverrideResult {
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const overrideActivationAction = useCallback(
    async (
      subscriberId: string,
      dealerCode: string,
      reasonCode: string,
      originalRejectionReason: string,
    ): Promise<void> => {
      setIsSubmitting(true);
      setError(null);
      setResult(null);
      try {
        const response = await overrideActivation(subscriberId, {
          dealer_code: dealerCode,
          reason_code: reasonCode,
          original_rejection_reason: originalRejectionReason,
        });
        setResult(`Subscriber ${response.subscriber_id} is now ${response.state}`);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Override failed");
      } finally {
        setIsSubmitting(false);
      }
    },
    [],
  );

  const overridePlanChangeAction = useCallback(
    async (
      subscriptionId: string,
      targetPlanVersionId: string,
      reasonCode: string,
      originalRejectionReason: string,
    ): Promise<void> => {
      setIsSubmitting(true);
      setError(null);
      setResult(null);
      try {
        const response = await overridePlanChange(subscriptionId, {
          target_plan_version_id: targetPlanVersionId,
          reason_code: reasonCode,
          original_rejection_reason: originalRejectionReason,
        });
        setResult(
          `Plan change committed — billing record ${response.billing_record_id}, pro-rata ${response.pro_rata_amount}`,
        );
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Override failed");
      } finally {
        setIsSubmitting(false);
      }
    },
    [],
  );

  return { result, error, isSubmitting, overrideActivationAction, overridePlanChangeAction };
}
