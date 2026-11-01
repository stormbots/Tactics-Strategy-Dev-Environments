import { invoke, isTauri } from "@tauri-apps/api/core";
import type { Check, Mode } from "./model";
import type { OperationStage } from "./safeOperations";

type Activity = "active" | "inactive" | "unknown";
type Restart = "confirmed" | "same_session" | "unavailable";
export type RecoveryState = {
  nativeSafety: {
    observedAt: number;
    trust: "trusted" | "untrusted" | "unknown";
    activity: Activity;
    packageHealth: "healthy" | "incomplete" | "unknown";
    activityReason: string;
    restart: Restart;
    interrupted: boolean;
    acknowledged: boolean;
    decision: string;
  };
  machine: {
    available: boolean;
    incidentId: string | null;
    intentSubmitted: boolean;
    acknowledgedAt: number | null;
  };
  user: {
    observedAt: number;
    available: boolean;
    incident: {
      id: string;
      operation: Exclude<Mode, "validate">;
      stage: OperationStage;
      startedAt: number;
      observedAt: number;
    } | null;
    acknowledgment: {
      incidentId: string;
      acknowledgedAt: number;
      reportId: string | null;
    } | null;
    restart: Restart;
    gate: Activity;
    viewToken: string | null;
  };
  effectiveActivity: Activity;
  decision: string;
  readiness: "blocked" | "needs_acknowledgment" | "ready_for_native_recheck";
  canAcknowledgeMachine: boolean;
  canAcknowledgeUser: boolean;
  guidance: { code: string; title: string; steps: string[] };
};
export type RecoveryValidation = {
  collectedAt: number | null;
  checks: Check[];
};
export type AcknowledgmentResult = {
  incidentId: string;
  reportId: string | null;
  reportWarning: string | null;
  intentStatus?: "submitted" | "unconfirmed";
  intentWarning?: string | null;
  acknowledgment?: RecoveryState["user"]["acknowledgment"];
  acknowledgmentWarning?: string | null;
};

// Preview is synthetic; it never reads or changes workstation state.
export function previewRecovery(): RecoveryState {
  return {
    nativeSafety: {
      observedAt: Math.floor(Date.now() / 1000),
      trust: "trusted",
      activity: "inactive",
      packageHealth: "unknown",
      activityReason: "no_package_activity",
      restart: "unavailable",
      interrupted: false,
      acknowledged: false,
      decision: "allow_with_health_warning",
    },
    machine: {
      available: true,
      incidentId: null,
      intentSubmitted: false,
      acknowledgedAt: null,
    },
    user: {
      observedAt: Math.floor(Date.now() / 1000),
      available: true,
      incident: null,
      acknowledgment: null,
      restart: "unavailable",
      gate: "unknown",
      viewToken: null,
    },
    effectiveActivity: "inactive",
    decision: "allow_with_health_warning",
    readiness: "ready_for_native_recheck",
    canAcknowledgeMachine: false,
    canAcknowledgeUser: false,
    guidance: {
      code: "health_unverified",
      title: "Package health remains unverified",
      steps: [
        "Preview only. Native safeguards and ordinary confirmations apply on the installed application.",
      ],
    },
  };
}
export async function inspectRecovery(): Promise<RecoveryState> {
  return isTauri() ? invoke("inspect_recovery_state") : previewRecovery();
}
export function recoveryNeedsAttention(state: RecoveryState | null): boolean {
  if (!state || state.readiness !== "ready_for_native_recheck") return true;
  return false;
}
export async function acknowledgeMachine(
  state: RecoveryState,
  validation: RecoveryValidation | null,
): Promise<AcknowledgmentResult> {
  if (!state.canAcknowledgeMachine || !state.machine.incidentId)
    throw new Error("Check Again before acknowledging the machine incident.");
  return invoke("acknowledge_recovery_incident", {
    incidentId: state.machine.incidentId,
    confirmed: true,
    validation,
  });
}
export async function acknowledgeUser(
  state: RecoveryState,
  validation: RecoveryValidation | null,
): Promise<AcknowledgmentResult> {
  if (
    !state.canAcknowledgeUser ||
    !state.user.incident ||
    !state.user.viewToken
  )
    throw new Error("Check Again before acknowledging the user incident.");
  return invoke("acknowledge_user_recovery_incident", {
    incidentId: state.user.incident.id,
    viewToken: state.user.viewToken,
    confirmed: true,
    validation,
  });
}
