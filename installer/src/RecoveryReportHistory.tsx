import { useEffect, useRef, useState } from "react";
import {
  deleteRecoveryReport,
  exportRecoveryReport,
  listRecoveryReports,
  readRecoveryReport,
  type RecoveryReportDetails,
  type RecoveryReportEntry,
} from "./recoveryReports";
function when(value: number | null) {
  return value ? new Date(value * 1000).toLocaleString() : "unavailable";
}

export function RecoveryReportHistory({
  disabled = false,
  recentReports = [],
}: {
  disabled?: boolean;
  recentReports?: string[];
}) {
  const [entries, setEntries] = useState<RecoveryReportEntry[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [details, setDetails] = useState<RecoveryReportDetails | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const active = useRef(false);
  const live = useRef(true);
  const heading = useRef<HTMLHeadingElement>(null);
  const confirmation = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (details) heading.current?.focus();
  }, [details]);
  useEffect(() => {
    if (confirmDelete) confirmation.current?.focus();
  }, [confirmDelete]);
  async function perform(action: () => Promise<void>) {
    if (active.current || disabled) return;
    active.current = true;
    setWorking(true);
    setError("");
    setNotice("");
    try {
      await action();
    } catch {
      if (live.current)
        setError(
          "Report action could not be completed or confirmed. Refresh history and check the selected report. Operational evidence and acknowledgment are separate and have not been cleared by this action.",
        );
    } finally {
      active.current = false;
      if (live.current) setWorking(false);
    }
  }
  async function load(next: string | null = null) {
    await perform(async () => {
      const page = await listRecoveryReports(next);
      if (!live.current) return;
      setEntries((previous) =>
        next
          ? [
              ...previous,
              ...page.entries.filter(
                (entry) =>
                  !previous.some(
                    (existing) => existing.reportId === entry.reportId,
                  ),
              ),
            ]
          : page.entries,
      );
      setCursor(page.nextCursor);
      setLoaded(true);
      if (!next) {
        setDetails(null);
        setConfirmDelete(null);
      }
    });
  }
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
    };
  }, []);
  useEffect(() => {
    if (!disabled && !loaded) void load();
  }, [disabled]);
  async function view(id: string) {
    setDetails(null);
    setConfirmDelete(null);
    await perform(async () => {
      const result = await readRecoveryReport(id);
      if (live.current) setDetails(result);
    });
  }
  async function exportSelected() {
    if (!details) return;
    await perform(async () => {
      const path = await exportRecoveryReport(details.reportId);
      if (live.current)
        setNotice(
          path
            ? `Exported a copy to ${path}. Share it only with someone you choose; SDE did not upload it.`
            : "Export canceled. The retained local report is unchanged.",
        );
    });
  }
  async function removeSelected() {
    const id = confirmDelete;
    if (!id) return;
    await perform(async () => {
      await deleteRecoveryReport(id);
      if (!live.current) return;
      setEntries((previous) =>
        previous.filter((entry) => entry.reportId !== id),
      );
      setDetails(null);
      setConfirmDelete(null);
      setNotice(
        "Selected local report deleted. This cannot be undone here; previously exported copies are unaffected. Operational evidence and minimum acknowledgment state remain; deletion does not authorize changes.",
      );
    });
  }
  const busy = disabled || working;
  return (
    <section
      className="validation-card recovery-history"
      aria-labelledby="recovery-history-heading"
      aria-busy={working}
    >
      <h2 id="recovery-history-heading">Report history</h2>
      <p>
        Reports stay in this account until you delete them. They help explain a
        problem but do not fix it or unlock changes. Sharing is optional.
      </p>
      <p>
        Viewing or deleting a report does not acknowledge an interruption or
        start setup. Saved summaries do not include detailed logs; use Create
        support report if you want to include those.
      </p>
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      <button className="secondary" disabled={busy} onClick={() => void load()}>
        Refresh report history
      </button>
      {recentReports.length > 0 && (
        <div className="result-actions" aria-label="Recently captured reports">
          {[...new Set(recentReports)].map((id) => (
            <button
              className="secondary"
              disabled={busy}
              key={id}
              onClick={() => void view(id)}
            >
              View recent report {id}
            </button>
          ))}
        </div>
      )}
      {loaded && !entries.length && (
        <p>
          No saved reports were found for this account. Reports may be missing
          or deleted; this list does not show every interruption or prove setup
          finished.
        </p>
      )}
      {entries.length > 0 && (
        <ul className="recovery-report-list">
          {entries.map((entry) => (
            <li key={entry.reportId}>
              <p>
                Report {entry.reportId} —{" "}
                {entry.status === "saved"
                  ? `captured ${when(entry.capturedAt)}; incident ${entry.incidentId}`
                  : "incomplete or unreadable; not a saved summary"}
              </p>
              <button
                className="secondary"
                disabled={busy || entry.status !== "saved"}
                onClick={() => void view(entry.reportId)}
              >
                View report {entry.reportId}
              </button>
              <button
                className="secondary"
                disabled={busy}
                onClick={() => setConfirmDelete(entry.reportId)}
              >
                Delete local report {entry.reportId}
              </button>
            </li>
          ))}
        </ul>
      )}
      {cursor && (
        <button
          className="secondary"
          disabled={busy}
          onClick={() => void load(cursor)}
        >
          Load more reports
        </button>
      )}
      {details && (
        <div className="recovery-report-details">
          <h3 ref={heading} tabIndex={-1}>
            Selected recovery summary
          </h3>
          <p>
            Report {details.reportId}. Source:{" "}
            {details.acknowledgment.source ?? "unavailable"}.
          </p>
          <p>
            Acknowledgment observation: {details.acknowledgment.status}.
            Observed {when(details.acknowledgment.observedAt)}. Recorded
            acknowledgment: {when(details.acknowledgment.acknowledgedAt)}.
          </p>
          <p>{details.acknowledgment.note}</p>
          <p>
            Continuation/completion: not recorded. Do not infer that the
            interrupted operation finished.
          </p>
          <iframe
            title="Retained recovery summary preview"
            sandbox=""
            referrerPolicy="no-referrer"
            srcDoc={details.html}
          />
          <p>
            This summary may identify this device or account. Review it before
            sharing. Export saves a copy using the ordinary save window; it
            never uploads the report. Choose a new filename outside SDE
            application data; existing files are never overwritten.
          </p>
          <div className="result-actions">
            <button
              className="primary"
              disabled={busy}
              onClick={() => void exportSelected()}
            >
              Export report copy
            </button>
            <button
              className="secondary"
              disabled={busy}
              onClick={() => setConfirmDelete(details.reportId)}
            >
              Delete selected local report
            </button>
            <button
              className="secondary"
              disabled={busy}
              onClick={() => setDetails(null)}
            >
              Close report preview
            </button>
          </div>
        </div>
      )}
      {confirmDelete && (
        <div
          role="group"
          aria-label="Confirm local report deletion"
          className="notice"
        >
          <p ref={confirmation} tabIndex={-1}>
            Delete only local report {confirmDelete}? This cannot be undone
            here. Existing exported copies, original operational evidence and
            minimum acknowledgment state will remain. This does not clear an
            incident or enable changes.
          </p>
          <div className="result-actions">
            <button
              className="secondary"
              disabled={busy}
              onClick={() => setConfirmDelete(null)}
            >
              Keep local report
            </button>
            <button
              className="primary"
              disabled={busy}
              onClick={() => void removeSelected()}
            >
              Confirm delete local report
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
