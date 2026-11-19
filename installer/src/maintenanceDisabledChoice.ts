import type { Schedule } from "./model";

// View preference only. No native consumer may use this as policy or consent.
export const disabledChoiceKey = "sde.maintenance.disabled-choice.v1";
export type ChoiceContext = {
  machineId: string;
  identifier: string;
  definitionId: string;
};
type Choice = {
  schema: 1;
  decision: "leaveDisabled";
  context: string;
  observedAt: string;
  chosenAt: string;
};
type Store = Pick<Storage, "getItem" | "setItem">;
const owned = new Set([
  "skyview-student-dev-update.timer",
  "\\Skyview Robotics - Dev Tool Updates",
]);
const hex = /^[0-9a-f]{64}$/;
const timestamp = (value: unknown) =>
  typeof value === "string" &&
  value.length <= 40 &&
  Number.isFinite(Date.parse(value))
    ? Date.parse(value)
    : NaN;

async function fingerprint(context: ChoiceContext) {
  if (
    typeof context.machineId !== "string" ||
    !hex.test(context.machineId) ||
    !owned.has(context.identifier) ||
    typeof context.definitionId !== "string" ||
    !hex.test(context.definitionId)
  )
    throw new Error("The maintenance choice context could not be verified.");
  const bytes = new TextEncoder().encode(
    JSON.stringify([
      context.machineId,
      context.identifier,
      context.definitionId,
    ]),
  );
  return Array.from(
    new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    (value) => value.toString(16).padStart(2, "0"),
  ).join("");
}
function freshDisabled(
  context: ChoiceContext,
  observation: Schedule,
  now: number,
) {
  const time = timestamp(observation.observedAt);
  return (
    Number.isFinite(now) &&
    time > 0 &&
    time <= now &&
    now - time <= 300_000 &&
    observation.identifier === context.identifier &&
    observation.status === "disabled" &&
    observation.inspectionScope === "schedule" &&
    observation.inspectionReason === "verified"
  );
}
function parse(raw: string | null): Choice | null {
  if (!raw || raw.length > 1024) return null;
  try {
    const value = JSON.parse(raw);
    if (
      !value ||
      typeof value !== "object" ||
      Array.isArray(value) ||
      Object.keys(value).sort().join(",") !==
        "chosenAt,context,decision,observedAt,schema" ||
      value.schema !== 1 ||
      value.decision !== "leaveDisabled" ||
      typeof value.context !== "string" ||
      !hex.test(value.context) ||
      !(timestamp(value.observedAt) > 0) ||
      !(timestamp(value.chosenAt) >= timestamp(value.observedAt))
    )
      return null;
    return value;
  } catch {
    return null;
  }
}
export async function readDisabledChoice(
  context: ChoiceContext,
  observation: Schedule,
  store: Store,
  now = Date.now(),
): Promise<boolean> {
  if (!freshDisabled(context, observation, now)) return false;
  try {
    const value = parse(store.getItem(disabledChoiceKey));
    return (
      !!value &&
      timestamp(value.chosenAt) <= now &&
      value.context === (await fingerprint(context))
    );
  } catch {
    return false;
  }
}
export async function saveDisabledChoice(
  context: ChoiceContext,
  observation: Schedule,
  store: Store,
  now = Date.now(),
  isCurrent: () => boolean = () => true,
): Promise<{ saved: boolean; error?: string }> {
  if (!freshDisabled(context, observation, now))
    return {
      saved: false,
      error: "Check maintenance again before saving this choice.",
    };
  try {
    const value: Choice = {
      schema: 1,
      decision: "leaveDisabled",
      context: await fingerprint(context),
      observedAt: new Date(timestamp(observation.observedAt)).toISOString(),
      chosenAt: new Date(now).toISOString(),
    };
    const raw = JSON.stringify(value);
    if (!isCurrent())
      return {
        saved: false,
        error:
          "Your choice was not saved. Review the current schedule and try again.",
      };
    store.setItem(disabledChoiceKey, raw);
    if (store.getItem(disabledChoiceKey) !== raw)
      throw new Error("Choice was not confirmed");
    return { saved: true };
  } catch {
    return {
      saved: false,
      error:
        "SDE couldn’t save your choice. Maintenance has not been changed. Try saving again.",
    };
  }
}
