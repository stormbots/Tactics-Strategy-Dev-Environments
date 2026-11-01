import type { Mode } from "./model";
import type { AcknowledgmentResult, RecoveryState } from "./recovery";

function when(seconds: number) {
  return new Date(seconds * 1000).toLocaleString();
}

// Presentation only: native snapshots and execution checks remain authoritative.
function nextStep(state: RecoveryState | null, platformLabel: string) {
  if (state?.effectiveActivity === "active")
    return {
      explanation:
        "A setup or update is still running. Install, Repair and Update are paused so two changes do not run at once.",
      steps: [
        "Let the current setup or update finish.",
        "Then select Check again.",
      ],
      note: "Do not force installer processes to close or restart during an installation.",
    };
  if (
    !state ||
    !state.machine.available ||
    !state.user.available ||
    state.nativeSafety.trust !== "trusted"
  )
    return {
      explanation:
        "SDE couldn’t read or verify its safety records. Install, Repair and Update are paused until those records can be checked.",
      steps: [
        "Select Check again.",
        "If the problem stays, create a support report. Review it before sharing.",
      ],
      note: "Restarting or reinstalling SDE does not guarantee those records can be read. Do not delete them to unlock changes.",
    };
  if (
    state.nativeSafety.packageHealth === "incomplete" &&
    state.effectiveActivity === "inactive"
  )
    return {
      explanation:
        "An installation needs attention before SDE can make more changes. Install, Repair and Update are paused.",
      steps: [
        "Open Technical details for the repair instructions for your computer.",
        "After following those instructions, select Check again.",
      ],
      note: "SDE will not run these repairs automatically. Acknowledging the interruption does not fix the installation.",
    };
  if (state.effectiveActivity === "unknown")
    return {
      explanation: `${state.machine.incidentId || state.user.incident ? "SDE found an unfinished setup or update. It" : "SDE"} can’t tell whether setup or update work has stopped. Install, Repair and Update are paused to avoid starting two changes at once.`,
      steps: [
        "Save your work.",
        /windows/i.test(platformLabel)
          ? "Restart your computer using Start → Power → Restart."
          : "Restart your computer using the normal Restart option in its power menu.",
        "Open SDE and select Check again.",
      ],
      note: "Restarting helps SDE check whether it’s safe to continue. It doesn’t automatically fix an unfinished installation.",
    };
  if (state.readiness === "needs_acknowledgment")
    return {
      explanation:
        "A setup or update didn’t finish. Review this notice, then acknowledge the interruption if you want to try again.",
      steps: [
        "Choose the acknowledgment button below. SDE will check safety again before you start a change.",
      ],
      note: "Acknowledging does not mean the earlier setup finished or was fixed.",
    };
  if (state.readiness === "blocked")
    return {
      explanation:
        "SDE needs another safety check before it can make changes. Install, Repair and Update are paused.",
      steps: [
        "Select Check again.",
        "If changes are still paused, create a support report.",
      ],
      note: "A report helps explain a problem; it does not unlock changes.",
    };
  return {
    explanation:
      "No current safety blocker was found. You can return to Overview and choose what to do next.",
    steps: [
      "SDE will check again before starting a change. Your usual review and administrator approval still apply.",
    ],
    note:
      state.nativeSafety.packageHealth === "unknown"
        ? "Installed packages have not been fully verified. This alone does not stop you from continuing, but it is not proof that an earlier installation finished."
        : "This check does not prove that an earlier setup or update finished.",
  };
}

export function RecoveryPage({
  state,
  loading,
  error,
  pending,
  outcomes,
  platformLabel = "",
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
  platformLabel?: string;
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
  const ready = state?.readiness === "ready_for_native_recheck";
  const acknowledgePrimary = canAcknowledge && state?.readiness !== "blocked";
  const continuePrimary = !canAcknowledge && !!pending && ready;
  const canValidate =
    state?.effectiveActivity === "inactive" &&
    state.nativeSafety.trust === "trusted";
  const submitted =
    !!state?.machine.available &&
    !!state.machine.incidentId &&
    (state.machine.intentSubmitted || state.machine.acknowledgedAt !== null);
  const accountAcknowledged =
    !!state?.user.available &&
    !!state.user.incident &&
    state.user.acknowledgment?.incidentId === state.user.incident.id;
  const advice = nextStep(state, platformLabel);
  // A presentation-only snapshot, never permission to execute a change.
  // Unknown package health alone is nonblocking; unknown activity is not.
  const clear =
    ready &&
    !canAcknowledge &&
    !pending &&
    !error &&
    state?.effectiveActivity === "inactive" &&
    state.nativeSafety.trust === "trusted" &&
    state.nativeSafety.packageHealth !== "incomplete" &&
    state.machine.available &&
    state.user.available;
  return (
    <>
      {clear && (
        <section
          className="recovery-page recovery-page-clear"
          aria-labelledby="recovery-heading"
          aria-busy={loading}
        >
          <h2 id="recovery-heading">
            There is nothing to recover from right now
          </h2>
          <p>
            No current safety blocker was found. You can return to Overview and
            choose what to do next.
          </p>
          <p>
            If you need, you can still create a support report to collect
            information you can share if you choose. Review it before sharing;
            it may identify your computer or account.
          </p>
          <div>
            <button
              className="secondary"
              disabled={loading}
              onClick={onSupport}
            >
              Create support report
            </button>
          </div>
        </section>
      )}
      <section
        className={clear ? "recovery-diagnostics" : "recovery-page"}
        aria-labelledby={clear ? undefined : "recovery-heading"}
        aria-busy={loading}
      >
        {!clear && (
          <>
            <h2 id="recovery-heading">Let’s get setup working again</h2>
            <p>{advice.explanation}</p>
            {submitted && (
              <p>
                SDE has your acknowledgment for this computer. You don’t need to
                submit that acknowledgment again.
              </p>
            )}
            {accountAcknowledged && (
              <p>Your acknowledgment for this account is saved.</p>
            )}
            {error && <p role="alert">{error}</p>}
            <h3>What to do now</h3>
            <ol>
              {advice.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            <p>{advice.note}</p>
            {canAcknowledge && (
              <p>
                When you acknowledge, SDE keeps the original record and tries to
                save a report automatically. No separate save step is needed.
                {state?.readiness === "blocked" &&
                  " You can acknowledge now, but changes will stay paused until the safety checks allow them."}
              </p>
            )}
            {pending && (
              <p>
                Requested action: {pending}. You’ll review it before it starts.
                Back to Overview cancels this request; SDE won’t replay it after
                restart.
              </p>
            )}
          </>
        )}
        {outcomes.map((outcome, index) => (
          <div key={`${outcome.incidentId}-${index}`} role="status">
            <p>
              {outcome.reportId
                ? "A recovery report was saved on this account."
                : "A recovery report could not be saved."}
            </p>
            {outcome.reportWarning && <p>{outcome.reportWarning}</p>}
            {outcome.intentWarning && <p>{outcome.intentWarning}</p>}
            {outcome.acknowledgmentWarning && (
              <p>{outcome.acknowledgmentWarning}</p>
            )}
          </div>
        ))}
        {!clear && (
          <>
            <div className="result-actions">
              {canAcknowledge && (
                <button
                  className={acknowledgePrimary ? "primary" : "secondary"}
                  disabled={loading}
                  onClick={onAcknowledge}
                >
                  {pending && acknowledgePrimary
                    ? "Acknowledge and continue"
                    : "Acknowledge interruption"}
                </button>
              )}
              {continuePrimary && (
                <button
                  className="primary"
                  disabled={loading}
                  onClick={onContinue}
                >
                  Continue with {pending}
                </button>
              )}
              <button
                className={
                  acknowledgePrimary || continuePrimary
                    ? "secondary"
                    : "primary"
                }
                disabled={loading}
                onClick={onCheck}
              >
                Check again
              </button>
              {canValidate && (
                <button
                  className="secondary"
                  disabled={loading}
                  onClick={onValidate}
                >
                  Run validation
                </button>
              )}
              <button
                className="text-button"
                disabled={loading}
                onClick={onCancel}
              >
                Back to Overview
              </button>
            </div>
            <div className="recovery-support">
              <p>
                Still stuck? Create a support report to collect information you
                can share if you choose. Review it before sharing; it may
                identify your computer or account.
              </p>
              <button
                className="secondary"
                disabled={loading}
                onClick={onSupport}
              >
                Create support report
              </button>
            </div>
          </>
        )}
        <details className="recovery-disclosure">
          <summary>Technical details</summary>
          {state ? (
            <>
              <dl className="recovery-findings">
                <dt>Last checked</dt>
                <dd>{when(state.nativeSafety.observedAt)}</dd>
                <dt>Setup activity</dt>
                <dd>
                  {state.effectiveActivity === "active"
                    ? "A setup or update is running."
                    : state.effectiveActivity === "inactive"
                      ? "No active setup was detected."
                      : "SDE couldn’t tell whether setup is still running."}
                </dd>
                <dt>Installed packages</dt>
                <dd>
                  {state.nativeSafety.packageHealth === "unknown"
                    ? "Not verified."
                    : state.nativeSafety.packageHealth === "incomplete"
                      ? "An installation reports unfinished work."
                      : "No package problem was detected."}
                </dd>
                <dt>Computer safety records</dt>
                <dd>
                  {state.nativeSafety.trust === "trusted"
                    ? "Verified."
                    : state.nativeSafety.trust === "untrusted"
                      ? "Could not be trusted."
                      : "Could not be verified."}
                </dd>
              </dl>
              <h3>This computer’s interruption</h3>
              <p>
                {!state.machine.available
                  ? "Computer records could not be read. This does not mean the problem is cleared."
                  : state.machine.incidentId
                    ? `Incident reference: ${state.machine.incidentId}`
                    : "No current machine incident recorded."}
              </p>
              {state.machine.incidentId && (
                <p>
                  {state.machine.acknowledgedAt !== null
                    ? `Acknowledgment recorded ${when(state.machine.acknowledgedAt)}. SDE still rechecks safety before a change.`
                    : state.machine.intentSubmitted
                      ? "Acknowledgment submitted. SDE still needs to confirm it during the normal administrator-approved safety check. This does not give permission to start a change."
                      : "Not acknowledged."}
                </p>
              )}
              <h3>This account’s interruption</h3>
              <p>
                {!state.user.available
                  ? "Account records could not be read. This does not mean the problem is cleared."
                  : state.user.incident
                    ? `${state.user.incident.operation} stopped during ${state.user.incident.stage}. Incident reference: ${state.user.incident.id}. Started ${when(state.user.incident.startedAt)}; last recorded ${when(state.user.incident.observedAt)}.`
                    : "No current account incident recorded."}
              </p>
              {state.user.incident && (
                <p>
                  {accountAcknowledged
                    ? `Account acknowledgment recorded ${when(state.user.acknowledgment!.acknowledgedAt)}.`
                    : "This account’s interruption has not been acknowledged."}{" "}
                  Restart check: {state.user.restart}. A free setup lock alone
                  does not prove an earlier installer stopped.
                </p>
              )}
              <h3>More guidance</h3>
              <p>{state.guidance.title}</p>
              <ul>
                {state.guidance.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
            </>
          ) : (
            <p>
              Recovery findings are unavailable. Check again or create a support
              report. No change has been authorized.
            </p>
          )}
          {outcomes.some((outcome) => outcome.reportId) && (
            <>
              <h3>Reports from this visit</h3>
              <ul>
                {outcomes
                  .filter((outcome) => outcome.reportId)
                  .map((outcome, index) => (
                    <li key={`${outcome.reportId}-${index}`}>
                      Local summary saved: {outcome.reportId}.
                    </li>
                  ))}
              </ul>
            </>
          )}
          <p>
            Do not delete setup records, remove installation locks or force
            installer processes to close. Passing validation does not
            acknowledge an interruption or prove that setup finished.
          </p>
          <button className="secondary" disabled={loading} onClick={onLogs}>
            Open logs
          </button>
        </details>
      </section>
    </>
  );
}
