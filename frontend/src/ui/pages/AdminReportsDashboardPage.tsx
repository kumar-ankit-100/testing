/**
 * Admin reporting dashboard page (E7-S4): displays the activation
 * funnel, plan mix, churn, and stubbed ARPU trend from the admin
 * dashboard endpoint.
 *
 * UI layer.
 */

import { useReports } from "../../service/useReports";

export function AdminReportsDashboardPage(): React.JSX.Element {
  const { dashboard, loading, error } = useReports();

  if (loading) {
    return <p>Loading…</p>;
  }
  if (error !== null) {
    return <p role="alert">{error}</p>;
  }
  if (dashboard === null) {
    return <></>;
  }

  return (
    <div className="app-shell" data-testid="admin-reports-dashboard">
      <h1>Reporting Dashboard</h1>

      <div className="panel">
        <h2>Activation funnel</h2>
        <table>
          <tbody>
            {Object.entries(dashboard.activation_funnel).map(([stage, count]) => (
              <tr key={stage}>
                <td>{stage}</td>
                <td>{count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h2>Plan mix</h2>
        <table>
          <tbody>
            {Object.entries(dashboard.plan_mix_percentages).map(([planType, percentage]) => (
              <tr key={planType}>
                <td>{planType}</td>
                <td>{percentage}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h2>Monthly churn</h2>
        {Object.keys(dashboard.churn).length === 0 ? (
          <p>No churn events recorded yet.</p>
        ) : (
          <table>
            <tbody>
              {Object.entries(dashboard.churn).map(([month, rate]) => (
                <tr key={month}>
                  <td>{month}</td>
                  <td>{rate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <h2>ARPU trend (stubbed)</h2>
        <p style={{ fontSize: "12px", color: "var(--muted)" }}>
          {dashboard.metadata.arpu_trend_note}
        </p>
        {Object.keys(dashboard.arpu_trend).length === 0 ? (
          <p>No billing data recorded yet.</p>
        ) : (
          <table>
            <tbody>
              {Object.entries(dashboard.arpu_trend).map(([month, arpu]) => (
                <tr key={month}>
                  <td>{month}</td>
                  <td>{arpu}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
