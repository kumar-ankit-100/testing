/**
 * Published/draft badge for a plan version (E3-S4 AC-1).
 *
 * UI layer.
 */

export interface StateBadgeProps {
  published: boolean;
}

export function StateBadge({ published }: StateBadgeProps): React.JSX.Element {
  return (
    <span
      data-testid="state-badge"
      data-state={published ? "published" : "draft"}
      className={published ? "badge badge-published" : "badge badge-draft"}
    >
      {published ? "PUBLISHED" : "DRAFT"}
    </span>
  );
}
