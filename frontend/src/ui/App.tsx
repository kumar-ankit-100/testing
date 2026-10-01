/**
 * Root component (E3-S4 bootstrap; extended E1-S6/E2-S5 for login +
 * the role-based route guard). Calls useAuth() exactly once here and
 * passes its state/actions down as props — see RouteGuard.tsx's
 * docstring for why each component must not call useAuth() itself.
 * Renders the login page until an admin token is present, then the
 * admin plan catalog page — the only two pages that exist so far. A
 * later UI story that adds real routing between multiple pages extends
 * this file further (analogous to how backend/src/app/api/main.py
 * grows).
 */

import { AdminPlanCatalogPage } from "./pages/AdminPlanCatalogPage";
import { LoginPage } from "./pages/LoginPage";
import { RouteGuard } from "./components/RouteGuard";
import { useAuth } from "../service/useAuth";

export function App(): React.JSX.Element {
  const { isAuthenticated, role, login } = useAuth();

  return (
    <RouteGuard
      isAuthenticated={isAuthenticated}
      role={role}
      allowedRoles={["admin"]}
      fallback={<LoginPage onLogin={login} />}
    >
      <AdminPlanCatalogPage
        planId="PLAN-5G"
        planName="Unlimited 5G Postpaid"
        planType="POSTPAID"
      />
    </RouteGuard>
  );
}
