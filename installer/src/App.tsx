import { useEffect, useReducer, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  Download,
  ExternalLink,
  FolderOpen,
  Info,
  Laptop,
  LayoutDashboard,
  RefreshCw,
  ShieldCheck,
  Terminal,
  TriangleAlert,
  Wrench,
  XCircle,
} from "lucide-react";
import {
  checksFrom,
  environmentStatus,
  initialState,
  reducer,
  type Check,
  type Mode,
} from "./model";
import { inspect, native, open, operate } from "./bridge";
const modes: Record<
  Mode,
  { name: string; button: string; description: string; icon: typeof Download }
> = {
  install: {
    name: "Install",
    button: "Install Development Environment",
    description:
      "Set up your development tools, editor, workspace, and weekly maintenance.",
    icon: Download,
  },
  repair: {
    name: "Repair",
    button: "Repair Development Environment",
    description:
      "Restore missing tools and standard configuration. Your projects and existing editor settings are preserved.",
    icon: Wrench,
  },
  validate: {
    name: "Validate",
    button: "Validate Development Environment",
    description:
      "Check your tools and configuration. Nothing will be installed or updated.",
    icon: ClipboardCheck,
  },
  update: {
    name: "Update",
    button: "Update Development Tools",
    description:
      "Update Skyview-managed tools, keeping Node on 24.x and Python on 3.14.x.",
    icon: RefreshCw,
  },
};
function StatusIcon({ status }: { status: Check["status"] }) {
  const Icon =
    status === "PASS"
      ? CheckCircle2
      : status === "FAIL"
        ? XCircle
        : status === "WARNING"
          ? TriangleAlert
          : Info;
  return <Icon size={17} aria-hidden="true" />;
}
export default function App() {
  const [s, dispatch] = useReducer(reducer, initialState);
  const [mode, setMode] = useState<Mode>("install");
  const [page, setPage] = useState<"overview" | "validation">("overview");
  const [checkUpdates, setCheckUpdates] = useState(false);
  const [notice, setNotice] = useState("");
  const runId = useRef("");
  const started = useRef(false);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const busy = s.stage === "running" || s.stage === "checking";
  const status = environmentStatus(s.checks, s.updates);
  const passes = s.checks.filter((c) => c.status === "PASS").length;
  const fails = s.checks.filter((c) => c.status === "FAIL").length;
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    inspect()
      .then((report) => dispatch({ type: "initial", report }))
      .catch((e) => dispatch({ type: "error", message: String(e) }));
  }, []);
  useEffect(() => {
    if (!native) return;
    let disposed = false;
    const cleanups: Array<() => void> = [];
    const add = (f: () => void) => (disposed ? f() : cleanups.push(f));
    listen<{ runId: string; line: string }>("skyview-line", ({ payload }) => {
      if (payload.runId === runId.current)
        dispatch({ type: "line", line: payload.line });
    }).then(add);
    listen("skyview-close-blocked", () =>
      setNotice(
        "Setup is still running. Keep this window open until it finishes.",
      ),
    ).then(add);
    return () => {
      disposed = true;
      cleanups.forEach((f) => f());
    };
  }, []);
  useEffect(() => {
    if (s.stage === "success" || s.stage === "failure")
      resultHeading.current?.focus();
  }, [s.stage]);
  async function start(selected: Mode) {
    if (busy) return;
    setNotice("");
    setPage("overview");
    runId.current = crypto.randomUUID();
    dispatch({ type: "start", mode: selected });
    try {
      const report = await operate(
        selected,
        runId.current,
        checkUpdates,
        (line) => dispatch({ type: "line", line }),
      );
      dispatch({ type: "complete", report });
    } catch (e) {
      dispatch({ type: "error", message: String(e) });
    }
  }
  async function openTarget(target: "editor" | "workspace" | "logs") {
    try {
      await open(target);
    } catch (e) {
      setNotice(String(e));
    }
  }
  const current = modes[mode];
  const CurrentIcon = current.icon;
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <aside className="sidebar">
        <div className="brand">
          <img src="/skyview-logo.png" alt="Skyview Robotics" />
          <div>
            SKYVIEW<span>ROBOTICS</span>
          </div>
        </div>
        <div className="sidebar-product">
          Student Development
          <br />
          Environment
        </div>
        <nav aria-label="Application">
          <button
            aria-current={page === "overview" ? "page" : undefined}
            onClick={() => setPage("overview")}
          >
            <LayoutDashboard size={18} />
            Overview
          </button>
          <button
            aria-current={page === "validation" ? "page" : undefined}
            onClick={() => setPage("validation")}
          >
            <ClipboardCheck size={18} />
            Validation
            {fails > 0 && (
              <span className="nav-count" aria-label={`${fails} failed checks`}>
                {fails}
              </span>
            )}
          </button>
        </nav>
        <div className="sidebar-bottom">
          <ShieldCheck size={20} />
          <p>
            Bureau of
            <br />
            <strong>Tactics &amp; Strategy</strong>
          </p>
          <span>Skyview Dev Setup Â· 1.1.1</span>
        </div>
      </aside>
      <main id="main" tabIndex={-1}>
        {!native && (
          <div className="preview-banner">
            <Info size={16} />
            Interactive design preview. All machine status and operations are
            simulated.
          </div>
        )}
        <header className="page-heading">
          <div>
            <p className="eyebrow">YOUR DEVELOPMENT WORKSTATION</p>
            <h1>
              {page === "overview"
                ? "Ready to build."
                : "Environment validation"}
            </h1>
          </div>
          <span className="system">
            <Laptop size={16} />
            {s.platform.label}
          </span>
        </header>
        {notice && (
          <div className="notice" role="status">
            {notice}
          </div>
        )}
        {!s.platform.supported && s.stage !== "checking" && (
          <div className="notice" role="status">
            This system is outside the supported platforms. You can still run
            validation.
          </div>
        )}
        {page === "overview" ? (
          <>
            <section className="hero" aria-labelledby="hero-heading">
              <div>
                <span className="hero-label">SKYVIEW ROBOTICS</span>
                <h2 id="hero-heading">
                  Your tools.
                  <br />
                  One place.
                </h2>
                <p>
                  Everything you need for student web and
                  <br className="desktop-break" /> application development, set
                  up together.
                </p>
                <span className="hero-footer">
                  <ShieldCheck size={16} />
                  Built for the Bureau of Tactics &amp; Strategy
                </span>
              </div>
              <div className="hero-logo">
                <img src="/skyview-logo.png" alt="" />
              </div>
            </section>
            <section className="status-card" aria-label="Workstation status">
              <div className="status-title">
                <div className="status-icon">
                  <Laptop size={22} />
                </div>
                <div>
                  <p>DEVELOPMENT ENVIRONMENT</p>
                  <h2>
                    {s.stage === "checking"
                      ? "Checking this workstationâ€¦"
                      : busy
                        ? "Setup in progress"
                        : status}
                  </h2>
                </div>
              </div>
              <div className="status-counts">
                <span>
                  <CheckCircle2 size={17} />
                  <strong>{passes}</strong> passed
                </span>
                <span>
                  <TriangleAlert size={17} />
                  <strong>{fails}</strong> need attention
                </span>
              </div>
            </section>
            {(s.stage === "success" || s.stage === "failure") && (
              <section
                className={`result ${s.stage}`}
                aria-labelledby="result-heading"
              >
                <div className="result-icon">
                  {s.stage === "success" ? <CheckCircle2 /> : <TriangleAlert />}
                </div>
                <div>
                  <h2 id="result-heading" ref={resultHeading} tabIndex={-1}>
                    {s.stage === "success"
                      ? s.mode === "validate"
                        ? "Validation passed."
                        : "Development environment ready."
                      : "Your environment needs attention."}
                  </h2>
                  <p>
                    {s.stage === "success"
                      ? "Your required tools and configuration passed validation."
                      : s.error}
                  </p>
                  <div className="result-actions">
                    {s.stage === "success" && (
                      <>
                        <button onClick={() => openTarget("editor")}>
                          Open VSCodium <ExternalLink size={14} />
                        </button>
                        <button onClick={() => openTarget("workspace")}>
                          Open Development <FolderOpen size={14} />
                        </button>
                      </>
                    )}
                    <button onClick={() => setPage("validation")}>
                      View validation results <ArrowRight size={14} />
                    </button>
                    {s.stage === "failure" && (
                      <button onClick={() => start(s.mode)}>
                        Retry {modes[s.mode].name.toLowerCase()}{" "}
                        <RefreshCw size={14} />
                      </button>
                    )}
                  </div>
                </div>
              </section>
            )}
            <section
              className="operation-card"
              aria-labelledby="operation-heading"
            >
              <div className="section-header">
                <h2 id="operation-heading">Manage your environment</h2>
                <span>Four simple ways to stay ready</span>
              </div>
              <div
                className="mode-tabs"
                role="group"
                aria-label="Choose an operation"
              >
                {(Object.keys(modes) as Mode[]).map((m) => {
                  const Icon = modes[m].icon;
                  return (
                    <button
                      key={m}
                      aria-pressed={mode === m}
                      disabled={busy}
                      onClick={() => setMode(m)}
                    >
                      <Icon size={17} />
                      {modes[m].name}
                    </button>
                  );
                })}
              </div>
              <p className="operation-description">{current.description}</p>
              {s.stage === "running" ? (
                <div className="progress-panel">
                  <div className="progress-heading" role="status">
                    <span>{s.phase}</span>
                    <strong>{s.progress}%</strong>
                  </div>
                  <progress value={s.progress} max={100} aria-label={s.phase} />
                  <p>
                    Keep this window open. Setup can take 10â€“20 minutes on a
                    fresh laptop.
                  </p>
                </div>
              ) : (
                <>
                  <button
                    className="primary"
                    disabled={
                      busy || (!s.platform.supported && mode !== "validate")
                    }
                    onClick={() => start(mode)}
                  >
                    <CurrentIcon size={19} />
                    {current.button}
                    <ArrowRight size={18} />
                  </button>
                  <p className="operation-note">
                    <ShieldCheck size={14} />
                    {mode === "validate"
                      ? "Validation runs without administrator privileges."
                      : "Your system will ask for administrator approval when needed."}
                  </p>
                </>
              )}
            </section>
            {s.warnings.length > 0 && (
              <div className="notice" role="status">
                <TriangleAlert size={18} />
                <div>
                  {s.warnings.map((w, i) => (
                    <p key={i}>{w}</p>
                  ))}
                </div>
              </div>
            )}
            <section className="tools-preview" aria-labelledby="tools-heading">
              <div className="section-header">
                <h2 id="tools-heading">Development tools</h2>
                <button
                  className="text-button"
                  onClick={() => setPage("validation")}
                >
                  See all checks <ArrowRight size={14} />
                </button>
              </div>
              <div className="tool-grid">
                {s.checks
                  .filter((c) =>
                    /^(Git:|GitHub CLI:|Node.js:|Python|VSCodium:|DBeaver:|PyCharm:|Chrome:|Firefox:|Git$|GitHub CLI$|Node.js$|VSCodium$|DBeaver$|PyCharm$|Firefox$|Google Chrome)/.test(
                      c.message,
                    ),
                  )
                  .slice(0, 9)
                  .map((c, i) => (
                    <div className={`tool ${c.status.toLowerCase()}`} key={i}>
                      <StatusIcon status={c.status} />
                      <span>{c.message.split(":")[0]}</span>
                      <span className="tool-status">
                        {c.status === "PASS"
                          ? "Ready"
                          : "Missing / needs repair"}
                      </span>
                    </div>
                  ))}
                {!s.checks.length && (
                  <p>Tool status appears after the workstation check.</p>
                )}
              </div>
            </section>
          </>
        ) : (
          <section className="validation-card">
            <div className="section-header">
              <h2>Validation results</h2>
              <button
                className="secondary"
                disabled={busy}
                onClick={() => start("validate")}
              >
                <RefreshCw size={16} />
                Check again
              </button>
            </div>
            <p className="muted">
              Git identity and GitHub sign-in are optional. They do not cause
              validation to fail.
            </p>
            <table>
              <caption className="sr-only">
                Development environment checks and results
              </caption>
              <thead>
                <tr>
                  <th scope="col">Component / check</th>
                  <th scope="col">Result</th>
                </tr>
              </thead>
              <tbody>
                {s.checks.map((c, i) => (
                  <tr key={i}>
                    <td>{c.message}</td>
                    <td>
                      <span className={`check-badge ${c.status.toLowerCase()}`}>
                        <StatusIcon status={c.status} />
                        {c.status === "INFO" ? "INFORMATION" : c.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!s.checks.length && <p>Run validation to see your results.</p>}
          </section>
        )}
        <details className="details">
          <summary>
            <Terminal size={17} />
            Show details <ChevronDown size={15} />
          </summary>
          <div>
            <p className="muted">
              Full logs are saved on this laptop. This view shows the latest
              2,000 lines.
            </p>
            {s.logPath && <p className="log-path">{s.logPath}</p>}
            <button
              className="secondary"
              disabled={!native || !s.logPath}
              onClick={() => openTarget("logs")}
            >
              <FolderOpen size={15} />
              Open log folder
            </button>
            <pre aria-label="Provisioning log" tabIndex={0}>
              {s.logs.join("\n") || "No log output yet."}
            </pre>
          </div>
        </details>
        <details className="details advanced">
          <summary>
            <Wrench size={17} />
            Advanced <ChevronDown size={15} />
          </summary>
          <div>
            <label className="checkbox">
              <input
                type="checkbox"
                disabled={busy}
                checked={checkUpdates}
                onChange={(e) => setCheckUpdates(e.target.checked)}
              />
              Check for managed package updates during validation
            </label>
            <p className="muted">
              Uses available package metadata; may take longer and require
              internet access. Linux metadata freshness depends on the most
              recent APT refresh.
            </p>
            <p>
              Optional repositories are read from the installed{" "}
              <code>repositories.csv</code>. Existing folders are preserved.
            </p>
            <p>
              Node.js 24.x Â· Python 3.14.x Â· No automatic Git identity or GitHub
              sign-in.
            </p>
          </div>
        </details>
        <footer>
          Skyview Robotics <span>Student Development Environment Â· 1.1.1</span>
        </footer>
        <div className="sr-only" aria-live="polite" aria-atomic="true">
          {s.stage === "checking"
            ? "Checking your workstation"
            : s.stage === "running"
              ? s.phase
              : s.stage === "success"
                ? "Operation complete. Validation passed."
                : s.stage === "failure"
                  ? `Operation needs attention. ${s.error}`
                  : status}
        </div>
      </main>
    </div>
  );
}
