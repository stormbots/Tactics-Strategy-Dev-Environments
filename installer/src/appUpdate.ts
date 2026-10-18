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
