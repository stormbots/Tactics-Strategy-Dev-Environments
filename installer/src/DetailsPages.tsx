import { useEffect, useRef, useState } from "react";
import {
  CalendarClock,
  ExternalLink,
  FolderOpen,
  LoaderCircle,
  RefreshCw,
} from "lucide-react";
import {
  appVersion,
  inspectSchedule,
  native,
  type Destination,
} from "./bridge";
import type { Schedule } from "./model";

export function localTime(
  value: string | null,
  fallback = "Unavailable",
): string {
  if (!value) return fallback;
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Unavailable"
    : date.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
}
const results: Record<Schedule["lastResult"], string> = {
  success: "Succeeded",
  failure: "Failed",
  never: "Never run",
  running: "Running",
  unavailable: "Unavailable",
};
const statuses: Record<Schedule["status"], string> = {
  enabled: "Enabled",
  disabled: "Disabled",
  missing: "Not installed",
  unavailable: "Unavailable",
};
export function SchedulePage({
  openTarget,
}: {
  openTarget: (target: Destination) => void;
}) {
  const [data, setData] = useState<Schedule | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshed, setRefreshed] = useState<string | null>(null);
  const request = useRef(0);
  async function refresh() {
    const id = ++request.current;
    setLoading(true);
    setError("");
    try {
      const result = await inspectSchedule();
      if (id === request.current) {
        setData(result);
        setRefreshed(new Date().toISOString());
      }
    } catch (e) {
      if (id === request.current) {
        setData(null);
        setError(String(e));
      }
    } finally {
      if (id === request.current) setLoading(false);
    }
  }
  useEffect(() => {
    void refresh();
    return () => {
      request.current++;
    };
  }, []);
  return (
    <section
      className="information-card"
      aria-labelledby="schedule-heading"
      aria-busy={loading}
    >
      <div className="section-header">
        <h2 id="schedule-heading">Scheduled maintenance</h2>
        <button
          className="secondary"
          disabled={loading}
          onClick={() => void refresh()}
        >
          <RefreshCw size={16} aria-hidden="true" />
          Refresh
        </button>
      </div>
      <p className="muted">
        Skyview installs weekly maintenance to keep your managed development
        tools current. This page reads the system schedule.
      </p>
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="schedule-status"
      >
        {loading ? (
          <>
            <LoaderCircle className="spinner" size={22} aria-hidden="true" />
            Reading maintenance schedule…
          </>
        ) : error ? (
          `Schedule unavailable. ${error}`
        ) : (
          data && (
            <>
              <CalendarClock size={22} aria-hidden="true" />
              {statuses[data.status]}
              {data.status === "enabled" && !data.active ? " · Inactive" : ""} ·
              Last result: {results[data.lastResult]}
            </>
          )
        )}
      </div>
      {!loading && data && (
        <>
          {data.note && <p className="notice">{data.note}</p>}
          <dl className="information-grid">
            <div>
              <dt>Task / timer</dt>
              <dd>{data.identifier}</dd>
            </div>
            <div>
              <dt>Frequency</dt>
              <dd>{data.frequency}</dd>
            </div>
            <div>
              <dt>Next run</dt>
              <dd>
                {localTime(
                  data.nextRun,
                  data.status === "disabled" || data.status === "missing"
                    ? "Not scheduled"
                    : "Unavailable",
                )}
              </dd>
            </div>
            <div>
              <dt>Last run</dt>
              <dd>
                {localTime(
                  data.lastRun,
                  data.lastResult === "never" ? "Never run" : "Unavailable",
                )}
              </dd>
            </div>
            <div>
              <dt>Last result</dt>
              <dd>
                {results[data.lastResult]}
                <span className="detail-note">{data.resultDetail}</span>
              </dd>
            </div>
            <div>
              <dt>Missed runs</dt>
              <dd>
                {data.catchUp === null
                  ? "Unavailable"
                  : data.catchUp
                    ? "Catch up when this machine becomes available"
                    : "No automatic catch-up"}
              </dd>
            </div>
          </dl>
          <p className="muted">
            Run times are shown in this machine’s local time. A next run is a
            scheduler estimate; power and network conditions can delay
            maintenance.
          </p>
          <div className="maintenance-scope">
            <h2>What gets updated</h2>
            <p>
              Skyview-managed packages and PyCharm receive updates. Node.js
              stays on 24.x and Python stays on 3.14.x. On Windows, Chrome uses
              Google Update; on Linux, Chrome is included in managed package
              updates.
            </p>
            <p>
              Maintenance does not update this setup app or configure your Git
              identity. User editor extensions are refreshed when you run
              Install, Repair, or Update in this app.
            </p>
          </div>
          <div className="maintenance-logs">
            <h2>Maintenance logs</h2>
            <p className="log-path">{data.logFolder}</p>
            <button
              className="secondary"
              disabled={!native || !data.logsAvailable}
              onClick={() => openTarget("maintenance")}
            >
              <FolderOpen size={16} aria-hidden="true" />
              Open maintenance log folder
            </button>
            {!data.logsAvailable && (
              <p className="muted">
                The folder becomes available after maintenance first writes a
                log.
              </p>
            )}
          </div>
          <p className="muted">Last refreshed: {localTime(refreshed)}</p>
        </>
      )}
    </section>
  );
}
export function AboutPage({
  platform,
  openTarget,
}: {
  platform: string;
  openTarget: (target: Destination) => void;
}) {
  function linkClick(
    e: React.MouseEvent<HTMLAnchorElement>,
    destination: Destination,
  ) {
    if (native) {
      e.preventDefault();
      openTarget(destination);
    }
  }
  return (
    <div className="about-page">
      <section
        className="information-card"
        aria-labelledby="about-tool-heading"
      >
        <h2 id="about-tool-heading">Skyview Dev Setup</h2>
        <p>
          Set up and maintain the student development environment for Skyview
          Robotics’ Bureau of Tactics &amp; Strategy. Install, repair, validate,
          and update your development tools, editor configuration, and workspace
          on Windows 11 or Linux Mint Cinnamon 22.x.
        </p>
        <dl className="information-grid">
          <div>
            <dt>App version</dt>
            <dd>{appVersion}</dd>
          </div>
          <div>
            <dt>Platform</dt>
            <dd>{platform}</dd>
          </div>
          <div>
            <dt>Maintained for</dt>
            <dd>Bureau of Tactics &amp; Strategy</dd>
          </div>
        </dl>
        <a
          className="external-link"
          href="https://github.com/stormbots/Tactics-Strategy-Dev-Environments"
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => linkClick(e, "repository")}
        >
          View the project on GitHub{" "}
          <ExternalLink size={16} aria-hidden="true" />
          <span className="sr-only"> (opens in your browser)</span>
        </a>
      </section>
      <section
        className="information-card"
        aria-labelledby="about-skyview-heading"
      >
        <h2 id="about-skyview-heading">Skyview Robotics</h2>
        <p>
          Skyview Robotics is a student STEM program in southwest Washington.
          Through robotics and community outreach, students develop technical
          skills, teamwork, and leadership while sharing STEM learning with
          others.
        </p>
        <a
          className="external-link"
          href="https://skyviewrobotics.com"
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => linkClick(e, "skyview")}
        >
          Visit Skyview Robotics <ExternalLink size={16} aria-hidden="true" />
          <span className="sr-only"> (opens in your browser)</span>
        </a>
      </section>
    </div>
  );
}
