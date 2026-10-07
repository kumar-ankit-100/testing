/**
 * Root component (E3-S4 bootstrap; extended E1-S6/E2-S5 for login, the
 * role-based route guard, and per-role landing screens).
 *
 * Calls useAuth() exactly once here and passes its state/actions down as
 * props — see RouteGuard.tsx's docstring for why each component must not
 * call useAuth() itself.
 *
 * Routing by role:
 *  - unauthenticated -> LoginPage
 *  - subscriber, no subscriber_id yet -> RegisterPage -> (on success) ActivationStatusPage
 *  - subscriber, already registered -> ActivationStatusPage directly
 *  - admin -> AdminPlanCatalogPage
 *  - csr / dealer -> no screen built yet (later UI stories: E6-S4 CSR queue).
 *    Shown as an explicit "not built yet" message rather than silently
 *    bouncing back to the login screen with no feedback, which is the
 *    exact confusing behavior this replaces.
 */

import { useState } from "react";

import { AdminPlanCatalogPage } from "./pages/AdminPlanCatalogPage";
import { ActivationStatusPage } from "./pages/ActivationStatusPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { RouteGuard } from "./components/RouteGuard";
import { useAuth } from "../service/useAuth";

function SubscriberFlow({
  subscriberId: initialSubscriberId,
}: {
  subscriberId: string | null;
}): React.JSX.Element {
  const [subscriberId, setSubscriberId] = useState<string | null>(initialSubscriberId);

  if (subscriberId === null) {
    return <RegisterPage onRegistered={setSubscriberId} />;
  }
  return <ActivationStatusPage subscriberId={subscriberId} />;
}

function NoScreenYet({ role }: { role: string }): React.JSX.Element {
  return (
    <div className="auth-shell">
      <h1>Logged in as {role}</h1>
      <p>
        No {role} screen has been built yet — this role authenticates correctly, but there is no
        UI for it in this build.
      </p>
    </div>
  );
}

export function App(): React.JSX.Element {
  const { isAuthenticated, role, subscriberId, login, logout } = useAuth();

  return (
    <RouteGuard isAuthenticated={isAuthenticated} role={role} fallback={<LoginPage onLogin={login} />}>
      <div className="topbar">
        <span>role: {role}</span>
        <button type="button" onClick={logout}>
          Log out
        </button>
      </div>
      {role === "admin" && (
        <AdminPlanCatalogPage planId="PLAN-5G" planName="Unlimited 5G Postpaid" planType="POSTPAID" />
      )}
      {role === "subscriber" && <SubscriberFlow subscriberId={subscriberId} />}
      {(role === "csr" || role === "dealer") && <NoScreenYet role={role} />}
    </RouteGuard>
  );
}
