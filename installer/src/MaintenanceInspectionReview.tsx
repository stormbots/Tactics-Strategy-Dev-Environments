import type { Schedule } from "./model";

export function maintenanceFinding(data: Schedule | null, error = "") {
  if (!data && !error) return null;
  if (error)
    return {
      title: "We couldn’t finish checking weekly maintenance",
      detail:
        "SDE did not get a complete result from the system. This does not mean maintenance is missing or disabled.",
      next: "Check again. If the problem continues, ask your teacher for help and create a support report.",
    };
  const scope = data?.inspectionScope ?? "schedule";
  const reason =
    data?.inspectionReason ??
    (data?.status === "missing"
      ? "notInstalled"
      : data?.status === "unavailable"
        ? "unknown"
        : "verified");
  if (scope === "history")
    return {
      title: "We couldn’t check the maintenance history",
      detail: `The schedule was read, but its earlier results could not be checked. ${reason === "accessDenied" ? "SDE did not have permission to read them." : reason === "timedOut" ? "The history check took too long." : "The system did not provide a complete history result."}`,
      next: "Check again, or ask your teacher for help and create a support report. The schedule state shown above has not been changed.",
    };
  if (data?.status === "enabled" && reason === "verified") {
    if (data.active) return null;
    return {
      title: "Weekly maintenance is enabled but not waiting",
      detail:
        "The schedule is enabled, but the system does not report it as active. SDE cannot confirm the next automatic run.",
      next: "Check again. If it stays inactive, ask your teacher to review the schedule. This check does not start it.",
    };
  }
  if (data?.status === "disabled" && reason === "verified")
    return {
      title: "Weekly maintenance is disabled",
      detail:
        data.identifier === "skyview-student-dev-update.timer" && data.active
          ? "Future automatic maintenance is disabled, but the timer is still active in this session and may run. This check has not stopped it."
          : "Future automatic development-tool maintenance is disabled. This check has not enabled or started it.",
      next: "If you want to change the schedule, ask your teacher to review the setup with you. Checking again only reads its current state.",
    };
  if (data?.status === "missing" && reason === "notInstalled")
    return {
      title: "Weekly maintenance wasn’t found",
      detail:
        "SDE could not find its maintenance task or timer. Checking again will not install it.",
      next: "Ask your teacher to review the maintenance setup. You can check again or create a support report here.",
    };
  return {
    title: "We couldn’t check weekly maintenance",
    detail:
      reason === "accessDenied"
        ? "SDE did not have permission to read the maintenance schedule. The schedule has not been changed."
        : reason === "timedOut"
          ? "The maintenance check took too long and did not finish. This does not mean maintenance is missing or disabled."
          : "The system did not provide a complete schedule result. SDE cannot yet tell whether maintenance is enabled, disabled or missing.",
    next:
      reason === "accessDenied"
        ? "Keep using your normal account. Ask your teacher or administrator to check read access, then check again. Do not give everyone access or run SDE as an administrator to get around this problem."
        : "Check again. If the problem continues, ask your teacher for help and create a support report.",
  };
}

export function MaintenanceInspectionReview({
  data,
  error,
  busy,
  onCheck,
  onSupport,
}: {
  data: Schedule | null;
  error: string;
  busy: boolean;
  onCheck: () => void;
  onSupport: () => void;
}) {
  const finding = maintenanceFinding(data, error);
  if (!finding) return null;
  return (
    <section
      className="maintenance-scope"
      aria-label="Maintenance status review"
    >
      <h3>{finding.title}</h3>
      <p>{finding.detail}</p>
      <p>{finding.next}</p>
      <div className="result-actions">
        <button className="secondary" disabled={busy} onClick={onCheck}>
          Check maintenance status again
        </button>
        <button className="secondary" disabled={busy} onClick={onSupport}>
          Create maintenance support report
        </button>
      </div>
    </section>
  );
}
