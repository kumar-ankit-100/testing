/**
 * Activation status hook (E2-S5): submits a dealer_code to the
 * activation endpoint and exposes the outcome — ACTIVE on success, or
 * the specific reason_code/message on rejection (AC-2/AC-3).
 *
 * Service layer — imports Types, Config, and api/.
 */

import { useCallback, useState } from "react";

import { ApiError } from "../api/client";
import { activateSubscriber } from "../api/subscriberApi";
import type { SubscriberState } from "../types/domain";

export interface ActivationOutcome {
  state: SubscriberState | null;
  reasonCode: string | null;
  message: string | null;
}

export interface UseActivationStatusResult extends ActivationOutcome {
  isSubmitting: boolean;
  activate: (subscriberId: string, dealerCode: string) => Promise<void>;
}

export function useActivationStatus(): UseActivationStatusResult {
  const [state, setState] = useState<SubscriberState | null>(null);
  const [reasonCode, setReasonCode] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const activate = useCallback(
    async (subscriberId: string, dealerCode: string): Promise<void> => {
      setIsSubmitting(true);
      setReasonCode(null);
      setMessage(null);
      try {
        const response = await activateSubscriber(subscriberId, { dealer_code: dealerCode });
        setState(response.state);
      } catch (err) {
        if (err instanceof ApiError) {
          setReasonCode(err.reasonCode);
          setMessage(err.message);
        } else {
          setReasonCode("UNKNOWN");
          setMessage("Activation failed");
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [],
  );

  return { state, reasonCode, message, isSubmitting, activate };
}
