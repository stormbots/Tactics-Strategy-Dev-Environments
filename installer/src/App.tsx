import { useEffect, useReducer, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import {
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  Download,
  ExternalLink,
  FolderOpen,
  Info,
  Laptop,
  LayoutDashboard,
  LifeBuoy,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  Terminal,
  TriangleAlert,
  Wrench,
  XCircle,
} from "lucide-react";
import {
  initialState,
  reducer,
  toolForCheck,
  toolStatus,
  toolNames,
  parseEvent,
  updateInspectionIncomplete,
  type Check,
  type Mode,
  type State,
  type ToolRecord,
  type Report,
} from "./model";
import {
  appVersion,
  inspect,
  inspectSchedule,
  native,
  open,
  operate,
  type Destination,
} from "./bridge";
import { ValidationCheck } from "./ValidationCheck";
import { operationScope, validationGuidance } from "./validationGuidance";
import { AppearanceControls } from "./AppearanceControls";
import {
  ApplicationUpdates,
  ToolUpdatePreview,
  useUpdateDiscovery,
} from "./UpdateCenter";
import { AboutPage, localTime, SchedulePage } from "./DetailsPages";
import { PreflightReview } from "./PreflightReview";
import { SupportReportDialog } from "./SupportReportDialog";
import { RecoveryPage } from "./RecoveryPage";
import { RecoveryReportHistory } from "./RecoveryReportHistory";
import { RecoveryIncidentHistory } from "./RecoveryIncidentHistory";
import {
  acknowledgeMachine,
  acknowledgeUser,
  inspectRecovery,
  recoveryNeedsAttention,
  type RecoveryState,
  type AcknowledgmentResult,
} from "./recovery";
import {
  maintenanceHealth,
  type MaintenanceHealth,
  type MaintenanceObservation,
  type OperationIncident,
} from "./safeOperations";
import {
  overviewDecision,
  type OverviewAction,
  type OverviewInput,
  type OverviewDecision,
} from "./overviewDecision";
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
const checkPriority = { FAIL: 0, WARNING: 1, PASS: 2, INFO: 3 };

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
function ToolItem({ check, record }: { check: Check; record?: ToolRecord }) {
  const detail =
    !record || record.updateCheck === "unavailable"
      ? "Update check unavailable"
      : record.updateCheck === "notChecked"
        ? "Updates not checked"
        : record.updateCheck === "inconsistent"
          ? "Executable and package metadata disagree; review update details"
          : record.updateCheck === "native"
            ? "Updates managed by the tool or its runtime"
            : "";
  return (
    <div className={`tool ${check.status.toLowerCase()}`}>
      <StatusIcon status={check.status} />
      <span>{toolForCheck(check)}</span>
      <span className="tool-status">{toolStatus(check, record)}</span>
      {check.status === "PASS" && detail && (
        <span className="tool-status">{detail}</span>
      )}
    </div>
  );
}
function LogOutput({ s, openLogs }: { s: State; openLogs: () => void }) {
  const output = useRef<HTMLPreElement>(null);
  const following = useRef(true);
  useEffect(() => {
    if (output.current && following.current)
      output.current.scrollTop = output.current.scrollHeight;
  }, [s.logs]);
  return (
    <div className="log-output">
      <pre
        ref={output}
        role="region"
        aria-label="Provisioning log"
        tabIndex={0}
        onScroll={(e) => {
          const el = e.currentTarget;
          following.current =
            el.scrollHeight - el.scrollTop - el.clientHeight < 24;
        }}
      >
        {s.logs.join("\n") || "Waiting for setup output…"}
      </pre>
      <p className="muted">
        Latest 2,000 lines. Full logs are saved on this laptop.
      </p>
      {s.stage !== "running" && s.logPath && (
        <p className="log-path">{s.logPath}</p>
      )}
      <button
        className="secondary"
        disabled={!native || !s.logPath}
        onClick={openLogs}
      >
        <FolderOpen size={15} /> Open log folder
      </button>
    </div>
  );
}
export default function App() {
  const [s, dispatch] = useReducer(reducer, initialState);
  const [reviewRepair, setReviewRepair] = useState(false);
  const [focusedPrimary, setFocusedPrimary] =
    useState<OverviewDecision["primary"]>(null);
  const [observedReport, setObservedReport] = useState<Report | null>(null);
  const validationRequest = useRef(0);
  const recoveryRequest = useRef(0);
  const maintenanceRequest = useRef(0);
  const contextEpoch = useRef(0);
  const mounted = useRef(true);
  const [page, setPage] = useState<
    "overview" | "validation" | "recovery" | "schedule" | "about"
  >("overview");
  const [checkUpdates, setCheckUpdates] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [installPreflightOpen, setInstallPreflightOpen] = useState(false);
  const [generation, setGeneration] = useState(0);
  const [notice, setNotice] = useState("");
  const [maintenance, setMaintenance] = useState<MaintenanceObservation | null>(
    null,
  );
  const [maintenanceLoading, setMaintenanceLoading] = useState(true);
  const [recovery, setRecovery] = useState<RecoveryState | null>(null);
  const [recoveryLoading, setRecoveryLoading] = useState(false);
  const [recoveryError, setRecoveryError] = useState("");
  const [pendingOperation, setPendingOperation] = useState<Mode | null>(null);
  const [acknowledgmentOutcomes, setAcknowledgmentOutcomes] = useState<
    AcknowledgmentResult[]
  >([]);
  const actionInFlight = useRef(false);
  const incident: OperationIncident | null = recovery?.user.incident
    ? {
        ...recovery.user.incident,
        schema: 1,
        logPath: null,
        acknowledged: !!recovery.user.acknowledgment,
      }
    : null;
  const [reportOpen, setReportOpen] = useState(false);
  const runId = useRef("");
  const started = useRef(false);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const progressHeading = useRef<HTMLHeadingElement>(null);
  const pageHeading = useRef<HTMLHeadingElement>(null);
  const previousPage = useRef(page);
  const busy =
    s.stage === "running" || s.stage === "checking" || recoveryLoading;
  const passes = s.checks.filter((c) => c.status === "PASS").length;
  const fails = s.checks.filter((c) => c.status === "FAIL").length;
  const discovery = useUpdateDiscovery(
    s.tools,
    generation,
    !busy && s.stage !== "checking",
  );
  const displayTools =
    discovery.preview?.tools ??
    (discovery.toolsError
      ? s.tools.map((t) => ({
          ...t,
          updateAvailable: false,
          availableVersion: null,
          updateCheck: "unavailable" as const,
        }))
      : s.tools);
  const updateCount = displayTools.filter((t) => t.updateAvailable).length;
  const partialUpdateCheck = updateInspectionIncomplete(s.checks, displayTools);
  const maintenanceState: MaintenanceHealth = maintenance
    ? maintenanceHealth(maintenance)
    : "unavailable";
  const task =
    s.stage === "running"
      ? { phase: "running" as const, mode: s.mode }
      : installPreflightOpen
        ? { phase: "review" as const, mode: "install" as const }
        : previewOpen
          ? { phase: "review" as const, mode: "update" as const }
          : reviewRepair
            ? { phase: "review" as const, mode: "repair" as const }
            : null;
  const overviewInput: OverviewInput = {
    epoch: generation,
    validation: {
      epoch: generation,
      request: validationRequest.current,
      value: observedReport,
      pending: s.stage === "checking" || s.stage === "running",
    },
    recovery: {
      epoch: generation,
      request: recoveryRequest.current,
      value: recovery,
      pending: recoveryLoading,
    },
    tools: {
      epoch: generation,
      request: discovery.preview?.checkedAt ?? 0,
      value: displayTools,
      pending: discovery.toolsLoading,
    },
    maintenance: {
      epoch: generation,
      request: maintenanceRequest.current,
      value: maintenance,
      pending: maintenanceLoading,
    },
    task,
  };
  const decision = overviewDecision(overviewInput);
  const recommendation = overviewDecision({ ...overviewInput, task: null });
  const status = recommendation.headline;
  const displayedPrimary = focusedPrimary ?? decision.primary;
  const tone = ["ready", "updates"].includes(recommendation.state)
    ? "green"
    : ["checking", "unchecked", "check-incomplete", "untrusted"].includes(
          recommendation.state,
        )
      ? "neutral"
      : "yellow";
  async function refreshMaintenance() {
    const id = ++maintenanceRequest.current;
    setMaintenanceLoading(true);
    try {
      const value = (await inspectSchedule()) as MaintenanceObservation;
      if (mounted.current && id === maintenanceRequest.current)
        setMaintenance(value);
    } catch {
      if (mounted.current && id === maintenanceRequest.current)
        setMaintenance(null);
    } finally {
      if (mounted.current && id === maintenanceRequest.current)
        setMaintenanceLoading(false);
    }
  }
  useEffect(() => {
    if (previousPage.current !== page) {
      pageHeading.current?.focus();
      setFocusedPrimary(null);
    }
    previousPage.current = page;
  }, [page]);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const id = ++validationRequest.current;
    inspect()
      .then((report) => {
        if (!mounted.current || id !== validationRequest.current) return;
        setObservedReport(report);
        dispatch({ type: "initial", report });
      })
      .catch((e) => {
        if (!mounted.current || id !== validationRequest.current) return;
        setObservedReport(null);
        dispatch({ type: "error", message: String(e) });
      });
  }, []);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    void refreshMaintenance();
  }, []);
  async function refreshRecovery() {
    const id = ++recoveryRequest.current;
    const epoch = contextEpoch.current;
    setRecoveryLoading(true);
    setRecoveryError("");
    try {
      const observation = await inspectRecovery();
      if (
        !mounted.current ||
        id !== recoveryRequest.current ||
        epoch !== contextEpoch.current
      )
        return null;
      setRecovery(observation);
      return observation;
    } catch {
      if (
        !mounted.current ||
        id !== recoveryRequest.current ||
        epoch !== contextEpoch.current
      )
        return null;
      setRecovery(null);
      setRecoveryError(
        "Recovery information could not be read. Check Again; no change has been authorized.",
      );
      return null;
    } finally {
      if (
        mounted.current &&
        id === recoveryRequest.current &&
        epoch === contextEpoch.current
      )
        setRecoveryLoading(false);
    }
  }
  useEffect(() => {
    void refreshRecovery();
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
    if (s.stage === "running") progressHeading.current?.focus();
    if (s.stage === "success" || s.stage === "failure")
      resultHeading.current?.focus();
  }, [s.stage]);
  async function start(
    selected: Mode,
    confirmed = false,
    acknowledgedUncertainty = false,
  ) {
    if (busy || actionInFlight.current) return;
    actionInFlight.current = true;
    setFocusedPrimary(null);
    try {
      const fresh = await refreshRecovery();
      if (selected !== "validate" && recoveryNeedsAttention(fresh)) {
        setPendingOperation(selected);
        setPreviewOpen(false);
        setInstallPreflightOpen(false);
        setReviewRepair(false);
        setPage("recovery");
        setNotice("Review the Recovery findings before starting this change.");
        return;
      }
      if (fresh?.effectiveActivity === "active") {
        setPage("recovery");
        setNotice("Wait for the active operation to finish, then Check Again.");
        return;
      }
      if (selected === "install" && !confirmed) {
        setInstallPreflightOpen(true);
        setPage("overview");
        return;
      }
      if (selected === "update" && !confirmed) {
        setPreviewOpen(true);
        setPage("overview");
        return;
      }
      setPreviewOpen(false);
      setInstallPreflightOpen(false);
      setReviewRepair(false);
      setPendingOperation(null);
      contextEpoch.current++;
      const request = ++validationRequest.current;
      setObservedReport(null);
      setGeneration(contextEpoch.current);
      setNotice("");
      setPage("overview");
      runId.current = crypto.randomUUID();
      dispatch({ type: "start", mode: selected });
      try {
        const report = await operate(
          selected,
          runId.current,
          checkUpdates,
          acknowledgedUncertainty,
          (line) => dispatch({ type: "line", line }),
        );
        if (!mounted.current || request !== validationRequest.current) return;
        setObservedReport(report);
        dispatch({ type: "complete", report });
        if (
          selected === "validate" &&
          (fresh?.machine.incidentId || fresh?.user.incident)
        ) {
          setNotice(
            "Validation does not acknowledge the interruption, prove that operation completed, or authorize another change. Recovery evidence remains available.",
          );
        }
        const observation = await refreshRecovery();
        if (selected !== "validate" && recoveryNeedsAttention(observation))
          setPage("recovery");
        void refreshMaintenance();
      } catch (e) {
        if (!mounted.current || request !== validationRequest.current) return;
        setObservedReport(null);
        dispatch({ type: "error", message: String(e) });
      }
    } finally {
      actionInFlight.current = false;
    }
  }
  async function acknowledgeRecovery() {
    if (busy || actionInFlight.current || !recovery) return;
    actionInFlight.current = true;
    setRecoveryLoading(true);
    setRecoveryError("");
    let resume = false;
    try {
      const validation = s.checks.length
        ? { collectedAt: s.validationCollectedAt, checks: s.checks }
        : null;
      // Each source keeps its own incident-bound result. A partial failure never
      // acknowledges the other source or silently launches the pending request.
      const operations = [
        ...(recovery.canAcknowledgeMachine
          ? [() => acknowledgeMachine(recovery, validation)]
          : []),
        ...(recovery.canAcknowledgeUser
          ? [() => acknowledgeUser(recovery, validation)]
          : []),
      ];
      for (const operation of operations) {
        const result = await operation();
        setAcknowledgmentOutcomes((previous) => [...previous, result]);
        if (
          result.intentStatus === "unconfirmed" ||
          result.acknowledgmentWarning ||
          (result.intentStatus === undefined && !result.acknowledgment)
        ) {
          throw new Error(
            "Acknowledgment is unconfirmed. Check Again; the pending operation has not started.",
          );
        }
      }
      const fresh = await refreshRecovery();
      resume =
        !!operations.length &&
        !!fresh &&
        fresh.readiness === "ready_for_native_recheck";
    } catch (error) {
      setRecoveryError(String(error));
      // Invalid/stale tokens are not silently retried with a freshly bound view.
      setRecovery(null);
    } finally {
      actionInFlight.current = false;
      setRecoveryLoading(false);
    }
    if (resume && !pendingOperation) {
      // Startup acknowledgment is not a request to change the workstation.
      // Saved-summary references and failures remain visible on Overview.
      setPage("overview");
    } else if (resume && pendingOperation) {
      // Re-enter ordinary review, never reuse a pre-acknowledgment confirmation.
      if (pendingOperation === "repair") {
        setReviewRepair(true);
        setPage("overview");
        setPendingOperation(null);
      } else {
        await start(pendingOperation);
      }
    }
  }
  function reviewOperation(operation: "repair" | "update") {
    if (busy || actionInFlight.current) return;
    if (operation === "update") {
      void start("update");
      return;
    }
    if (recoveryNeedsAttention(recovery)) {
      setPage("recovery");
      setNotice("Review the Recovery findings before starting this change.");
      return;
    }
    setFocusedPrimary(null);
    setPreviewOpen(false);
    setInstallPreflightOpen(false);
    setReviewRepair(true);
    setPage("overview");
    setNotice("");
  }
  async function openTarget(target: Destination) {
    try {
      await open(target);
    } catch (e) {
      setNotice(String(e));
    }
  }
  useEffect(() => {
    if (reviewRepair) document.getElementById("next-step-heading")?.focus();
  }, [reviewRepair]);
  function cancelReview() {
    setFocusedPrimary(null);
    setInstallPreflightOpen(false);
    setPreviewOpen(false);
    setReviewRepair(false);
    setPendingOperation(null);
    requestAnimationFrame(() =>
      document.getElementById("next-step-heading")?.focus(),
    );
  }
  function overviewAction(action: OverviewAction) {
    if (action === "review-interruption") {
      setPage("recovery");
      return;
    }
    if (action === "review-issue") {
      setPage("validation");
      return;
    }
    if (action === "open-editor") {
      void openTarget("editor");
      return;
    }
    if (action === "open-workspace") {
      void openTarget("workspace");
      return;
    }
    if (busy || actionInFlight.current) return;
    if (action === "check") void start("validate");
    else if (action === "recheck-safety") void refreshRecovery();
    else if (action === "review-repair") reviewOperation("repair");
    else void start(action === "review-install" ? "install" : "update");
  }
  const actionLabels: Record<OverviewAction, string> = {
    check: "Check my setup",
    "recheck-safety": "Check again",
    "review-install": "Install development tools",
    "review-repair": "Repair setup",
    "review-updates": "Review tool updates",
    "review-issue": "View validation results",
    "review-interruption": "Review interruption",
    "open-editor": "Open VSCodium",
    "open-workspace": "Open Development",
  };
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <aside className="sidebar">
        <div className="brand-row">
          <div className="brand">
            <img src="/skyview-logo.png" alt="Skyview Robotics" />
            <div>
              SKYVIEW<span>ROBOTICS</span>
            </div>
          </div>
          <div id="compact-appearance-slot" />
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
          {
            <button
              aria-current={page === "recovery" ? "page" : undefined}
              onClick={() => setPage("recovery")}
            >
              <TriangleAlert size={18} />
              Recovery
            </button>
          }
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
          <button
            aria-current={page === "schedule" ? "page" : undefined}
            onClick={() => setPage("schedule")}
          >
            <CalendarClock size={18} />
            Schedule
          </button>
          <button
            aria-current={page === "about" ? "page" : undefined}
            onClick={() => setPage("about")}
          >
            <Info size={18} />
            About
          </button>
        </nav>
        <div className="sidebar-bottom">
          <ShieldCheck size={20} />
          <p>
            Bureau of
            <br />
            <strong>Tactics &amp; Strategy</strong>
          </p>
          <span>Skyview Dev Setup · {appVersion}</span>
        </div>
      </aside>
      <AppearanceControls page={page} />
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
            <h1 ref={pageHeading} tabIndex={-1}>
              {page === "overview"
                ? "Are you ready to build?"
                : page === "validation"
                  ? "Environment validation"
                  : page === "recovery"
                    ? "Recovery"
                    : page === "schedule"
                      ? "Maintenance schedule"
                      : "About Skyview Dev Setup"}
            </h1>
          </div>
          <div id="wide-appearance-slot" />
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
        {s.stage === "running" && page !== "overview" && (
          <p role="status">
            Setup in progress: {s.phase}{" "}
            <button onClick={() => setPage("overview")}>
              Return to current task
            </button>
          </p>
        )}
        {page !== "recovery" && acknowledgmentOutcomes.length > 0 && (
          <div className="notice" role="status">
            {acknowledgmentOutcomes.map((result, index) => (
              <p key={`${result.incidentId}-${index}`}>
                {result.reportId
                  ? `Recovery summary saved: ${result.reportId}.`
                  : "Recovery summary was not saved."}{" "}
                {result.reportWarning} {result.intentWarning}{" "}
                {result.acknowledgmentWarning}
              </p>
            ))}
            <button className="text-button" onClick={() => setPage("recovery")}>
              Review Recovery
            </button>
          </div>
        )}
        {s.stage === "checking" && page === "validation" && (
          <section
            className="checking-panel"
            aria-label="Workstation check"
            aria-busy="true"
          >
            <LoaderCircle className="spinner" size={34} aria-hidden="true" />
            <div>
              <h2>Checking your workstation…</h2>
              <p>
                Looking for installed tools and checking your configuration.
                Please wait.
              </p>
            </div>
          </section>
        )}
        {observedReport && !s.platform.supported && s.stage !== "checking" && (
          <div className="notice" role="status">
            This system is outside the supported platforms. You can still run
            validation.
          </div>
        )}
        {page === "overview" ? (
          <>
            <section
              className={`status-card guided-status tone-${tone}`}
              aria-label="Workstation status"
            >
              <div className="status-title">
                <div className="status-icon">
                  <Laptop size={22} aria-hidden="true" />
                </div>
                <div>
                  <p>DEVELOPMENT ENVIRONMENT</p>
                  <h2>
                    {s.stage === "running"
                      ? "Setup in progress"
                      : recommendation.headline}
                  </h2>
                </div>
              </div>
            </section>
            <ApplicationUpdates data={discovery} />
            <section
              className="operation-card guided-task"
              aria-labelledby="next-step-heading"
              aria-busy={busy}
            >
              <p className="eyebrow">Your next step</p>
              {s.stage === "running" ? (
                <div className="progress-panel">
                  <h2
                    id="next-step-heading"
                    ref={progressHeading}
                    tabIndex={-1}
                  >
                    <LoaderCircle
                      className="spinner"
                      size={20}
                      aria-hidden="true"
                    />
                    {s.mode === "validate" ? "Checking your setup…" : s.phase}
                  </h2>
                  <progress
                    value={s.progress || undefined}
                    max={100}
                    aria-label={s.phase}
                  />
                  <p>
                    Keep this window open. Detailed output is available below.
                  </p>
                </div>
              ) : installPreflightOpen ? (
                <>
                  <h2 id="next-step-heading">Review your setup</h2>
                  <p>
                    {modes.install.description} Normal setup can reapply the
                    full baseline, including configuration and the weekly
                    schedule.
                  </p>
                  <ul aria-label="Current setup findings">
                    {s.checks
                      .filter((check) => check.status === "FAIL")
                      .map((check, index) => (
                        <li key={index}>
                          {validationGuidance(
                            check,
                            undefined,
                            s.platform.supported,
                          )?.title ?? check.message}
                        </li>
                      ))}
                  </ul>
                  <PreflightReview
                    operation="install"
                    platformSupported={s.platform.supported}
                    onContinue={(acknowledged) =>
                      void start("install", true, acknowledged)
                    }
                    onCancel={cancelReview}
                  />
                </>
              ) : previewOpen ? (
                <ToolUpdatePreview
                  data={discovery}
                  snapshot={s.tools}
                  platformSupported={s.platform.supported}
                  onContinue={(acknowledged) =>
                    void start("update", true, acknowledged)
                  }
                  onCancel={cancelReview}
                />
              ) : reviewRepair ? (
                <>
                  <h2 id="next-step-heading" tabIndex={-1}>
                    Review your fixes
                  </h2>
                  <p>{operationScope.repair}</p>
                  <ul aria-label="Current repair findings">
                    {s.checks
                      .filter((check) => check.status === "FAIL")
                      .map((check, index) => (
                        <li key={index}>
                          {validationGuidance(
                            check,
                            undefined,
                            s.platform.supported,
                          )?.title ?? check.message}
                        </li>
                      ))}
                  </ul>
                  <p>{modes.repair.description}</p>
                  <button
                    className="primary"
                    disabled={busy}
                    onClick={() => void start("repair")}
                  >
                    Repair setup
                  </button>
                  <button className="secondary" onClick={cancelReview}>
                    Back
                  </button>
                  <p className="muted">
                    Your system will ask for administrator approval when needed.
                    Native safety checks still apply.
                  </p>
                </>
              ) : (
                <>
                  <h2 id="next-step-heading" tabIndex={-1} ref={resultHeading}>
                    {decision.heading}
                  </h2>
                  <p className="operation-description">{decision.body}</p>
                  {displayedPrimary && (
                    <button
                      className="primary"
                      disabled={busy}
                      onFocus={() => setFocusedPrimary(decision.primary)}
                      onBlur={() => setFocusedPrimary(null)}
                      onClick={() => {
                        if (
                          !decision.primary ||
                          displayedPrimary.id !== decision.primary.id
                        ) {
                          setNotice(
                            "The findings changed. Review your current next step before continuing.",
                          );
                          setFocusedPrimary(null);
                          document.getElementById("next-step-heading")?.focus();
                          return;
                        }
                        overviewAction(decision.primary.id);
                      }}
                    >
                      {displayedPrimary.label}
                      <ArrowRight size={18} aria-hidden="true" />
                    </button>
                  )}
                  {s.stage === "failure" && <p role="status">{s.error}</p>}
                </>
              )}
              <div className="guided-disclosures">
                <details>
                  <summary>Other actions</summary>
                  <div className="result-actions">
                    {decision.secondary
                      .filter(
                        (action) =>
                          action !== displayedPrimary?.id &&
                          action !== "review-issue",
                      )
                      .map((action) => (
                        <button
                          className="secondary"
                          key={action}
                          disabled={busy}
                          onClick={() => overviewAction(action)}
                        >
                          {actionLabels[action]}
                        </button>
                      ))}
                  </div>
                </details>
                <details>
                  <summary>Details</summary>
                  <p>
                    {passes} passed · {fails} need attention. Validation
                    collected{" "}
                    {s.validationCollectedAt
                      ? new Date(
                          s.validationCollectedAt * 1000,
                        ).toLocaleString()
                      : "time unavailable"}
                    .
                  </p>
                  <p>
                    {discovery.toolsLoading
                      ? "Checking managed-tool updates…"
                      : partialUpdateCheck && updateCount === 0
                        ? "Tool update availability is unknown."
                        : `${updateCount} confirmed managed-tool updates available.`}{" "}
                    {partialUpdateCheck && "Updates not fully checked."}
                  </p>
                  <ul aria-label="Latest check findings">
                    {s.checks
                      .filter((check) =>
                        ["FAIL", "WARNING"].includes(check.status),
                      )
                      .map((check, index) => (
                        <li key={index}>
                          {check.status}:{" "}
                          {validationGuidance(
                            check,
                            undefined,
                            s.platform.supported,
                          )?.title ?? check.message}
                        </li>
                      ))}
                  </ul>
                  {discovery.toolsError && (
                    <p role="status">{discovery.toolsError}</p>
                  )}
                  <p>
                    {maintenanceLoading
                      ? "Reading maintenance status…"
                      : maintenanceState === "failed"
                        ? "Maintenance failed"
                        : maintenanceState === "unavailable"
                          ? "Maintenance history unavailable"
                          : `Maintenance: ${maintenanceState}`}
                  </p>
                  {maintenance && (
                    <p>
                      {maintenance.resultDetail} Observed{" "}
                      {localTime(maintenance.observedAt)}
                    </p>
                  )}
                  {recovery && (
                    <p>
                      {recovery.readiness === "ready_for_native_recheck"
                        ? recovery.nativeSafety.packageHealth === "unknown"
                          ? "Package health remains unverified; native checks still apply."
                          : "No current safety blocker was found."
                        : `${recovery.guidance.title}. ${recovery.guidance.steps.join(" ")}`}
                    </p>
                  )}
                  {recoveryError && <p>{recoveryError}</p>}
                  <div className="result-actions">
                    <button onClick={() => setPage("validation")}>
                      View validation results
                    </button>
                    <button onClick={() => setPage("recovery")}>
                      Review Recovery
                    </button>
                    <button onClick={() => setPage("schedule")}>
                      View schedule
                    </button>
                    {maintenanceState === "failed" && (
                      <button onClick={() => void openTarget("maintenance")}>
                        Open maintenance logs
                      </button>
                    )}
                    <button disabled={busy} onClick={() => setReportOpen(true)}>
                      Create support report
                    </button>
                  </div>
                  {s.warnings.map((warning, i) => (
                    <p key={i} role="status">
                      {warning}
                    </p>
                  ))}
                  <LogOutput
                    key={runId.current}
                    s={s}
                    openLogs={() => void openTarget("logs")}
                  />
                </details>
              </div>
            </section>
            <details className="tools-preview">
              <summary>Development tools</summary>
              <div className="tool-grid">
                {s.checks
                  .filter((c) => toolForCheck(c))
                  .map((check, i) => (
                    <ToolItem
                      key={i}
                      check={check}
                      record={displayTools.find(
                        (t) => t.tool === toolForCheck(check),
                      )}
                    />
                  ))}
              </div>
              <button
                className="text-button"
                onClick={() => setPage("validation")}
              >
                See all checks
              </button>
            </details>
          </>
        ) : page === "recovery" ? (
          <>
            <RecoveryPage
              state={recovery}
              platformLabel={s.platform.label}
              loading={busy}
              error={recoveryError}
              pending={pendingOperation}
              outcomes={acknowledgmentOutcomes}
              onCheck={() => void refreshRecovery()}
              onAcknowledge={() => void acknowledgeRecovery()}
              onContinue={() => {
                if (pendingOperation) void start(pendingOperation);
              }}
              onCancel={() => {
                setPendingOperation(null);
                setPage("overview");
              }}
              onValidate={() => void start("validate")}
              onLogs={() => void openTarget("logs")}
              onSupport={() => setReportOpen(true)}
            />
            <details className="recovery-disclosure recovery-history">
              <summary>Earlier recovery events</summary>
              <RecoveryIncidentHistory disabled={busy} />
            </details>
            <details className="recovery-disclosure recovery-history">
              <summary>Saved reports</summary>
              <RecoveryReportHistory
                disabled={busy}
                recentReports={acknowledgmentOutcomes.flatMap((result) =>
                  result.reportId ? [result.reportId] : [],
                )}
              />
            </details>
          </>
        ) : page === "validation" ? (
          <section className="validation-card">
            <div className="section-header">
              <h2>Validation results</h2>
              <div className="result-actions">
                <button
                  className="secondary"
                  onClick={() => setReportOpen(true)}
                >
                  <LifeBuoy size={16} /> Create support report
                </button>
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() => start("validate")}
                >
                  <RefreshCw size={16} />
                  Check again
                </button>
              </div>
            </div>
            <p className="muted">
              Git identity and GitHub sign-in are optional. They do not cause
              validation to fail.
            </p>
            <p className="muted">
              Review buttons select an operation without starting it.{" "}
              {operationScope.repair} {operationScope.update}
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
                {[...s.checks]
                  .sort(
                    (a, b) => checkPriority[a.status] - checkPriority[b.status],
                  )
                  .map((c, i) => (
                    <tr key={`${c.status}:${c.message}:${i}`}>
                      <td>
                        <ValidationCheck
                          check={c}
                          record={displayTools.find(
                            (r) => r.tool === toolForCheck(c),
                          )}
                          supported={s.platform.supported}
                          busy={busy}
                          onReview={reviewOperation}
                          onSchedule={() => setPage("schedule")}
                        />
                      </td>
                      <td>
                        <span
                          className={`check-badge ${c.status.toLowerCase()}`}
                        >
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
        ) : page === "schedule" ? (
          <SchedulePage openTarget={openTarget} />
        ) : (
          <>
            <ApplicationUpdates data={discovery} about />
            <AboutPage platform={s.platform.label} openTarget={openTarget} />
          </>
        )}
        {page === "validation" && (
          <details className="details">
            <summary>
              <Terminal size={17} />
              Show details <ChevronDown size={15} />
            </summary>
            <LogOutput s={s} openLogs={() => openTarget("logs")} />
          </details>
        )}
        {page === "validation" && (
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
                Node.js 24.x · Python 3.14.x · No automatic Git identity or
                GitHub sign-in.
              </p>
            </div>
          </details>
        )}
        {reportOpen && (
          <SupportReportDialog
            checks={s.checks}
            validationComplete={s.validationComplete}
            validationCollectedAt={s.validationCollectedAt}
            platform={s.platform.label}
            incident={incident}
            maintenance={maintenance}
            onClose={() => setReportOpen(false)}
          />
        )}
        <footer>
          Skyview Robotics{" "}
          <span>Student Development Environment · {appVersion}</span>
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
