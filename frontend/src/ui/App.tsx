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
 *    (which itself grows a suspend/resume/port-out/plan-change panel once ACTIVE)
 *  - admin -> AdminPlanCatalogPage / AdminReportsDashboardPage, toggled by tab
 *  - csr -> CsrExceptionQueuePage (override + termination tools)
 *  - dealer -> no screen built yet (no story ever defined one — dealer-code
 *    validation happens server-side during activation only, per E2-S1's
 *    own "no dealer-facing UI" scope note)
 */

import { useState } from "react";

import { AdminPlanCatalogPage } from "./pages/AdminPlanCatalogPage";
import { AdminReportsDashboardPage } from "./pages/AdminReportsDashboardPage";
import { ActivationStatusPage } from "./pages/ActivationStatusPage";
import { CsrExceptionQueuePage } from "./pages/CsrExceptionQueuePage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { StaffRegisterPage } from "./pages/StaffRegisterPage";
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

type AdminTab = "catalog" | "reports";

function AdminFlow(): React.JSX.Element {
  const [tab, setTab] = useState<AdminTab>("catalog");

  return (
    <div>
      <nav className="admin-tabs">
        <button type="button" disabled={tab === "catalog"} onClick={() => setTab("catalog")}>
          Plan Catalog
        </button>
        <button type="button" disabled={tab === "reports"} onClick={() => setTab("reports")}>
          Reports
        </button>
      </nav>
      {tab === "catalog" ? (
        <AdminPlanCatalogPage planId="PLAN-5G" planName="Unlimited 5G Postpaid" planType="POSTPAID" />
      ) : (
        <AdminReportsDashboardPage />
      )}
    </div>
  );
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

type UnauthenticatedScreen = "login" | "staff-register";

export function App(): React.JSX.Element {
  const { isAuthenticated, role, subscriberId, login, logout } = useAuth();
  const [unauthenticatedScreen, setUnauthenticatedScreen] =
    useState<UnauthenticatedScreen>("login");

  const fallback =
    unauthenticatedScreen === "staff-register" ? (
      <StaffRegisterPage
        onRegistered={() => setUnauthenticatedScreen("login")}
        onBackToLogin={() => setUnauthenticatedScreen("login")}
      />
    ) : (
      <LoginPage onLogin={login} onGoToStaffRegister={() => setUnauthenticatedScreen("staff-register")} />
    );

  return (
    <RouteGuard isAuthenticated={isAuthenticated} role={role} fallback={fallback}>
      <div className="topbar">
        <span>role: {role}</span>
        <button type="button" onClick={logout}>
          Log out
        </button>
      </div>
      {role === "admin" && <AdminFlow />}
      {role === "subscriber" && <SubscriberFlow subscriberId={subscriberId} />}
      {role === "csr" && <CsrExceptionQueuePage />}
      {role === "dealer" && <NoScreenYet role={role} />}
    </RouteGuard>
  );
}
