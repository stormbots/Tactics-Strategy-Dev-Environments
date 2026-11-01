import { useEffect, useRef, useState } from "react";
import {
  listRecoveryIncidents,
  deleteRecoveryHistoryView,
  type HistorySource,
  type IncidentHistoryEntry,
} from "./recoveryIncidents";

function SourceHistory({
  source,
  disabled,
}: {
  source: HistorySource;
  disabled: boolean;
}) {
  const [entries, setEntries] = useState<IncidentHistoryEntry[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [observed, setObserved] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  const [unexpected, setUnexpected] = useState(false);
  const [hidden, setHidden] = useState(0);
  const [viewStateUnavailable, setViewStateUnavailable] = useState(false);
  const [confirmation, setConfirmation] = useState<IncidentHistoryEntry | null>(
    null,
  );
  const [notice, setNotice] = useState("");
  const confirmHeading = useRef<HTMLParagraphElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (confirmation) confirmHeading.current?.focus();
  }, [confirmation]);
  const active = useRef(false);
  const live = useRef(true);
  async function load(next: string | null = null) {
    if (disabled || active.current) return;
    active.current = true;
    setWorking(true);
    setError("");
    try {
      const result = await listRecoveryIncidents(source, next);
      const page = result[source];
      if (!page) throw new Error("Missing history source");
      if (!live.current) return;
      setEntries((previous) =>
        next
          ? [
              ...previous,
              ...page.entries.filter(
                (entry) =>
                  !previous.some((old) => old.incidentId === entry.incidentId),
              ),
            ]
          : page.entries,
      );
      setCursor(page.nextCursor);
      setObserved(result.observedAt);
      setUnexpected(!!page.unexpectedEntries);
      setViewStateUnavailable(!!result.viewStateUnavailable);
      setHidden((previous) =>
        next ? previous + (result.hiddenViews ?? 0) : (result.hiddenViews ?? 0),
      );
      setConfirmation(null);
    } catch {
      if (live.current)
        setError(
          `${source === "machine" ? "Computer" : "Account"} history is unavailable. Try Refresh after setup finishes. Nothing was cleared.`,
        );
    } finally {
      active.current = false;
      if (live.current) setWorking(false);
    }
  }
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
    };
  }, []);
  useEffect(() => {
    if (!disabled && observed === null) void load();
  }, [disabled]);
  async function deleteView() {
    if (disabled || active.current || !confirmation?.viewToken) return;
    const selected = confirmation;
    active.current = true;
    setWorking(true);
    setError("");
    setNotice("");
    try {
      await deleteRecoveryHistoryView(selected.viewToken!);
      if (!live.current) return;
      setEntries((previous) =>
        previous.filter((entry) => entry.incidentId !== selected.incidentId),
      );
      setHidden((previous) => previous + 1);
      setConfirmation(null);
      setNotice(
        "Selected history view deleted for this account. Minimum operational evidence, acknowledgment, reports and safety gates are unchanged; no operation was authorized.",
      );
    } catch {
      if (live.current) {
        setConfirmation(null);
        setError(
          "History view deletion is unconfirmed or the entry changed. Refresh history before trying again. No incident was acknowledged or cleared.",
        );
      }
    } finally {
      active.current = false;
      if (live.current) setWorking(false);
    }
  }
  return (
    <div aria-busy={working}>
      <h3>{source === "machine" ? "This computer" : "Your account"}</h3>
      {observed && (
        <p>Last checked: {new Date(observed * 1000).toLocaleString()}.</p>
      )}
      {error && <p role="alert">{error}</p>}
      {viewStateUnavailable && (
        <p>
          Some history-view preferences are unavailable. Affected entries remain
          visible, but their view deletion is disabled. Operational evidence and
          safety checks are unchanged.
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      {hidden > 0 && (
        <p>
          {hidden} deleted history {hidden === 1 ? "view is" : "views are"}{" "}
          excluded from these pages. Original operational records remain; this
          is not cleared evidence.
        </p>
      )}
      {unexpected && (
        <p>
          Unexpected account-history entries were detected. The list is not a
          complete verified history; no files were removed.
        </p>
      )}
      <button
        className="secondary"
        disabled={disabled || working}
        onClick={() => void load()}
      >
        Refresh {source} incident history
      </button>
      {observed && !error && !entries.length && (
        <p>
          No earlier events are shown for{" "}
          {source === "machine" ? "this computer" : "your account"}. Hidden
          views are not listed. Current problems appear above; an empty history
          does not mean setup finished.
        </p>
      )}
      {entries.length > 0 && (
        <ul>
          {entries.map((entry) => (
            <li key={entry.incidentId}>
              <p>Incident {entry.incidentId}</p>
              <p>
                {entry.status === "archive_observed_acknowledgment_unknown"
                  ? "Protected archive filename observed. Private contents were not read; acknowledgment status is unknown."
                  : entry.status === "acknowledgment_observed"
                    ? "Matching retained account acknowledgment observed. This is not an execution permit."
                    : entry.status === "ambiguous_generations"
                      ? "Multiple retained generations share this incident ID. They have not been combined into one acknowledgment; details are ambiguous."
                      : entry.status === "unavailable"
                        ? "Retained evidence or acknowledgment could not be verified. No cleared state is inferred."
                        : "Acknowledgment status is unknown, not proven absent."}
              </p>
              {entry.context && (
                <p>
                  Recorded {entry.context.incident.operation} /{" "}
                  {entry.context.incident.stage}; started{" "}
                  {new Date(
                    entry.context.incident.startedAt * 1000,
                  ).toLocaleString()}
                  ; last recorded{" "}
                  {new Date(
                    entry.context.incident.observedAt * 1000,
                  ).toLocaleString()}
                  .
                </p>
              )}
              {entry.acknowledgment && (
                <p>
                  Acknowledged{" "}
                  {new Date(
                    entry.acknowledgment.acknowledgedAt * 1000,
                  ).toLocaleString()}
                  .{" "}
                  {entry.acknowledgment.reportId
                    ? `Original report reference ${entry.acknowledgment.reportId}; the report may no longer exist.`
                    : "No saved report reference. The operational decision exists independently."}
                </p>
              )}
              <p>Continuation/completion: not recorded.</p>
              {entry.viewToken ? (
                <button
                  className="secondary"
                  disabled={disabled || working}
                  onClick={() => {
                    returnFocus.current = document.activeElement as HTMLElement;
                    setConfirmation(entry);
                  }}
                >
                  Delete {source} history view {entry.incidentId}
                </button>
              ) : (
                <p>
                  View deletion is unavailable for this snapshot. Refresh
                  history; do not remove operational files.
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
      {confirmation && (
        <div
          role="group"
          aria-label={`Confirm ${source} history view deletion`}
          className="notice"
        >
          <p ref={confirmHeading} tabIndex={-1}>
            Delete the displayed {source} history view for incident{" "}
            {confirmation.incidentId} from this account? Minimum evidence and
            decisions remain, reports and other accounts are unaffected, and a
            changed incident reappears. This does not acknowledge, repair or
            authorize changes.
          </p>
          <div className="result-actions">
            <button
              className="secondary"
              disabled={disabled || working}
              onClick={() => {
                setConfirmation(null);
                returnFocus.current?.focus();
              }}
            >
              Keep {source} history view
            </button>
            <button
              className="primary"
              disabled={disabled || working}
              onClick={() => void deleteView()}
            >
              Confirm delete {source} history view
            </button>
          </div>
        </div>
      )}
      {cursor && (
        <button
          className="secondary"
          disabled={disabled || working}
          onClick={() => void load(cursor)}
        >
          Load more {source} incidents
        </button>
      )}
    </div>
  );
}
export function RecoveryIncidentHistory({
  disabled = false,
}: {
  disabled?: boolean;
}) {
  return (
    <section
      className="validation-card recovery-history"
      aria-labelledby="incident-history-heading"
    >
      <h2 id="incident-history-heading">Recovery event history</h2>
      <p>
        These are earlier setup records for this computer and your account. They
        can remain even if a report was not saved or was deleted.
      </p>
      <p>
        Deleting a history view hides it for your account. It does not fix a
        problem, delete SDE’s safety records or unlock changes. A changed record
        will show again.
      </p>
      <SourceHistory source="machine" disabled={disabled} />
      <SourceHistory source="user" disabled={disabled} />
    </section>
  );
}
