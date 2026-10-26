import { useEffect, useMemo, useRef, useState } from "react";
import { FileDown, LoaderCircle, X } from "lucide-react";
import { appVersion, saveSupportReport, supportContext } from "./bridge";
import type { Check } from "./model";
import type {
  MaintenanceObservation,
  OperationIncident,
} from "./safeOperations";
import {
  supportHtml,
  supportSnapshot,
  type SupportContext,
} from "./supportReport";

export function SupportReportDialog({
  checks,
  validationComplete,
  platform,
  incident,
  maintenance,
  onClose,
}: {
  checks: Check[];
  validationComplete: boolean;
  platform: string;
  incident: OperationIncident | null;
  maintenance: MaintenanceObservation | null;
  onClose: () => void;
}) {
  const [includeLogs, setIncludeLogs] = useState(false);
  const [context, setContext] = useState<SupportContext | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const closeButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    closeButton.current?.focus();
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("keydown", escape);
      previous?.focus();
    };
  }, [onClose]);
  useEffect(() => {
    setContext(null);
    setError("");
    supportContext(includeLogs)
      .then(setContext)
      .catch(() =>
        setError("The report preview could not be prepared. Try again."),
      );
  }, [includeLogs]);
  const html = useMemo(() => {
    if (!context) return "";
    return supportHtml(
      supportSnapshot({
        context,
        platform,
        applicationVersion: appVersion,
        checks,
        validationComplete,
        incident,
        maintenance,
        includeLogs,
      }),
    );
  }, [
    checks,
    context,
    includeLogs,
    incident,
    maintenance,
    platform,
    validationComplete,
  ]);
  return (
    <section
      className="report-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="report-heading"
    >
      <div className="section-header">
        <div>
          <p className="eyebrow">SUPPORT REPORT</p>
          <h2 id="report-heading">Preview exactly what will be shared</h2>
        </div>
        <button
          ref={closeButton}
          className="secondary"
          onClick={onClose}
          aria-label="Close support report"
        >
          <X size={16} /> Close
        </button>
      </div>
      <label className="report-log-option">
        <input
          type="checkbox"
          checked={includeLogs}
          onChange={(event) => setIncludeLogs(event.currentTarget.checked)}
        />
        Include recent application logs. Logs are excluded by default and may
        contain detailed workstation paths.
      </label>
      {error ? (
        <div className="notice" role="alert">
          {error}
        </div>
      ) : !html ? (
        <p role="status">
          <LoaderCircle className="spinner" size={18} /> Preparing preview…
        </p>
      ) : (
        <iframe title="Exact support report preview" srcDoc={html} />
      )}
      <div className="result-actions">
        <button
          className="primary"
          disabled={!html}
          onClick={async () => {
            setSaved("");
            setError("");
            try {
              const path = await saveSupportReport(html);
              if (path) setSaved(path);
            } catch {
              setError("The support report could not be saved. Try again.");
            }
          }}
        >
          <FileDown size={16} /> Save support report
        </button>
      </div>
      {saved && <p role="status">Report saved to {saved}</p>}
    </section>
  );
}
