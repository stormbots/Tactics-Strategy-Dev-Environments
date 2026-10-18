/** Read-only eligibility is not installation authorization. Backend request
 * checks must remain independent when native integration is enabled later. */
export type AppUpdateAvailability = {
  enabled: boolean;
  reason: "native_validation_pending" | "preview" | "unavailable";
};
export const unavailableAppUpdate: AppUpdateAvailability = {
  enabled: false,
  reason: "unavailable",
};
export function parseAppUpdate(value: unknown): AppUpdateAvailability {
  // No native implementation is approved to advertise eligibility yet. Unknown,
  // malformed or future replies fail closed until that contract is reviewed.
  if (
    typeof value === "object" &&
    value !== null &&
    "enabled" in value &&
    value.enabled === false &&
    "reason" in value &&
    value.reason === "native_validation_pending"
  )
    return { enabled: false, reason: "native_validation_pending" };
  return { ...unavailableAppUpdate };
}

export type VerifiedRelease = { version: string; tag: string; sha256: string };
export type ReleaseCheck =
  | { status: "available"; candidate: VerifiedRelease }
  | { status: "no_newer_listing"; candidate: null };
const version = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
const digest = /^[0-9a-f]{64}$/;
export const requestIdPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
function object(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function exact(value: Record<string, unknown>, keys: string[]) {
  return (
    Object.keys(value).length === keys.length &&
    keys.every((k) => Object.hasOwn(value, k))
  );
}
function validVersion(value: unknown): value is string {
  return typeof value === "string" && value.length <= 64 && version.test(value);
}
export function parseReleaseCheck(value: unknown): ReleaseCheck {
  if (!object(value) || !exact(value, ["status", "candidate"]))
    throw new Error("Unverified release observation");
  if (value.status === "no_newer_listing" && value.candidate === null)
    return { status: "no_newer_listing", candidate: null };
  const c = value.candidate;
  if (
    value.status !== "available" ||
    !object(c) ||
    !exact(c, ["version", "tag", "sha256"]) ||
    !validVersion(c.version) ||
    c.tag !== `v${c.version}` ||
    typeof c.sha256 !== "string" ||
    !digest.test(c.sha256)
  )
    throw new Error("Unverified release observation");
  return {
    status: "available",
    candidate: { version: c.version, tag: c.tag, sha256: c.sha256 },
  };
}
export const progressStates = [
  "preparing",
  "downloading",
  "verifying",
  "ready",
  "committing",
  "installing",
  "postchecking",
  "current",
  "paused",
  "deferred",
  "updated",
  "recoveryRequired",
] as const;
export type UpdateProgress = {
  requestId: string;
  bootId: string;
  sequence: number;
  state: (typeof progressStates)[number];
  observedMs: number;
  ageMs: number;
  remainingMs: number;
  fresh: boolean;
  candidateVersion: string | null;
  candidateSha256: string | null;
  closeAllowed: false;
};
const integer = (v: unknown): v is number =>
  Number.isSafeInteger(v) && (v as number) >= 0;
export function parseUpdateProgress(
  value: unknown,
  id: string,
): UpdateProgress {
  if (
    !requestIdPattern.test(id) ||
    !object(value) ||
    !exact(value, [
      "requestId",
      "bootId",
      "sequence",
      "state",
      "observedMs",
      "ageMs",
      "remainingMs",
      "fresh",
      "candidateVersion",
      "candidateSha256",
      "closeAllowed",
    ]) ||
    value.requestId !== id ||
    typeof value.bootId !== "string" ||
    !requestIdPattern.test(value.bootId) ||
    !integer(value.sequence) ||
    value.sequence < 1 ||
    value.sequence > 32 ||
    !progressStates.includes(value.state as UpdateProgress["state"]) ||
    !integer(value.observedMs) ||
    !integer(value.ageMs) ||
    !integer(value.remainingMs) ||
    value.remainingMs > 900_000 ||
    typeof value.fresh !== "boolean" ||
    (value.fresh && value.ageMs > 10_000) ||
    value.closeAllowed !== false ||
    !(
      (value.candidateVersion === null && value.candidateSha256 === null) ||
      (validVersion(value.candidateVersion) &&
        typeof value.candidateSha256 === "string" &&
        digest.test(value.candidateSha256))
    ) ||
    (value.state === "ready" && value.candidateVersion === null) ||
    (["preparing", "downloading", "verifying", "ready"].includes(
      value.state as string,
    ) &&
      value.remainingMs === 0 &&
      value.fresh)
  )
    throw new Error("Unverified progress observation");
  return { ...value } as UpdateProgress;
}
const terminal = (s: UpdateProgress["state"]) =>
  ["current", "paused", "deferred", "updated", "recoveryRequired"].includes(s);
/** Drop counters/age from the immutable publication identity. Repeated polls may
 * observe the same publication; they must not refresh its reported age. */
export function acceptProgress(
  previous: UpdateProgress | null,
  next: UpdateProgress,
): UpdateProgress {
  if (previous) {
    const identity = (p: UpdateProgress) =>
      JSON.stringify([
        p.requestId,
        p.bootId,
        p.sequence,
        p.state,
        p.observedMs,
        p.candidateVersion,
        p.candidateSha256,
      ]);
    if (
      previous.requestId !== next.requestId ||
      previous.bootId !== next.bootId ||
      next.sequence < previous.sequence ||
      next.observedMs < previous.observedMs ||
      (previous.candidateSha256 !== null &&
        (next.candidateSha256 !== previous.candidateSha256 ||
          next.candidateVersion !== previous.candidateVersion)) ||
      (next.sequence === previous.sequence &&
        (identity(next) !== identity(previous) ||
          next.ageMs < previous.ageMs ||
          next.remainingMs > previous.remainingMs)) ||
      (!terminal(previous.state) &&
        !terminal(next.state) &&
        progressStates.indexOf(next.state) <
          progressStates.indexOf(previous.state)) ||
      (terminal(previous.state) && identity(next) !== identity(previous))
    )
      throw new Error("Progress continuity lost");
  }
  return next;
}

/** Correlation only: accepted is not readiness, liveness or close authority. */
export type RequestReceipt = {
  schemaVersion: 1;
  requestId: string;
  bootId: string;
  createdMs: number;
  deadlineMs: number;
  status: "pending" | "accepted";
  expired: boolean;
};
export function parseRequestReceipt(value: unknown): RequestReceipt | null {
  if (value === null) return null;
  if (
    !object(value) ||
    !exact(value, [
      "schemaVersion",
      "requestId",
      "bootId",
      "createdMs",
      "deadlineMs",
      "status",
      "expired",
    ]) ||
    value.schemaVersion !== 1 ||
    typeof value.requestId !== "string" ||
    !requestIdPattern.test(value.requestId) ||
    typeof value.bootId !== "string" ||
    !requestIdPattern.test(value.bootId) ||
    typeof value.createdMs !== "number" ||
    !Number.isSafeInteger(value.createdMs) ||
    value.createdMs < 0 ||
    typeof value.deadlineMs !== "number" ||
    !Number.isSafeInteger(value.deadlineMs) ||
    value.deadlineMs !== value.createdMs + 900000 ||
    (value.status !== "pending" && value.status !== "accepted") ||
    typeof value.expired !== "boolean"
  )
    throw new Error("Unverified request receipt");
  return value as RequestReceipt;
}
