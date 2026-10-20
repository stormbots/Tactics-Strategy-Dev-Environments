import { useEffect, useRef, useState } from "react";
import type { ToolRecord } from "./model";
import {
  checkApplication,
  checkTools,
  checkPreflight,
  failureText,
  openRelease,
  toolExplanation,
  usableRetryTime,
  type AppDiscovery,
  type ToolPreview,
  type PreflightCheck,
} from "./updateDiscovery";
import { localTime } from "./DetailsPages";

export function useUpdateDiscovery(
  snapshot: ToolRecord[],
  generation: number,
  enabled: boolean,
) {
  const [application, setApplication] = useState<AppDiscovery | null>(null);
  const [appLoading, setAppLoading] = useState(false);
  const [appError, setAppError] = useState("");
  const [lastSuccess, setLastSuccess] = useState<number | null>(null);
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem("sde-dismissed-release") || "";
    } catch {
      return "";
    }
  });
  const [preview, setPreview] = useState<ToolPreview | null>(null);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [toolsError, setToolsError] = useState("");
  const appPending = useRef(false);
  const toolsPending = useRef(false);
  const epoch = useRef(0);
  const latest = useRef({ snapshot, generation, enabled });
  latest.current = { snapshot, generation, enabled };
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      epoch.current++;
    };
  }, []);
  async function refreshApp() {
    if (appPending.current || usableRetryTime(application?.retryAt) !== null)
      return;
    appPending.current = true;
    setAppLoading(true);
    setAppError("");
    setApplication(null);
    try {
      const data = await checkApplication();
      if (mounted.current) {
        setApplication(data);
        if (!data.failure) setLastSuccess(data.checkedAt);
      }
    } catch {
      if (mounted.current)
        setAppError(
          "SDE discovery could not finish. Try again later; your local validation is unchanged.",
        );
    } finally {
      appPending.current = false;
      if (mounted.current) setAppLoading(false);
    }
  }
  async function refreshTools() {
    if (toolsPending.current || !latest.current.enabled) return;
    const id = epoch.current;
    const source = latest.current;
    toolsPending.current = true;
    setToolsLoading(true);
    setToolsError("");
    try {
      const result = await checkTools(source.snapshot);
      if (mounted.current && id === epoch.current) setPreview(result);
    } catch (e) {
      if (mounted.current && id === epoch.current) {
        setPreview(null);
        setToolsError(
          e instanceof Error ? e.message : "Tool discovery unavailable. Retry.",
        );
      }
    } finally {
      toolsPending.current = false;
      if (mounted.current) {
        setToolsLoading(false);
        if (id !== epoch.current && latest.current.enabled) void refreshTools();
      }
    }
  }
  useEffect(() => {
    void refreshApp();
  }, []);
  const snapshotKey = snapshot
    .map((t) => `${t.tool}:${t.installedVersion}`)
    .join("|");
  useEffect(() => {
    epoch.current++;
    setPreview(null);
    setToolsError("");
    if (enabled && snapshot.length) void refreshTools();
  }, [snapshotKey, generation, enabled]);
  function dismiss() {
    const tag = application?.candidate?.tag;
    if (!tag) return;
    setDismissed(tag);
    try {
      localStorage.setItem("sde-dismissed-release", tag);
    } catch {
      /* Session dismissal still works. */
    }
  }
  return {
    application,
    appLoading,
    appError,
    lastSuccess,
    refreshApp,
    dismiss,
    dismissed,
    preview,
    toolsLoading,
    toolsError,
    refreshTools,
  };
}
export type Discovery = ReturnType<typeof useUpdateDiscovery>;
export function ApplicationUpdates({
  data,
  about = false,
}: {
  data: Discovery;
  about?: boolean;
}) {
  const [error, setError] = useState("");
  const app = data.application;
  const [clock, refreshClock] = useState(0);
  const retryAt = usableRetryTime(app?.retryAt);
  const retryBlocked = retryAt !== null;
  useEffect(() => {
    if (!retryBlocked || !app?.retryAt) return;
    const timer = setTimeout(
      () => refreshClock((n) => n + 1),
      Math.min((app.retryAt - Date.now() / 1000) * 1000 + 100, 2147483647),
    );
    return () => clearTimeout(timer);
  }, [app?.retryAt, retryBlocked, clock]);
  const candidate = app?.candidate;
  const visible = candidate && candidate.tag !== data.dismissed;
  if (!about && !visible && !data.appError && !app?.failure) return null;
  async function open(installer = false) {
    try {
      await openRelease(candidate?.tag ?? null, installer);
    } catch {
      setError("Your browser could not be opened. Try again.");
    }
  }
  return (
    <section
      className="information-card update-discovery"
      aria-labelledby={
        about ? "about-update-heading" : "overview-update-heading"
      }
    >
      <h2 id={about ? "about-update-heading" : "overview-update-heading"}>
        SDE application updates
      </h2>
      <p role="status">
        {data.appLoading
          ? "Checking official SDE releases…"
          : data.appError ||
            (app?.failure
              ? failureText[app.failure] ||
                "SDE update check unavailable. Try again later."
              : candidate
                ? `SDE ${candidate.version} is available. This window runs ${app?.version}.`
                : app
                  ? `No newer stable SDE release found for ${app.version}.`
                  : "Not checked.")}
      </p>
      <p>
        This checks SDE itself. It does not update your development tools or
        install anything automatically.
      </p>
      {(visible || (about && candidate)) && (
        <>
          <button className="secondary" onClick={() => void open()}>
            View release notes
          </button>{" "}
          <button className="secondary" onClick={() => void open(true)}>
            Download SDE installer
          </button>{" "}
          {visible && (
            <button className="text-button" onClick={data.dismiss}>
              Dismiss this version
            </button>
          )}
          <p className="muted">
            Download opens your browser. Follow the mentor verification
            procedure before installing; release discovery alone does not
            authenticate downloaded files.
          </p>
        </>
      )}
      {app?.failure && (
        <button className="secondary" onClick={() => void open()}>
          View official releases
        </button>
      )}
      {about && (
        <>
          <button
            className="secondary"
            disabled={data.appLoading || retryBlocked}
            onClick={() => void data.refreshApp()}
          >
            Check for SDE updates
          </button>
          {retryBlocked && (
            <p role="status">
              GitHub requested another check after{" "}
              {localTime(new Date(retryAt! * 1000).toISOString())}.
            </p>
          )}
          <p className="muted">
            Last successful SDE check:{" "}
            {data.lastSuccess
              ? localTime(new Date(data.lastSuccess * 1000).toISOString())
              : "None this session"}
          </p>
        </>
      )}
      {error && <p role="status">{error}</p>}
    </section>
  );
}
export function ToolUpdatePreview({
  data,
  snapshot,
  onContinue,
  onCancel,
  platformSupported,
}: {
  data: Discovery;
  snapshot: ToolRecord[];
  onContinue: () => void;
  onCancel: () => void;
  platformSupported: boolean;
}) {
  const [checks, setChecks] = useState<PreflightCheck[] | null>(null);
  const [preflightLoading, setPreflightLoading] = useState(false);
  const [error, setError] = useState("");
  const [ack, setAck] = useState(false);
  const live = useRef(true);
  const heading = useRef<HTMLHeadingElement>(null);
  async function preflight() {
    if (preflightLoading) return;
    setPreflightLoading(true);
    setChecks(null);
    setAck(false);
    setError("");
    try {
      const rows = await checkPreflight();
      if (live.current) setChecks(rows);
    } catch {
      if (live.current)
        setError(
          "Preflight could not be completed. Check again before continuing.",
        );
    } finally {
      if (live.current) setPreflightLoading(false);
    }
  }
  useEffect(() => {
    live.current = true;
    heading.current?.focus();
    void preflight();
    return () => {
      live.current = false;
    };
  }, []);
  const tools =
    data.preview?.tools ??
    (data.toolsError
      ? snapshot.map((t) => ({
          ...t,
          updateAvailable: false,
          availableVersion: null,
          updateCheck: "unavailable" as const,
        }))
      : snapshot);
  const caution = checks?.some(
    (c) => c.status === "warning" || c.status === "unavailable",
  );
  const blocked =
    !platformSupported || checks?.some((c) => c.status === "blocking");
  return (
    <section
      className="information-card update-preview"
      aria-labelledby="tool-preview-heading"
    >
      <h2 id="tool-preview-heading" tabIndex={-1} ref={heading}>
        Preview development-tool update
      </h2>
      <p>
        Update refreshes all Skyview-managed tools, your workspace/editor
        defaults and user extensions, then validates. Node stays on 24.x and
        Python on 3.14.x. Your projects and existing editor preferences are
        preserved. SDE application updates are separate.
      </p>
      <p role="status">
        {data.toolsLoading
          ? "Checking managed-tool sources…"
          : data.toolsError ||
            (!data.preview
              ? "Available versions have not been confirmed."
              : "Preview collected. Some tools may have incomplete checks; see each result.")}
      </p>
      <p className="muted">
        Collected:{" "}
        {data.preview
          ? localTime(new Date(data.preview.checkedAt * 1000).toISOString())
          : "Unavailable"}
        . Linux uses existing local APT metadata; this preview does not refresh
        it. Available versions may change before execution.
      </p>
      <div className="update-tool-list">
        {tools.map((t) => (
          <div className="update-tool-row" key={t.tool}>
            <strong>{t.tool}</strong>
            <span>
              {t.installedVersion ?? "Installed version unavailable"}
              {t.updateAvailable ? ` → ${t.availableVersion}` : ""}
            </span>
            <span>
              {toolExplanation(t)}
              {t.source ? ` Source: ${t.source}.` : ""}
            </span>
          </div>
        ))}
      </div>
      {!tools.length && (
        <p>
          Tool inventory is unavailable. Run validation to collect installed
          versions. Update still uses the complete managed scope.
        </p>
      )}
      <button
        className="secondary"
        disabled={data.toolsLoading}
        onClick={() => void data.refreshTools()}
      >
        Refresh preview
      </button>
      <h3>Before changes begin</h3>
      <p role="status">
        {preflightLoading
          ? "Checking update prerequisites…"
          : error ||
            (!checks
              ? "Preflight not completed."
              : blocked
                ? "Action needed. No changes have been started."
                : "Preflight complete. Review warnings and unavailable checks before continuing.")}
      </p>
      {checks?.map((c) => (
        <p key={c.name}>
          <strong>
            {c.name} — {c.status === "blocking" ? "Action needed" : c.status}
          </strong>
          : {c.detail}
        </p>
      ))}
      <button
        className="secondary"
        disabled={preflightLoading}
        onClick={() => void preflight()}
      >
        Check again
      </button>
      {caution && (
        <label className="preflight-ack">
          <input
            type="checkbox"
            checked={ack}
            onChange={(e) => setAck(e.target.checked)}
          />{" "}
          I have reviewed the warnings and unavailable checks. Downloads or
          installation may still fail.
        </label>
      )}
      <div className="result-actions">
        <button
          disabled={
            preflightLoading ||
            !checks ||
            !!blocked ||
            !!error ||
            (!!caution && !ack)
          }
          onClick={onContinue}
        >
          Continue with Update
        </button>
        <button className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
      <p className="muted">
        Continuing requests administrator approval. Preconditions are checked
        again before package changes; a successful preflight cannot guarantee
        success.
      </p>
    </section>
  );
}
