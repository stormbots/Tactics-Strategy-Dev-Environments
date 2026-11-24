import type { RecoveryState } from "./recovery";

function time(seconds: number | undefined) {
  const date = new Date((seconds ?? NaN) * 1000);
  return seconds && seconds > 0 && Number.isFinite(date.getTime())
    ? date.toLocaleString()
    : "Time unavailable";
}
const operations: Record<string, string> = {
  install: "Install",
  repair: "Repair",
  update: "Development-tool Update",
};
function explanation(state: RecoveryState | null, error: string) {
  if (
    error ||
    !state ||
    !state.machine.available ||
    !state.user.available ||
    state.nativeSafety.trust !== "trusted"
  )
    return "SDE could not read or verify all of its safety information. Open Recovery to review the access or inspection problem. This does not prove that an earlier operation failed.";
  if (state.effectiveActivity === "active")
    return "SDE detected setup or update work still running. Let it finish before starting another change. Do not force it to close or restart during installation.";
  if (state.effectiveActivity === "unknown") {
    if (state.nativeSafety.interrupted || state.machine.incidentId) {
      if (
        state.nativeSafety.activityReason === "earlier_process_lifetime_unknown"
      )
        return "SDE cannot yet confirm that the earlier system operation ended during this computer session.";
      if (state.nativeSafety.activityReason === "restart_evidence_unavailable")
        return "SDE could not read enough restart information to confirm that the earlier system operation ended.";
      if (state.nativeSafety.activityReason === "native_inspection_unavailable")
        return "SDE could not finish checking whether setup or update work is still running.";
    }
    return "SDE cannot yet confirm whether setup or update work has stopped. The current evidence does not establish the cause.";
  }
  if (state.nativeSafety.packageHealth === "incomplete")
    return "An installation needs attention before SDE can start another change. Review the operating system’s findings in Recovery.";
  if (
    state.readiness === "needs_acknowledgment" ||
    state.canAcknowledgeMachine ||
    state.canAcknowledgeUser
  )
    return "The operation is no longer running. Its retained interruption still needs your review. This does not mean the earlier operation completed successfully.";
  return "A safety check still needs review before SDE can start another change. Open Recovery for the current findings and supported next action.";
}

/** Shows existing observations only. Review cannot acknowledge, retire or permit work. */
export function ChangeSafetyOverviewCard({
  state,
  pending,
  error,
  busy,
  onReview,
  onSupport,
}: {
  state: RecoveryState | null;
  pending: boolean;
  error: string;
  busy: boolean;
  onReview: () => void;
  onSupport: () => void;
}) {
  if (!changeSafetyNeedsReview(state, pending, error)) return null;
  const account = state?.user.available ? state.user.incident : null;
  const system =
    state?.machine.available &&
    (state.machine.incidentId || state.nativeSafety.interrupted);
  return (
    <section
      className="information-card"
      aria-labelledby="change-safety-overview-heading"
      aria-busy={pending}
    >
      <p className="eyebrow">Change safety</p>
      <h2 id="change-safety-overview-heading" tabIndex={-1}>
        {pending ? "Checking change safety…" : "Change safety needs review"}
      </h2>
      {pending ? (
        <p>
          SDE is reading its safety information. This check does not start or
          acknowledge an operation.
        </p>
      ) : (
        <>
          <p>{explanation(state, error)}</p>
          {account && (
            <dl className="information-grid">
              <div>
                <dt>Account operation</dt>
                <dd>
                  {Object.hasOwn(operations, account.operation)
                    ? operations[account.operation]
                    : "Operation name unavailable"}
                </dd>
              </div>
              <div>
                <dt>Started</dt>
                <dd>{time(account.startedAt)}</dd>
              </div>
              <div>
                <dt>Last recorded</dt>
                <dd>{time(account.observedAt)}</dd>
              </div>
            </dl>
          )}
          {system && (
            <dl className="information-grid">
              <div>
                <dt>System operation</dt>
                <dd>Operation name unavailable</dd>
              </div>
              <div>
                <dt>System operation started</dt>
                <dd>Time unavailable</dd>
              </div>
              <div>
                <dt>System safety last checked</dt>
                <dd>{time(state?.nativeSafety.observedAt)}</dd>
              </div>
            </dl>
          )}
          {!account && !system && (
            <p>
              Operation name unavailable. SDE has not confirmed a readable
              earlier-operation record.
            </p>
          )}
          <p>
            Open Recovery to check the operation status and review what can
            happen next. Opening review does not acknowledge or clear the
            record, stop work, or allow a new change.
          </p>
        </>
      )}
      <div className="result-actions">
        <button
          className="secondary"
          disabled={busy || pending}
          onClick={onReview}
        >
          Address safety finding
        </button>
        <button
          className="secondary"
          disabled={busy || pending}
          onClick={onSupport}
        >
          Create safety support report
        </button>
      </div>
    </section>
  );
}

export function changeSafetyNeedsReview(
  state: RecoveryState | null,
  pending: boolean,
  error: string,
): boolean {
  return !(
    !pending &&
    !error &&
    state?.readiness === "ready_for_native_recheck" &&
    state.effectiveActivity === "inactive" &&
    state.nativeSafety.trust === "trusted" &&
    state.nativeSafety.packageHealth !== "incomplete" &&
    state.machine.available &&
    state.user.available &&
    !state.canAcknowledgeMachine &&
    !state.canAcknowledgeUser
  );
}
