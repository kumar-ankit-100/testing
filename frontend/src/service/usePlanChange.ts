/**
 * Plan change hook (E4-S5): preview a pro-rata amount before committing
 * to a plan change, without persisting anything until commit is called.
 *
 * Service layer — imports Types, Config, and api/.
 */

import { useCallback, useState } from "react";

import { ApiError } from "../api/client";
import { commitPlanChange, previewPlanChange } from "../api/planChangeApi";
import type { DecimalString } from "../types/api";

export interface UsePlanChangeResult {
  previewAmount: DecimalString | null;
  committedBillingRecordId: string | null;
  error: string | null;
  isSubmitting: boolean;
  preview: (subscriptionId: string, targetPlanVersionId: string) => Promise<void>;
  commit: (subscriptionId: string, targetPlanVersionId: string) => Promise<void>;
  reset: () => void;
}

export function usePlanChange(): UsePlanChangeResult {
  const [previewAmount, setPreviewAmount] = useState<DecimalString | null>(null);
  const [committedBillingRecordId, setCommittedBillingRecordId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const preview = useCallback(
    async (subscriptionId: string, targetPlanVersionId: string): Promise<void> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const response = await previewPlanChange(subscriptionId, {
          target_plan_version_id: targetPlanVersionId,
        });
        setPreviewAmount(response.pro_rata_amount);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Preview failed");
      } finally {
        setIsSubmitting(false);
      }
    },
    [],
  );

  const commit = useCallback(
    async (subscriptionId: string, targetPlanVersionId: string): Promise<void> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const response = await commitPlanChange(subscriptionId, {
          target_plan_version_id: targetPlanVersionId,
        });
        setCommittedBillingRecordId(response.billing_record_id);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Commit failed");
      } finally {
        setIsSubmitting(false);
      }
    },
    [],
  );

  const reset = useCallback((): void => {
    setPreviewAmount(null);
    setCommittedBillingRecordId(null);
    setError(null);
  }, []);

  return { previewAmount, committedBillingRecordId, error, isSubmitting, preview, commit, reset };
}
