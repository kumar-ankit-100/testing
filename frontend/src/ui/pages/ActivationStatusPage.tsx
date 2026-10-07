/**
 * Activation status page (E2-S5 AC-2/AC-3): submits a dealer code to
 * the activation endpoint and displays the outcome — a success badge
 * with state ACTIVE, or the specific rejection reason code/message.
 *
 * Once ACTIVE, renders the subscriber's own subscription-management
 * panel (E5-S5 suspend/resume/port-out; E4-S5 plan change preview and
 * commit) — subscription_id comes from authStorage (set once at
 * registration, E2-S5/E4-S5/E5-S5's shared source of truth) rather than
 * a prop, since this page's props contract (just subscriberId) predates
 * these two stories and activate's own response never carries it.
 *
 * UI layer.
 */

import { useState } from "react";

import { getStoredSubscriptionId } from "../../config/authStorage";
import { KNOWN_DEALER_CODES } from "../../config/dealerCodes";
import { useActivationStatus } from "../../service/useActivationStatus";
import { useLifecycle } from "../../service/useLifecycle";
import { usePlanChange } from "../../service/usePlanChange";

export interface ActivationStatusPageProps {
  subscriberId: string;
}

export function ActivationStatusPage({
  subscriberId,
}: ActivationStatusPageProps): React.JSX.Element {
  const { state, reasonCode, message, isSubmitting, activate } = useActivationStatus();
  const [dealerCode, setDealerCode] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    await activate(subscriberId, dealerCode);
  }

  return (
    <div className="auth-shell">
      <h1>Activate your subscription</h1>

      {state === "ACTIVE" ? (
        <>
          <p data-testid="activation-success" role="status">
            Your subscription is now <strong>ACTIVE</strong>.
          </p>
          <SubscriptionManagementPanel />
        </>
      ) : (
        <form onSubmit={(event) => void handleSubmit(event)}>
          <label htmlFor="dealer-code">Dealer code</label>
          <input
            id="dealer-code"
            value={dealerCode}
            onChange={(event) => setDealerCode(event.target.value)}
            list="known-dealer-codes"
            required
          />
          <datalist id="known-dealer-codes">
            {KNOWN_DEALER_CODES.map(({ code, name }) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </datalist>
          <p className="field-hint">
            Valid dealer codes:{" "}
            {KNOWN_DEALER_CODES.map(({ code }) => code).join(", ")}
          </p>

          {reasonCode !== null && (
            <p role="alert" data-testid="activation-rejection" data-reason-code={reasonCode}>
              {message}
            </p>
          )}

          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Activating…" : "Activate"}
          </button>
        </form>
      )}
    </div>
  );
}

function SubscriptionManagementPanel(): React.JSX.Element {
  const subscriptionId = getStoredSubscriptionId();
  const lifecycle = useLifecycle("ACTIVE");
  const planChange = usePlanChange();
  const [targetPlanVersionId, setTargetPlanVersionId] = useState("");

  if (subscriptionId === null) {
    return <></>;
  }

  return (
    <div className="panel" data-testid="subscription-management-panel">
      <h2>Manage your subscription</h2>

      {lifecycle.error !== null && <p role="alert">{lifecycle.error}</p>}
      <p>
        Current state: <strong>{lifecycle.state}</strong>
      </p>

      {lifecycle.state === "ACTIVE" && (
        <>
          <button
            type="button"
            disabled={lifecycle.isSubmitting}
            onClick={() => void lifecycle.suspend(subscriptionId)}
          >
            Suspend
          </button>
          <button
            type="button"
            disabled={lifecycle.isSubmitting}
            onClick={() => void lifecycle.requestPortOutAction(subscriptionId)}
          >
            Request port-out
          </button>
        </>
      )}

      {lifecycle.state === "SUSPENDED" && (
        <button
          type="button"
          disabled={lifecycle.isSubmitting}
          onClick={() => void lifecycle.resume(subscriptionId)}
        >
          Resume
        </button>
      )}

      {lifecycle.state === "PORT_OUT_REQUESTED" && (
        <>
          {lifecycle.coolingPeriodEndAt !== null && (
            <p>Cooling period ends: {lifecycle.coolingPeriodEndAt}</p>
          )}
          <button
            type="button"
            disabled={lifecycle.isSubmitting}
            onClick={() => void lifecycle.cancelPortOutAction(subscriptionId)}
          >
            Cancel port-out
          </button>
        </>
      )}

      <h3>Change plan</h3>
      {planChange.error !== null && <p role="alert">{planChange.error}</p>}
      <label htmlFor="target-plan-version-id">Target plan version ID</label>
      <input
        id="target-plan-version-id"
        value={targetPlanVersionId}
        onChange={(event) => setTargetPlanVersionId(event.target.value)}
      />
      <button
        type="button"
        disabled={planChange.isSubmitting || targetPlanVersionId === ""}
        onClick={() => void planChange.preview(subscriptionId, targetPlanVersionId)}
      >
        Preview
      </button>
      {planChange.previewAmount !== null && (
        <>
          <p data-testid="plan-change-preview-amount">
            Pro-rata amount: {planChange.previewAmount}
          </p>
          <button
            type="button"
            disabled={planChange.isSubmitting}
            onClick={() => void planChange.commit(subscriptionId, targetPlanVersionId)}
          >
            Confirm plan change
          </button>
        </>
      )}
      {planChange.committedBillingRecordId !== null && (
        <p role="status" data-testid="plan-change-committed">
          Plan change committed — billing record {planChange.committedBillingRecordId}.
        </p>
      )}
    </div>
  );
}
