/**
 * Subscription lifecycle hook (E5-S5): suspend/resume/port-out actions
 * for a subscriber managing their own subscription, surfacing the
 * resulting state and any error.
 *
 * Service layer — imports Types, Config, and api/.
 */

import { useCallback, useState } from "react";

import { cancelPortOut, requestPortOut, resumeSubscription, suspendSubscription } from "../api/lifecycleApi";
import { ApiError } from "../api/client";
import type { SubscriberState } from "../types/domain";

export interface UseLifecycleResult {
  state: SubscriberState | null;
  coolingPeriodEndAt: string | null;
  error: string | null;
  isSubmitting: boolean;
  suspend: (subscriptionId: string) => Promise<void>;
  resume: (subscriptionId: string) => Promise<void>;
  requestPortOutAction: (subscriptionId: string) => Promise<void>;
  cancelPortOutAction: (subscriptionId: string) => Promise<void>;
}

export function useLifecycle(initialState: SubscriberState): UseLifecycleResult {
  const [state, setState] = useState<SubscriberState | null>(initialState);
  const [coolingPeriodEndAt, setCoolingPeriodEndAt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function withErrorHandling(
    action: () => Promise<void>,
  ): () => Promise<void> {
    return async () => {
      setIsSubmitting(true);
      setError(null);
      try {
        await action();
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Request failed");
      } finally {
        setIsSubmitting(false);
      }
    };
  }

  const suspend = useCallback(
    (subscriptionId: string) =>
      withErrorHandling(async () => {
        const response = await suspendSubscription(subscriptionId);
        setState(response.state);
      })(),
    [],
  );

  const resume = useCallback(
    (subscriptionId: string) =>
      withErrorHandling(async () => {
        const response = await resumeSubscription(subscriptionId);
        setState(response.state);
      })(),
    [],
  );

  const requestPortOutAction = useCallback(
    (subscriptionId: string) =>
      withErrorHandling(async () => {
        const response = await requestPortOut(subscriptionId);
        setState("PORT_OUT_REQUESTED");
        setCoolingPeriodEndAt(response.cooling_period_end_at);
      })(),
    [],
  );

  const cancelPortOutAction = useCallback(
    (subscriptionId: string) =>
      withErrorHandling(async () => {
        const response = await cancelPortOut(subscriptionId);
        setState(response.state);
        setCoolingPeriodEndAt(null);
      })(),
    [],
  );

  return {
    state,
    coolingPeriodEndAt,
    error,
    isSubmitting,
    suspend,
    resume,
    requestPortOutAction,
    cancelPortOutAction,
  };
}
