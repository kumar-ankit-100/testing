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
import { usePublishedPlans } from "../../service/usePublishedPlans";
import { useSubscriptionDetail } from "../../service/useSubscriptionDetail";
import type { SubscriptionDetailResponse } from "../../types/api";

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
          <SubscriptionManagementPanel subscriberId={subscriberId} />
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

function SubscriptionManagementPanel({
  subscriberId,
}: {
  subscriberId: string;
}): React.JSX.Element {
  const subscriptionId = getStoredSubscriptionId();
  const lifecycle = useLifecycle("ACTIVE");
  const planChange = usePlanChange();
  const publishedPlans = usePublishedPlans();
  const subscriptionDetail = useSubscriptionDetail(subscriberId);
  const [targetPlanVersionId, setTargetPlanVersionId] = useState("");

  if (subscriptionId === null) {
    return <></>;
  }

  return (
    <div className="panel" data-testid="subscription-management-panel">
      <h2>Manage your subscription</h2>

      <SubscriptionDetailPanel
        detail={subscriptionDetail.detail}
        loading={subscriptionDetail.loading}
        error={subscriptionDetail.error}
        lastUpdatedAt={subscriptionDetail.lastUpdatedAt}
        onRefresh={subscriptionDetail.refresh}
      />

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
      {publishedPlans.error !== null && <p role="alert">{publishedPlans.error}</p>}
      <label htmlFor="target-plan-version-id">Target plan</label>
      <select
        id="target-plan-version-id"
        value={targetPlanVersionId}
        onChange={(event) => setTargetPlanVersionId(event.target.value)}
        disabled={publishedPlans.loading}
      >
        <option value="">
          {publishedPlans.loading ? "Loading plans…" : "Select a plan"}
        </option>
        {publishedPlans.plans.map((plan) => (
          <option key={plan.plan_version_id} value={plan.plan_version_id}>
            {plan.plan_name} ({plan.plan_type}) — ₹{plan.price}
          </option>
        ))}
      </select>
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

function SubscriptionDetailPanel({
  detail,
  loading,
  error,
  lastUpdatedAt,
  onRefresh,
}: {
  detail: SubscriptionDetailResponse | null;
  loading: boolean;
  error: string | null;
  lastUpdatedAt: Date | null;
  onRefresh: () => void;
}): React.JSX.Element {
  return (
    <div className="panel" data-testid="subscription-detail-panel">
      <div className="dashboard-refresh-bar">
        {error !== null && <p role="alert">{error}</p>}
        <p data-testid="subscription-detail-last-updated">
          {lastUpdatedAt !== null ? `Last updated: ${lastUpdatedAt.toLocaleTimeString()}` : ""}
        </p>
        <button type="button" onClick={onRefresh} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh now"}
        </button>
      </div>

      {detail === null ? (
        <p>Loading your subscription details…</p>
      ) : (
        <dl className="detail-grid">
          <dt>Subscription ID</dt>
          <dd>{detail.subscription_id}</dd>

          <dt>Mobile number</dt>
          <dd>{detail.mobile_number}</dd>

          <dt>Plan type</dt>
          <dd>{detail.plan_type}</dd>

          <dt>Dealer code</dt>
          <dd>{detail.dealer_code ?? "—"}</dd>

          <dt>Activated at</dt>
          <dd>{detail.activated_at ?? "—"}</dd>

          <dt>Current plan</dt>
          <dd>
            {detail.current_plan !== null
              ? `${detail.current_plan.plan_name} — ₹${detail.current_plan.price}`
              : "No plan set yet"}
          </dd>
        </dl>
      )}
    </div>
  );
}
