import {
  checksFrom,
  collectionTime,
  reportPassed,
  type Check,
  type Report,
  type ToolRecord,
} from "./model";
import type { RecoveryState } from "./recovery";
import type { OperationKind } from "./safeOperations";

export type OperationOutcome = {
  mode: OperationKind;
  report: Report | null;
  error: string;
  before: Check[];
};
export type OperationResult = {
  kind: "not-started" | "uncertain" | "verification-incomplete" | "unresolved";
  heading: string;
  body: string;
  error: string;
  next: "dismiss" | "check" | "review-issue";
  label: string;
};

/** Native evidence alone proves non-start/completion. Text, exit codes and UI
 * history never do. A result is presentation, not a recovery disposition. */
export function operationResult(
  outcome: OperationOutcome | null,
): OperationResult | null {
  if (!outcome) return null;
  const { mode, report, error, before } = outcome;
  const name =
    mode === "install" ? "Setup" : mode === "repair" ? "Repair" : "Tool update";
  if (report?.mutation_outcome === "not_started")
    return {
      kind: "not-started",
      heading: "No changes were started",
      body: "SDE confirmed that no change started. Return to Overview when you are ready; approval will not be requested again automatically.",
      error,
      next: "dismiss",
      label: "Back to Overview",
    };
  const failures = report
    ? checksFrom(report.lines).filter((c) => c.status === "FAIL")
    : [];
  const unresolved =
    mode === "repair" &&
    failures.some((c) =>
      before.some((b) => b.status === "FAIL" && b.message === c.message),
    );
  if (report?.mutation_outcome !== "completed")
    return {
      kind: "uncertain",
      heading: unresolved
        ? "The repair has not confirmed a resolution"
        : `${name} outcome is unconfirmed`,
      body: `${unresolved ? "A reported finding still needs attention. " : ""}${mode === "update" ? "Some tools may already have changed. " : "Some changes may have been applied. "}Keep the diagnostic and recovery evidence. This is not a confirmed cancellation or rollback. Check current findings before deciding on another change.`,
      error,
      next: "check",
      label: "Check my setup",
    };
  if (
    !reportPassed(report) ||
    collectionTime(report.validation_collected_at) === null
  )
    return {
      kind: failures.length ? "unresolved" : "verification-incomplete",
      heading: failures.length
        ? `${name} finished; checks still need attention`
        : `${name} finished, but checking did not finish`,
      body: failures.length
        ? "Review the reported findings and supported guidance. Another repair or update will not start automatically."
        : "The operation finished, but SDE could not finish checking the result. Check your setup before considering another installation.",
      error,
      next: failures.length ? "review-issue" : "check",
      label: failures.length ? "Review the issue" : "Check my setup",
    };
  return null; // Recompute from current observations, including remaining updates.
}

export type ReviewContext = {
  validationRequest: number;
  checkUpdates: boolean;
  platformSupported: boolean;
  tools: ToolRecord[];
  recovery: RecoveryState | null;
};

/** Compare material reviewed scope/evidence, not observation timestamps. Fresh
 * equivalent native inspection does not invalidate a review; changed sources,
 * incidents, versions or options do. Never used as an execution capability. */
export function reviewFingerprint(
  mode: OperationKind,
  context: ReviewContext,
): string {
  const r = context.recovery;
  return JSON.stringify([
    mode,
    context.validationRequest,
    context.checkUpdates,
    context.platformSupported,
    context.tools
      .map((t) => [
        t.tool,
        t.installedVersion,
        t.availableVersion,
        t.updateAvailable,
        t.updateCheck,
        t.source ?? null,
      ])
      .sort((a, b) => String(a[0]).localeCompare(String(b[0]))),
    r
      ? [
          r.readiness,
          r.decision,
          r.effectiveActivity,
          r.nativeSafety.trust,
          r.nativeSafety.packageHealth,
          r.machine.available,
          r.machine.incidentId,
          r.machine.intentSubmitted,
          r.machine.acknowledgedAt,
          r.user.available,
          r.user.incident?.id,
          r.user.viewToken,
          r.user.acknowledgment?.incidentId,
          r.user.acknowledgment?.acknowledgedAt,
        ]
      : null,
  ]);
}

export function checkingResult(mode: string, phase: string): boolean {
  return (
    mode === "validate" || phase === "Validating your development environment"
  );
}
