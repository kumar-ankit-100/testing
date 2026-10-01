/**
 * Login page (E1-S6/E2-S5 AC-5): submits to POST /api/auth/login via the
 * onLogin callback (the caller's useAuth().login, so the resulting
 * session state lives in one place — see RouteGuard.tsx's docstring for
 * why this is props-driven rather than calling useAuth() itself).
 *
 * Supports both login shapes: staff (username+password) and subscriber
 * self-service (mobile_number only), toggled by the radio group below.
 *
 * UI layer.
 */

import { useState } from "react";

import type { LoginRequest } from "../../types/api";

export interface LoginPageProps {
  onLogin: (request: LoginRequest) => Promise<boolean>;
}

type LoginMode = "staff" | "subscriber";

export function LoginPage({ onLogin }: LoginPageProps): React.JSX.Element {
  const [mode, setMode] = useState<LoginMode>("staff");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mobileNumber, setMobileNumber] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);

    const succeeded =
      mode === "staff"
        ? await onLogin({ username, password })
        : await onLogin({ mobile_number: mobileNumber });

    if (!succeeded) {
      setError("Invalid credentials");
    }
  }

  return (
    <div>
      <h1>Log in</h1>

      <div role="radiogroup" aria-label="Login as">
        <label>
          <input
            type="radio"
            name="mode"
            value="staff"
            checked={mode === "staff"}
            onChange={() => setMode("staff")}
          />
          Staff
        </label>
        <label>
          <input
            type="radio"
            name="mode"
            value="subscriber"
            checked={mode === "subscriber"}
            onChange={() => setMode("subscriber")}
          />
          Subscriber
        </label>
      </div>

      <form onSubmit={(event) => void handleSubmit(event)}>
        {mode === "staff" ? (
          <>
            <label htmlFor="username">Username</label>
            <input
              id="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />

            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </>
        ) : (
          <>
            <label htmlFor="mobile-number">Mobile number</label>
            <input
              id="mobile-number"
              value={mobileNumber}
              onChange={(event) => setMobileNumber(event.target.value)}
              required
            />
          </>
        )}

        {error !== null && <p role="alert">{error}</p>}

        <button type="submit">Log in</button>
      </form>
    </div>
  );
}
