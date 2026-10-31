import { useEffect, useRef, useState } from "react";
import {
  listRecoveryIncidents,
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
    } catch {
      if (live.current)
        setError(
          `${source === "machine" ? "Machine" : "Account"} incident history is unavailable. This is not an empty or cleared history. Refresh when the current operation finishes; keep the original evidence.`,
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
  return (
    <div aria-busy={working}>
      <h3>
        {source === "machine"
          ? "Machine archive observations"
          : "This account’s retained incidents"}
      </h3>
      {observed && (
        <p>
          Last observed {new Date(observed * 1000).toLocaleString()}. Refresh to
          check current retained state.
        </p>
      )}
      {error && <p role="alert">{error}</p>}
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
          No retained {source} entries were found in this source. Current
          incidents are shown above; absence here does not establish completion
          or acknowledgment.
        </p>
      )}
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
          </li>
        ))}
      </ul>
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
      <h2 id="incident-history-heading">Retained incident observations</h2>
      <p>
        These observations come from minimum operational state, not the saved
        report list. Failed report saving or report deletion does not remove
        them. History is read-only here: no acknowledgment, deletion, repair or
        operation is performed.
      </p>
      <p>
        Machine archive names do not reveal private journal or receipt contents.
        Partial publication, multiple generations or unavailable state cannot be
        treated as proof of completion or permission to proceed.
      </p>
      <SourceHistory source="machine" disabled={disabled} />
      <SourceHistory source="user" disabled={disabled} />
    </section>
  );
}
