import {
  checksFrom,
  collectionTime,
  parseEvent,
  reportPassed,
  toolsFrom,
  updateInspectionIncomplete,
  type Check,
  type Report,
  type Schedule,
  type ToolRecord,
} from "./model";
import type { RecoveryState } from "./recovery";
import { validationGuidance } from "./validationGuidance";

/** Request identity is presentation freshness, never native execution authority. */
export type Observation<T> = {
  epoch: number;
  request: number;
  value: T | null;
  pending: boolean;
};
export function beginObservation<T>(
  previous: Observation<T>,
  epoch: number,
): Observation<T> {
  return { epoch, request: previous.request + 1, value: null, pending: true };
}
export function settleObservation<T>(
  current: Observation<T>,
  ticket: Pick<Observation<T>, "epoch" | "request">,
  value: T | null,
): Observation<T> {
  return current.pending &&
    current.epoch === ticket.epoch &&
    current.request === ticket.request
    ? { ...current, value, pending: false }
    : current;
}

export type OverviewAction =
  | "check"
  | "recheck-safety"
  | "review-install"
  | "review-repair"
  | "review-updates"
  | "review-issue"
  | "review-interruption"
  | "open-editor"
  | "open-workspace";

/** Fixed destinations only; integration must use the existing reviewed dispatch. */
export const overviewActionTargets = {
  check: { kind: "operation", mode: "validate" },
  "recheck-safety": { kind: "inspection", command: "inspect_recovery_state" },
  "review-install": { kind: "review", mode: "install" },
  "review-repair": { kind: "review", mode: "repair" },
  "review-updates": { kind: "review", mode: "update" },
  "review-issue": { kind: "page", page: "validation" },
  "review-interruption": { kind: "page", page: "recovery" },
  "open-editor": { kind: "destination", destination: "editor" },
  "open-workspace": { kind: "destination", destination: "workspace" },
} as const satisfies Record<OverviewAction, object>;
export type OverviewState =
  | "checking"
  | "unchecked"
  | "check-incomplete"
  | "setup"
  | "repair"
  | "attention"
  | "ready"
  | "updates"
  | "active"
  | "unknown"
  | "untrusted"
  | "incident"
  | "native-incomplete"
  | "task";
export type OverviewInput = {
  epoch: number;
  validation: Observation<Report>;
  recovery: Observation<RecoveryState>;
  tools: Observation<ToolRecord[]>;
  maintenance: Observation<Schedule>;
  // Supplied only while an existing review/operation/result owns the task card.
  task: {
    phase: "review" | "running" | "verification" | "result";
    mode: "install" | "repair" | "validate" | "update";
  } | null;
};

/** Snapshot a reviewed scope. A changed query invalidates it, even if its
 * eventual findings look equal. This does not replace fresh native admission. */
export function overviewReviewBinding(input: OverviewInput): string {
  return JSON.stringify([
    input.epoch,
    ...[input.validation, input.recovery, input.tools].map((o) => [
      o.epoch,
      o.request,
      o.pending,
    ]),
  ]);
}
export type OverviewDecision = {
  state: OverviewState;
  headline: string;
  heading: string;
  body: string;
  primary: { id: OverviewAction; label: string } | null;
  secondary: OverviewAction[];
  reason: string;
  // These are disclosure data, not permission/consent or privileged receipts.
  details: {
    checks: Check[];
    safety: RecoveryState | null;
    maintenance: Schedule | null;
    updatesUnknown: boolean;
  };
};

/** Both Overview cards consume this decision. Dispatch retains all native gates. */
export function overviewDecision(input: OverviewInput): OverviewDecision {
  const current = <T>(o: Observation<T>) =>
    o.epoch === input.epoch && !o.pending ? o.value : null;
  const report = current(input.validation);
  const safety = current(input.recovery);
  const checks = report ? checksFrom(report.lines) : [];
  const tools = current(input.tools) ?? (report ? toolsFrom(report.lines) : []);
  const details = {
    checks,
    safety,
    maintenance: current(input.maintenance),
    updatesUnknown: updateInspectionIncomplete(checks, tools),
  };
  const safeReview = safety?.readiness === "ready_for_native_recheck";
  const secondary: OverviewAction[] = ["check", "review-issue"];
  if (!input.task && safeReview && report?.platform.supported)
    secondary.push("review-install", "review-repair", "review-updates");
  const choose = (
    state: OverviewState,
    headline: string,
    heading: string,
    body: string,
    id: OverviewAction | null,
    label = "",
    reason: string = state,
  ): OverviewDecision => ({
    state,
    headline,
    heading,
    body,
    primary: id ? { id, label } : null,
    secondary:
      input.task || state === "checking"
        ? []
        : secondary.filter((action) => action !== id),
    reason,
    details,
  });
  if (input.task)
    return choose(
      "task",
      "Your current task",
      "",
      "",
      null,
      "",
      `${input.task.mode}:${input.task.phase}`,
    );
  // Respect the native combined decision. Only known active work overrides its
  // explanation to prevent restart/repair guidance while a package process runs.
  if (safety?.effectiveActivity === "active")
    return choose(
      "active",
      "Changes are paused",
      "Let setup finish",
      "Wait for the current operation to finish, then check again. Don’t restart or force an installer to close.",
      "recheck-safety",
      "Check again",
    );
  if (!safety) {
    if (input.recovery.pending && input.recovery.epoch === input.epoch)
      return choose(
        "checking",
        "Checking your setup…",
        "Finding your next step",
        "Reading workstation safety observations. No changes are being made.",
        null,
      );
    return choose(
      "untrusted",
      "Safety check unavailable",
      "SDE couldn’t verify that changes are safe",
      "Check again or review diagnostic information. No change has been authorized.",
      "recheck-safety",
      "Check again",
      "safety-unavailable",
    );
  }
  if (!safeReview) {
    const decision = safety.decision;
    if (
      decision === "block_untrusted" ||
      !safety.machine.available ||
      !safety.user.available ||
      safety.nativeSafety.trust !== "trusted"
    )
      return choose(
        "untrusted",
        "Safety check unavailable",
        "SDE couldn’t verify that changes are safe",
        safety.guidance.steps.join(" "),
        "recheck-safety",
        "Check again",
        decision,
      );
    if (safety.effectiveActivity === "unknown")
      return choose(
        "unknown",
        "Changes are paused",
        "Check whether setup has finished",
        safety.guidance.steps.join(" "),
        "recheck-safety",
        "Check again",
        decision,
      );
    if (decision === "block_incomplete")
      return choose(
        "native-incomplete",
        "Changes are paused",
        "An installation needs attention",
        safety.guidance.steps.join(" "),
        "review-issue",
        "Review the issue",
        decision,
      );
    if (safety.readiness === "needs_acknowledgment")
      return choose(
        "incident",
        "Review an interruption",
        "Review what happened",
        safety.guidance.steps.join(" "),
        "review-interruption",
        "Review interruption",
        decision,
      );
    return choose(
      "attention",
      "Changes are paused",
      safety.guidance.title,
      safety.guidance.steps.join(" "),
      "review-issue",
      "Review the issue",
      decision,
    );
  }
  if (input.validation.pending && input.validation.epoch === input.epoch)
    return choose(
      "checking",
      "Checking your setup…",
      "Finding your next step",
      "Checking tools and configuration. No changes are being made.",
      null,
    );
  if (
    !report &&
    input.validation.epoch === input.epoch &&
    input.validation.request > 0
  )
    return choose(
      "check-incomplete",
      "Check not finished",
      "Try checking again",
      "The check could not be collected. No setup failure has been inferred.",
      "check",
      "Check again",
    );
  if (!report)
    return choose(
      "unchecked",
      "Not checked yet",
      "Let’s check your setup",
      "A complete check is needed before recommending a change.",
      "check",
      "Check my setup",
    );
  const events = report.lines.map(parseEvent).filter((e) => e !== null);
  const summary = events
    .filter(
      (e) =>
        e.kind === "validation" || e.kind === "summary" || e.kind === "error",
    )
    .at(-1);
  const failures = checks.filter((c) => c.status === "FAIL");
  // Timestamp alone covers partial output. Require the terminal validator marker
  // and matching failure count, not a fixed number of checks or a time threshold.
  const complete =
    checks.length > 0 &&
    collectionTime(report.validation_collected_at) !== null &&
    summary?.kind === "summary" &&
    Number(summary.key) === failures.length;
  if (!complete)
    return choose(
      "check-incomplete",
      "Check not finished",
      "Try checking again",
      "SDE couldn’t complete the check. Partial results remain available in Details; this does not mean your setup is broken.",
      "check",
      "Check again",
    );
  if (!report.platform.supported)
    return choose(
      "attention",
      "Setup needs attention",
      "Follow the recommended fix",
      "The supported workstation platform could not be confirmed. Review the diagnostic information before making changes.",
      "review-issue",
      "Review the issue",
      "unsupported-platform",
    );
  if (failures.length) {
    const guidance = failures.map((c) =>
      validationGuidance(c, undefined, report.platform.supported),
    );
    if (guidance.some((g) => g?.operation !== "repair"))
      return choose(
        "attention",
        "Setup needs attention",
        "Follow the recommended fix",
        "Review the identified findings and their supported guidance. A generic repair may not resolve them.",
        "review-issue",
        "Review the issue",
        "unsupported-finding",
      );
    const missing = failures.some((c) =>
      /(?:not installed|not found)$/.test(c.message),
    );
    if (missing)
      return choose(
        "setup",
        "Setup needed",
        "Set up this computer",
        "Required tools were not found. Review the full setup scope before making changes.",
        "review-install",
        "Review setup",
        "missing-tools-no-prior-setup-proof",
      );
    return choose(
      "repair",
      "Setup needs a fix",
      "Fix your setup",
      guidance[0]!.impact,
      "review-repair",
      "Review fixes",
      "supported-repair",
    );
  }
  if (!reportPassed(report))
    return choose(
      "check-incomplete",
      "Check not finished",
      "Try checking again",
      "The check did not finish successfully. Review Details before trying again.",
      "check",
      "Check again",
    );
  secondary.push("open-editor", "open-workspace");
  if (tools.some((t) => t.updateAvailable && t.updateCheck === "current"))
    return choose(
      "updates",
      "Ready!",
      "Install updates",
      "Your setup works, but there are updates available if you would like to install them.",
      "review-updates",
      "Review updates",
    );
  return choose(
    "ready",
    "Ready!",
    "Start building",
    "Your required tools and configuration passed the latest check.",
    "open-editor",
    "Open VSCodium",
  );
}
