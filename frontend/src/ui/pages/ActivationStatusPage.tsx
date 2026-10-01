/**
 * Activation status page (E2-S5 AC-2/AC-3): submits a dealer code to
 * the activation endpoint and displays the outcome — a success badge
 * with state ACTIVE, or the specific rejection reason code/message.
 *
 * UI layer.
 */

import { useState } from "react";

import { useActivationStatus } from "../../service/useActivationStatus";

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
        <p data-testid="activation-success" role="status">
          Your subscription is now <strong>ACTIVE</strong>.
        </p>
      ) : (
        <form onSubmit={(event) => void handleSubmit(event)}>
          <label htmlFor="dealer-code">Dealer code</label>
          <input
            id="dealer-code"
            value={dealerCode}
            onChange={(event) => setDealerCode(event.target.value)}
            required
          />

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
