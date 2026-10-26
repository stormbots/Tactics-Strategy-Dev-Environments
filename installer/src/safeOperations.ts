import type { Mode, Schedule } from "./model";

export type PreflightStatus = "pass" | "blocking" | "warning" | "unavailable";

export type PreflightCheck = {
  name: string;
  status: PreflightStatus;
  detail: string;
};

export type PreflightDecision = {
  blocked: boolean;
  needsAcknowledgement: boolean;
  canContinue: boolean;
  passed: number;
  warnings: number;
  unavailable: number;
  blockers: number;
};

/**
 * Unavailable evidence is uncertainty, never a pass. The approved product
 * policy permits one operation attempt after explicit acknowledgement, while a
 * positively detected blocker has no bypass.
 */
export function preflightDecision(
  checks: PreflightCheck[] | null,
  acknowledged = false,
): PreflightDecision {
  const rows = checks ?? [];
  const count = (status: PreflightStatus) =>
    rows.filter((check) => check.status === status).length;
  const blockers = count("blocking");
  const unavailable = checks === null ? 1 : count("unavailable");
  const warnings = count("warning");
  const needsAcknowledgement = warnings > 0 || unavailable > 0;
  return {
    blocked: blockers > 0,
    needsAcknowledgement,
    canContinue:
      blockers === 0 && (!needsAcknowledgement || acknowledged === true),
    passed: count("pass"),
    warnings,
    unavailable,
    blockers,
  };
}

export type OperationKind = Exclude<Mode, "validate">;
export type OperationStage =
  "starting" | "system" | "profile" | "validation" | "unknown";

export type OperationIncident = {
  schema: 1;
  id: string;
  operation: OperationKind;
  stage: OperationStage;
  startedAt: number;
  observedAt: number;
  logPath: string | null;
  acknowledged: boolean;
};

export type ValidationDisposition = "notRun" | "passed" | "repair" | "mentor";

export type RecoveryAction =
  "wait" | "validate" | "resolved" | "repair" | "mentor";

export function recoveryAction(
  incident: OperationIncident | null,
  backendActive: boolean,
  validation: ValidationDisposition,
): RecoveryAction {
  if (backendActive) return "wait";
  if (!incident || incident.acknowledged || validation === "passed")
    return "resolved";
  if (validation === "repair") return "repair";
  if (validation === "mentor") return "mentor";
  return "validate";
}

export type MaintenanceHealth =
  | "healthy"
  | "failed"
  | "missing"
  | "disabled"
  | "overdue"
  | "running"
  | "unavailable"
  | "grace";

export type MaintenanceObservation = Schedule & {
  observedAt: string;
  createdAt: string | null;
  lastSuccess: string | null;
};

const DAYS_14_MS = 14 * 24 * 60 * 60 * 1000;

function time(value: string | null): number | null {
  if (!value) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function maintenanceHealth(
  observation: MaintenanceObservation,
  now = Date.now(),
): MaintenanceHealth {
  if (observation.lastResult === "running") return "running";
  if (observation.status === "missing") return "missing";
  if (observation.status === "disabled" || !observation.active)
    return "disabled";
  if (observation.status === "unavailable") return "unavailable";
  if (observation.lastResult === "failure") return "failed";

  const success = time(observation.lastSuccess);
  if (success !== null)
    return now - success > DAYS_14_MS ? "overdue" : "healthy";

  const created = time(observation.createdAt);
  if (created !== null && now - created <= DAYS_14_MS) return "grace";
  return "unavailable";
}

export type OverviewTone = "green" | "yellow" | "red";

export function overviewTone(
  readinessFailed: boolean,
  readinessWarning: boolean,
  maintenance: MaintenanceHealth,
): OverviewTone {
  if (readinessFailed) return "red";
  if (readinessWarning || !["healthy", "grace"].includes(maintenance))
    return "yellow";
  return "green";
}

export type SupportReportSnapshot = {
  schema: 1;
  createdAt: string;
  deviceName: string;
  platform: string;
  applicationVersion: string;
  validation: {
    collectedAt: string | null;
    outcome: "ready" | "needsAttention" | "unavailable";
    checks: Array<{ status: string; message: string }>;
  };
  operation: {
    kind: OperationKind;
    stage: OperationStage;
    outcome: string;
    observedAt: string;
  } | null;
  maintenance: MaintenanceObservation | null;
  logs: {
    included: boolean;
    content: string | null;
    omission: string | null;
  };
};
