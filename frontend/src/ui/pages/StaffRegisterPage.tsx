/**
 * Staff self-registration page: creates a dynamic CSR or admin account
 * via POST /api/auth/register-staff. On success, hands control back to
 * the login screen (register then login are two distinct steps) rather
 * than auto-logging-in.
 *
 * Dealer is deliberately not offered here: per specs/design/
 * system-design.md and specs/stories/E2-S1.md, the dealer role has no
 * dealer-facing UI anywhere in this app — it exists only as an
 * authorization-test identity and as the seeded DealerMaster reference
 * table consulted server-side during activation. A dealer account
 * created here would have nowhere to log in to.
 *
 * UI layer.
 */

import { useState } from "react";

import { useStaffRegistration } from "../../service/useStaffRegistration";

export interface StaffRegisterPageProps {
  onRegistered: () => void;
  onBackToLogin: () => void;
}

type StaffRole = "csr" | "admin";

export function StaffRegisterPage({
  onRegistered,
  onBackToLogin,
}: StaffRegisterPageProps): React.JSX.Element {
  const { error, isSubmitting, register } = useStaffRegistration();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<StaffRole>("csr");
  const [succeeded, setSucceeded] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const response = await register({ username, password, role });
    if (response !== null) {
      setSucceeded(true);
      onRegistered();
    }
  }

  if (succeeded) {
    return (
      <div className="auth-shell">
        <h1>Account created</h1>
        <p>Your staff account was created. You can now log in.</p>
        <button type="button" onClick={onBackToLogin}>
          Go to login
        </button>
      </div>
    );
  }

  return (
    <div className="auth-shell">
      <h1>Register (staff)</h1>

      <form onSubmit={(event) => void handleSubmit(event)}>
        <label htmlFor="staff-register-username">Username</label>
        <input
          id="staff-register-username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          required
        />

        <label htmlFor="staff-register-password">Password</label>
        <input
          id="staff-register-password"
          type="password"
          minLength={8}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        <label htmlFor="staff-register-role">Role</label>
        <select
          id="staff-register-role"
          value={role}
          onChange={(event) => setRole(event.target.value as StaffRole)}
        >
          <option value="csr">CSR</option>
          <option value="admin">Admin</option>
        </select>

        {error !== null && <p role="alert">{error}</p>}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Registering…" : "Register"}
        </button>
      </form>

      <button type="button" onClick={onBackToLogin}>
        Back to login
      </button>
    </div>
  );
}
