/**
 * CSR override + termination tool (E6-S4). There is no "list pending
 * exceptions" backend endpoint — csr_override_repository only supports
 * querying overrides by subscription_id, not a cross-subscriber pending
 * queue — so this is a direct-entry tool (enter the subscriber_id/
 * subscription_id you're resolving) rather than a queue view. A future
 * story adding a real exception-listing endpoint would replace the
 * manual ID entry with a selectable list.
 *
 * Termination (E6-S6, CSR/admin) lives on this page too since both are
 * CSR back-office actions with no other screen to live on.
 *
 * UI layer.
 */

import { useState } from "react";

import { useCsrOverride } from "../../service/useCsrOverride";
import { useTerminate } from "../../service/useTerminate";

export function CsrExceptionQueuePage(): React.JSX.Element {
  return (
    <div className="app-shell">
      <h1>CSR Tools</h1>
      <OverrideActivationForm />
      <OverridePlanChangeForm />
      <TerminateForm />
    </div>
  );
}

function OverrideActivationForm(): React.JSX.Element {
  const { result, error, isSubmitting, overrideActivationAction } = useCsrOverride();
  const [subscriberId, setSubscriberId] = useState("");
  const [dealerCode, setDealerCode] = useState("");
  const [reasonCode, setReasonCode] = useState("");
  const [originalRejectionReason, setOriginalRejectionReason] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    await overrideActivationAction(subscriberId, dealerCode, reasonCode, originalRejectionReason);
  }

  return (
    <form className="panel" onSubmit={(event) => void handleSubmit(event)}>
      <h2>Override a rejected activation</h2>

      <label htmlFor="ovr-act-subscriber-id">Subscriber ID</label>
      <input
        id="ovr-act-subscriber-id"
        value={subscriberId}
        onChange={(event) => setSubscriberId(event.target.value)}
        required
      />

      <label htmlFor="ovr-act-dealer-code">Dealer code</label>
      <input
        id="ovr-act-dealer-code"
        value={dealerCode}
        onChange={(event) => setDealerCode(event.target.value)}
        required
      />

      <label htmlFor="ovr-act-original-reason">Original rejection reason</label>
      <input
        id="ovr-act-original-reason"
        value={originalRejectionReason}
        onChange={(event) => setOriginalRejectionReason(event.target.value)}
        required
      />

      <label htmlFor="ovr-act-reason-code">Override reason code</label>
      <input
        id="ovr-act-reason-code"
        value={reasonCode}
        onChange={(event) => setReasonCode(event.target.value)}
        required
      />

      {error !== null && <p role="alert">{error}</p>}
      {result !== null && <p role="status">{result}</p>}

      <button type="submit" disabled={isSubmitting}>
        Override activation
      </button>
    </form>
  );
}

function OverridePlanChangeForm(): React.JSX.Element {
  const { result, error, isSubmitting, overridePlanChangeAction } = useCsrOverride();
  const [subscriptionId, setSubscriptionId] = useState("");
  const [targetPlanVersionId, setTargetPlanVersionId] = useState("");
  const [reasonCode, setReasonCode] = useState("");
  const [originalRejectionReason, setOriginalRejectionReason] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    await overridePlanChangeAction(
      subscriptionId,
      targetPlanVersionId,
      reasonCode,
      originalRejectionReason,
    );
  }

  return (
    <form className="panel" onSubmit={(event) => void handleSubmit(event)}>
      <h2>Override a rejected plan change</h2>

      <label htmlFor="ovr-pc-subscription-id">Subscription ID</label>
      <input
        id="ovr-pc-subscription-id"
        value={subscriptionId}
        onChange={(event) => setSubscriptionId(event.target.value)}
        required
      />

      <label htmlFor="ovr-pc-target-plan">Target plan version ID</label>
      <input
        id="ovr-pc-target-plan"
        value={targetPlanVersionId}
        onChange={(event) => setTargetPlanVersionId(event.target.value)}
        required
      />

      <label htmlFor="ovr-pc-original-reason">Original rejection reason</label>
      <input
        id="ovr-pc-original-reason"
        value={originalRejectionReason}
        onChange={(event) => setOriginalRejectionReason(event.target.value)}
        required
      />

      <label htmlFor="ovr-pc-reason-code">Override reason code</label>
      <input
        id="ovr-pc-reason-code"
        value={reasonCode}
        onChange={(event) => setReasonCode(event.target.value)}
        required
      />

      {error !== null && <p role="alert">{error}</p>}
      {result !== null && <p role="status">{result}</p>}

      <button type="submit" disabled={isSubmitting}>
        Override plan change
      </button>
    </form>
  );
}

function TerminateForm(): React.JSX.Element {
  const { result, error, isSubmitting, terminate } = useTerminate();
  const [subscriptionId, setSubscriptionId] = useState("");
  const [reasonCode, setReasonCode] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    await terminate(subscriptionId, reasonCode);
  }

  return (
    <form className="panel" onSubmit={(event) => void handleSubmit(event)}>
      <h2>Terminate a subscription</h2>

      <label htmlFor="term-subscription-id">Subscription ID</label>
      <input
        id="term-subscription-id"
        value={subscriptionId}
        onChange={(event) => setSubscriptionId(event.target.value)}
        required
      />

      <label htmlFor="term-reason-code">Reason code</label>
      <input
        id="term-reason-code"
        value={reasonCode}
        onChange={(event) => setReasonCode(event.target.value)}
        required
      />

      {error !== null && <p role="alert">{error}</p>}
      {result !== null && <p role="status">{result}</p>}

      <button type="submit" disabled={isSubmitting}>
        Terminate
      </button>
    </form>
  );
}
