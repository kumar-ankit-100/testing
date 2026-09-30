/**
 * Root component (E3-S4 bootstrap). Renders the only page that exists so
 * far; a later UI story that adds routing between multiple pages extends
 * this file (analogous to how backend/src/app/api/main.py grows).
 */

import { AdminPlanCatalogPage } from "./pages/AdminPlanCatalogPage";

export function App(): React.JSX.Element {
  return <AdminPlanCatalogPage planId="PLAN-5G" planName="Unlimited 5G Postpaid" planType="POSTPAID" />;
}
