/**
 * Subscriber self-registration page (E2-S5 AC-1): submits mobile
 * number, identity-proof reference, and plan type to the registration
 * endpoint. On success, hands the resulting subscriber_id up via
 * onRegistered so the caller can move on to the activation step.
 *
 * UI layer.
 */

import { useState } from "react";

import { useRegistration } from "../../service/useRegistration";
import type { PlanType } from "../../types/domain";

export interface RegisterPageProps {
  onRegistered: (subscriberId: string) => void;
}

export function RegisterPage({ onRegistered }: RegisterPageProps): React.JSX.Element {
  const { error, isSubmitting, register } = useRegistration();
  const [mobileNumber, setMobileNumber] = useState("");
  const [identityProofRef, setIdentityProofRef] = useState("");
  const [planType, setPlanType] = useState<PlanType>("PREPAID");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const response = await register(mobileNumber, identityProofRef, planType);
    if (response !== null) {
      onRegistered(response.subscriber_id);
    }
  }

  return (
    <div className="auth-shell">
      <h1>Register</h1>

      <form onSubmit={(event) => void handleSubmit(event)}>
        <label htmlFor="mobile-number">Mobile number</label>
        <input
          id="mobile-number"
          value={mobileNumber}
          onChange={(event) => setMobileNumber(event.target.value)}
          required
        />

        <label htmlFor="identity-proof-ref">Identity proof reference</label>
        <input
          id="identity-proof-ref"
          value={identityProofRef}
          onChange={(event) => setIdentityProofRef(event.target.value)}
          required
        />

        <label htmlFor="plan-type">Plan type</label>
        <select
          id="plan-type"
          value={planType}
          onChange={(event) => setPlanType(event.target.value as PlanType)}
        >
          <option value="PREPAID">Prepaid</option>
          <option value="POSTPAID">Postpaid</option>
        </select>

        {error !== null && <p role="alert">{error}</p>}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Registering…" : "Register"}
        </button>
      </form>
    </div>
  );
}
