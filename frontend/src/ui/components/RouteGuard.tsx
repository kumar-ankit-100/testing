/**
 * Role-based route guard (E1-S6/E2-S5 AC-6): renders its children only
 * when authenticated and (if allowedRoles is given) the current role is
 * in that set; otherwise renders the supplied fallback (typically the
 * login page) instead of the protected content.
 *
 * Pure/presentational — auth state is lifted to the caller (App.tsx,
 * via a single shared useAuth() call) rather than read here directly,
 * so a successful login on a sibling LoginPage reliably re-renders this
 * guard with fresh props instead of each component holding its own,
 * independently-stale copy of the auth state.
 *
 * UI layer.
 */

import type { Role } from "../../types/domain";

export interface RouteGuardProps {
  isAuthenticated: boolean;
  role: Role | null;
  allowedRoles?: Role[];
  fallback: React.ReactNode;
  children: React.ReactNode;
}

export function RouteGuard({
  isAuthenticated,
  role,
  allowedRoles,
  fallback,
  children,
}: RouteGuardProps): React.JSX.Element {
  if (!isAuthenticated) {
    return <>{fallback}</>;
  }

  if (allowedRoles !== undefined && (role === null || !allowedRoles.includes(role))) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
