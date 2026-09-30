/**
 * Admin plan catalog management page (E3-S4).
 *
 * UI layer — lists a plan's version history, blocks editing published
 * versions with an inline message, and lets an admin create + publish a
 * new draft.
 */

import { useState } from "react";

import { usePlanCatalog } from "../../service/usePlanCatalog";
import type { PlanType } from "../../types/domain";
import type { PlanVersionDto } from "../../types/api";
import { StateBadge } from "../components/StateBadge";

export interface AdminPlanCatalogPageProps {
  planId: string;
  planName: string;
  planType: PlanType;
}

interface DraftForm {
  price: string;
  validityDays: string;
  dataGb: string;
  smsPerDay: string;
}

const EMPTY_FORM: DraftForm = { price: "", validityDays: "", dataGb: "", smsPerDay: "" };

export function AdminPlanCatalogPage({
  planId,
  planName,
  planType,
}: AdminPlanCatalogPageProps): React.JSX.Element {
  const { versions, loading, error, createDraft, publishDraft } = usePlanCatalog(planId);
  const [editLockedVersion, setEditLockedVersion] = useState<PlanVersionDto | null>(null);
  const [form, setForm] = useState<DraftForm>(EMPTY_FORM);

  const publishedVersion = versions.find((version) => version.published) ?? null;

  function prefillFromPublished(): void {
    if (publishedVersion === null) {
      return;
    }
    setForm({
      price: publishedVersion.price,
      validityDays: String(publishedVersion.terms.validity_days),
      dataGb: String(publishedVersion.terms.data_gb),
      smsPerDay: String(publishedVersion.terms.sms_per_day),
    });
    setEditLockedVersion(null);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const created = await createDraft({
      plan_id: planId,
      plan_name: planName,
      plan_type: planType,
      price: form.price,
      terms: {
        validity_days: Number(form.validityDays),
        data_gb: Number(form.dataGb),
        sms_per_day: Number(form.smsPerDay),
      },
    });
    if (created) {
      setForm(EMPTY_FORM);
    }
  }

  return (
    <div>
      <h1>Plan Catalog</h1>
      {loading && <p>Loading…</p>}
      {error !== null && <p role="alert">{error}</p>}

      <table>
        <thead>
          <tr>
            <th>Version</th>
            <th>Price</th>
            <th>Status</th>
            <th aria-label="actions" />
          </tr>
        </thead>
        <tbody>
          {versions.map((version) => (
            <tr key={version.plan_version_id}>
              <td>v{version.version_number}</td>
              <td>{version.price}</td>
              <td>
                <StateBadge published={version.published} />
              </td>
              <td>
                {version.published ? (
                  <button type="button" onClick={() => setEditLockedVersion(version)}>
                    Edit
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => void publishDraft(version.plan_version_id)}
                  >
                    Publish
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {editLockedVersion !== null && (
        <div role="alert" data-testid="edit-locked-message">
          <p>
            Version v{editLockedVersion.version_number} is published and immutable. Create a new
            draft version instead.
          </p>
          <label htmlFor="locked-price">Price</label>
          <input id="locked-price" value={editLockedVersion.price} disabled />
          <button type="button" onClick={prefillFromPublished}>
            Create draft from v{editLockedVersion.version_number}
          </button>
          <button type="button" onClick={() => setEditLockedVersion(null)}>
            Cancel
          </button>
        </div>
      )}

      <form onSubmit={(event) => void handleSubmit(event)}>
        <label htmlFor="draft-price">Monthly price</label>
        <input
          id="draft-price"
          value={form.price}
          onChange={(event) => setForm({ ...form, price: event.target.value })}
          required
        />

        <label htmlFor="draft-validity">Validity (days)</label>
        <input
          id="draft-validity"
          type="number"
          value={form.validityDays}
          onChange={(event) => setForm({ ...form, validityDays: event.target.value })}
          required
        />

        <label htmlFor="draft-data">Data quota / day (GB)</label>
        <input
          id="draft-data"
          type="number"
          value={form.dataGb}
          onChange={(event) => setForm({ ...form, dataGb: event.target.value })}
          required
        />

        <label htmlFor="draft-sms">SMS / day</label>
        <input
          id="draft-sms"
          type="number"
          value={form.smsPerDay}
          onChange={(event) => setForm({ ...form, smsPerDay: event.target.value })}
          required
        />

        <button type="submit">Create draft</button>
      </form>
    </div>
  );
}
