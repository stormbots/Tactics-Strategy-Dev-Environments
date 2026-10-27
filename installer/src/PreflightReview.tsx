import { useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { checkPreflight } from "./updateDiscovery";
import {
  preflightDecision,
  type OperationKind,
  type PreflightCheck,
} from "./safeOperations";

export function PreflightReview({
  operation,
  platformSupported,
  onContinue,
  onCancel,
}: {
  operation: Extract<OperationKind, "install" | "update">;
  platformSupported: boolean;
  onContinue: (acknowledgedUncertainty: boolean) => void;
  onCancel: () => void;
}) {
  const [checks, setChecks] = useState<PreflightCheck[] | null>(null);
  const [completed, setCompleted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const live = useRef(true);
  const heading = useRef<HTMLHeadingElement>(null);
  const label = operation === "install" ? "Install" : "Update";

  async function refresh() {
    if (loading) return;
    setLoading(true);
    setCompleted(false);
    setChecks(null);
    setAcknowledged(false);
    setError("");
    try {
      const rows = await checkPreflight(operation);
      if (live.current) setChecks(rows);
    } catch {
      if (live.current)
        setError(
          "Preflight could not produce a complete result. This is unavailable information, not a pass.",
        );
    } finally {
      if (live.current) {
        setCompleted(true);
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    live.current = true;
    heading.current?.focus();
    void refresh();
    return () => {
      live.current = false;
    };
  }, []);

  const decision = preflightDecision(completed ? checks : [], acknowledged);
  const blocked = !platformSupported || decision.blocked;
  const needsAcknowledgement =
    completed && (decision.needsAcknowledgement || !!error);
  const clean = completed && !blocked && !needsAcknowledgement;
  const canContinue =
    completed &&
    !loading &&
    !blocked &&
    (clean || (needsAcknowledgement && acknowledged));

  return (
    <section
      className="information-card preflight-review"
      aria-labelledby={`${operation}-preflight-heading`}
      aria-busy={loading}
    >
      <h2 id={`${operation}-preflight-heading`} tabIndex={-1} ref={heading}>
        Before {label} begins
      </h2>
      <p>
        SDE checks this laptop before requesting administrator approval. No
        provisioning or package changes have started.
      </p>
      <p
        role="status"
        className={blocked ? "preflight-summary blocking" : "preflight-summary"}
      >
        {loading
          ? `Checking ${label.toLowerCase()} prerequisites…`
          : !completed
            ? "Preflight has not completed."
            : blocked
              ? `${label} cannot begin until the blocking condition is resolved.`
              : clean
                ? `${decision.passed} prerequisite checks passed.`
                : "Review the warnings or unavailable checks before continuing."}
      </p>
      {error && (
        <p className="preflight-row unavailable">
          <strong>Preflight result — Unavailable</strong>
          <span>{error}</span>
        </p>
      )}
      {clean ? (
        <details className="preflight-details">
          <summary>Show passed checks</summary>
          {checks?.map((check) => (
            <PreflightRow key={check.name} check={check} />
          ))}
        </details>
      ) : (
        checks?.map((check) => <PreflightRow key={check.name} check={check} />)
      )}
      {needsAcknowledgement && !blocked && (
        <label className="preflight-ack">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(event) => setAcknowledged(event.target.checked)}
          />{" "}
          I reviewed the warnings and unavailable checks. {label} may still
          fail.
        </label>
      )}
      <div className="result-actions">
        <button
          className="primary"
          disabled={!canContinue}
          onClick={() => onContinue(acknowledged)}
        >
          Continue with {label}
        </button>
        <button
          className="secondary"
          disabled={loading}
          onClick={() => void refresh()}
        >
          <RefreshCw size={16} aria-hidden="true" />
          Check Again
        </button>
        <button className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
      <p className="muted">
        SDE checks race-sensitive conditions again before changes. A successful
        preflight cannot guarantee that later downloads or installation will
        succeed.
      </p>
    </section>
  );
}

function PreflightRow({ check }: { check: PreflightCheck }) {
  return (
    <p className={`preflight-row ${check.status}`}>
      <strong>
        {check.name} —{" "}
        {check.status === "blocking" ? "Action needed" : check.status}
      </strong>
      <span>{check.detail}</span>
    </p>
  );
}
