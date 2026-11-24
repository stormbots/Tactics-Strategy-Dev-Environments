import { useEffect, useState } from "react";
import type { Schedule } from "./model";
import { readDisabledChoice } from "./maintenanceDisabledChoice";
import { maintenanceFinding } from "./MaintenanceInspectionReview";

/** Display only: neither the preference nor this card participates in admission. */
export function MaintenanceOverviewCard({
  data,
  pending,
  busy,
  onReview,
  onSupport,
}: {
  data: Schedule | null;
  pending: boolean;
  busy: boolean;
  onReview: () => void;
  onSupport: () => void;
}) {
  const [choice, setChoice] = useState<{
    observation: Schedule;
    saved: boolean;
  } | null>(null);
  useEffect(() => {
    let current = true;
    if (!pending && data?.choiceContext) {
      void readDisabledChoice(data.choiceContext, data, {
        getItem: (key) => window.localStorage.getItem(key),
        setItem: (key, value) => window.localStorage.setItem(key, value),
      }).then((saved) => {
        if (current) setChoice({ observation: data, saved });
      });
    }
    return () => {
      current = false;
    };
  }, [data, pending]);
  const saved = !pending && choice?.observation === data && choice.saved;
  const finding = maintenanceFinding(
    data,
    !data && !pending ? "unavailable" : "",
  );
  if (!maintenanceOverviewVisible(data, pending)) return null;
  const title = pending
    ? "Checking weekly maintenance…"
    : saved
      ? "You chose to leave weekly maintenance disabled"
      : (finding?.title ??
        (data?.lastResult === "running"
          ? "Weekly maintenance is running"
          : data?.lastResult === "failure"
            ? "An earlier maintenance attempt failed"
            : "Maintenance history needs review"));
  return (
    <section
      className="information-card"
      aria-labelledby="maintenance-overview-heading"
      aria-busy={pending}
    >
      <p className="eyebrow">Weekly maintenance</p>
      <h2 id="maintenance-overview-heading" tabIndex={-1}>
        {title}
      </h2>
      {pending ? (
        <p>
          SDE is reading the schedule. This check does not start maintenance.
        </p>
      ) : (
        <>
          {finding && <p>{finding.detail}</p>}
          {saved && (
            <p>
              Your choice is saved for your account on this computer. The
              schedule is still disabled. Earlier results have not changed.
            </p>
          )}
          {data?.lastResult === "running" && (
            <p>Maintenance is running. Saving a choice does not stop it.</p>
          )}
          {data?.lastResult === "failure" && (
            <p>
              An earlier maintenance attempt failed. Review its results even if
              you chose to leave future maintenance disabled.
            </p>
          )}
          {data?.lastResult === "unavailable" && (
            <p>
              SDE could not confirm the result of earlier maintenance. A saved
              choice does not complete that check.
            </p>
          )}
          {data && (
            <details>
              <summary>Maintenance observation details</summary>
              <p>
                Schedule: {data.status}. Earlier result: {data.lastResult}.
              </p>
              <p>{data.resultDetail}</p>
              <p>Observed: {data.observedAt}</p>
            </details>
          )}
        </>
      )}
      <div className="result-actions">
        <button
          className="secondary"
          disabled={busy || pending}
          onClick={onReview}
        >
          {saved ? "View maintenance details" : "Review weekly maintenance"}
        </button>
        <button
          className="secondary"
          disabled={busy || pending}
          onClick={onSupport}
        >
          Create maintenance report
        </button>
      </div>
    </section>
  );
}

export function maintenanceOverviewVisible(
  data: Schedule | null,
  pending: boolean,
): boolean {
  return (
    pending ||
    !!maintenanceFinding(data, !data ? "unavailable" : "") ||
    data?.lastResult !== "success"
  );
}
