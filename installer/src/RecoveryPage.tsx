import type { Mode } from "./model";
import type { AcknowledgmentResult, RecoveryState } from "./recovery";

function when(seconds: number) {
  return new Date(seconds * 1000).toLocaleString();
}
export function RecoveryPage({
  state,
  loading,
  error,
  pending,
  outcomes,
  onCheck,
  onAcknowledge,
  onContinue,
  onCancel,
  onValidate,
  onLogs,
  onSupport,
}: {
  state: RecoveryState | null;
  loading: boolean;
  error: string;
  pending: Mode | null;
  outcomes: AcknowledgmentResult[];
  onCheck: () => void;
  onAcknowledge: () => void;
  onContinue: () => void;
  onCancel: () => void;
  onValidate: () => void;
  onLogs: () => void;
  onSupport: () => void;
}) {
  const canAcknowledge =
    !!state && (state.canAcknowledgeMachine || state.canAcknowledgeUser);
  const accountUnavailable =
    !!state &&
    state.machine.available &&
    !state.user.available &&
    state.nativeSafety.trust === "trusted";
  return (
    <section
      className="recovery-page"
      aria-labelledby="recovery-heading"
      aria-busy={loading}
    >
      <div>
        <p className="eyebrow">SAFE RECOVERY</p>
        <h2 id="recovery-heading">
          {state?.effectiveActivity === "active"
            ? "An operation is still active"
            : "Recovery findings"}
        </h2>
        <p>
          Review what SDE detected. Acknowledgment preserves the evidence and
          automatically attempts to save a local summary—no separate report
          step. It does not certify completion, repair packages or bypass safety
          checks.
        </p>
        {state?.readiness === "blocked" && (
          <p>
            Acknowledgment may be recorded now when offered below, but changes
            remain blocked until current safety findings permit a fresh native
            recheck.
          </p>
        )}
        {error && <p role="alert">{error}</p>}
        {!state && (
          <p>
            Recovery findings are unavailable. Check Again; do not delete
            journals, remove locks or end installer processes.
          </p>
        )}
        {state && (
          <>
            <h3>
              {accountUnavailable
                ? "Account recovery evidence unavailable"
                : state.guidance.title}
            </h3>
            <ul>
              {(accountUnavailable
                ? [
                    "Check Again. Keep the account journal and retained decisions unchanged; do not delete or rewrite them to enable changes.",
                    "Create support report includes structured source-availability and machine-safety findings even when the account journal cannot be parsed. Review and share it only if you choose; malformed journal bytes are not copied.",
                    "A normal Restart can end an earlier process lifetime but cannot repair malformed evidence or acknowledge an incident. Reinstalling SDE repairs application files, not an unreadable account journal.",
                  ]
                : state.guidance.steps
              ).map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ul>
            <dl className="recovery-findings">
              <dt>Observed</dt>
              <dd>{when(state.nativeSafety.observedAt)}</dd>
              <dt>Current activity</dt>
              <dd>{state.effectiveActivity}</dd>
              <dt>Package health</dt>
              <dd>{state.nativeSafety.packageHealth}</dd>
              <dt>Protected coordination</dt>
              <dd>{state.nativeSafety.trust}</dd>
            </dl>
            <h3>Machine incident</h3>
            <p>
              {!state.machine.available
                ? "Machine evidence unavailable—not a cleared incident."
                : state.machine.incidentId
                  ? `Incident ${state.machine.incidentId}`
                  : "No current machine incident recorded."}
            </p>
            {state.machine.incidentId && (
              <p>
                {state.machine.acknowledgedAt
                  ? `Protected acknowledgment recorded ${when(state.machine.acknowledgedAt)}.`
                  : state.machine.intentSubmitted
                    ? "Acknowledgment submitted. Protected commitment is still pending the normal privileged recheck; no execution permission has been granted."
                    : "Not acknowledged."}
              </p>
            )}
            <h3>This account’s incident</h3>
            <p>
              {!state.user.available
                ? "Account evidence unavailable—not a cleared incident."
                : state.user.incident
                  ? `${state.user.incident.operation} stopped during ${state.user.incident.stage}. Incident ${state.user.incident.id}. Started ${when(state.user.incident.startedAt)}; last recorded ${when(state.user.incident.observedAt)}.`
                  : "No current account incident recorded."}
            </p>
            {state.user.incident && (
              <>
                <p>
                  {state.user.acknowledgment
                    ? `Account acknowledgment recorded ${when(state.user.acknowledgment.acknowledgedAt)}.`
                    : "Not acknowledged."}
                </p>
                <p>
                  Restart evidence: {state.user.restart}. A free account gate
                  does not prove an earlier child ended. A legacy incident may
                  need a normal Restart after acknowledgment captures its first
                  provenance.
                </p>
              </>
            )}
          </>
        )}
        {outcomes.map((outcome, index) => (
          <div key={`${outcome.incidentId}-${index}`} role="status">
            <p>
              {outcome.reportId
                ? `Local summary saved: ${outcome.reportId}.`
                : "Local summary was not saved."}
            </p>
            {outcome.reportWarning && <p>{outcome.reportWarning}</p>}
            {outcome.intentWarning && <p>{outcome.intentWarning}</p>}
            {outcome.acknowledgmentWarning && (
              <p>{outcome.acknowledgmentWarning}</p>
            )}
          </div>
        ))}
        {pending && (
          <p>
            Requested action: {pending}. Continuation keeps the normal review
            and operating-system approval steps. Cancel forgets this request;
            SDE will not replay it after restart.
          </p>
        )}
        <div className="result-actions">
          {canAcknowledge && (
            <button
              className="primary"
              disabled={loading}
              onClick={onAcknowledge}
            >
              {pending
                ? "Acknowledge and continue"
                : "Acknowledge interruption"}
            </button>
          )}
          {!canAcknowledge &&
            pending &&
            state?.readiness === "ready_for_native_recheck" && (
              <button
                className="primary"
                disabled={loading}
                onClick={onContinue}
              >
                Continue with {pending}
              </button>
            )}
          <button className="secondary" disabled={loading} onClick={onCheck}>
            Check Again
          </button>
          <button
            className="secondary"
            disabled={loading || state?.effectiveActivity === "active"}
            onClick={onValidate}
          >
            Run validation
          </button>
          <button className="secondary" disabled={loading} onClick={onLogs}>
            Open logs
          </button>
          <button className="secondary" disabled={loading} onClick={onSupport}>
            Create support report
          </button>
          <button className="secondary" disabled={loading} onClick={onCancel}>
            Cancel
          </button>
        </div>
      </div>
    </section>
  );
}
