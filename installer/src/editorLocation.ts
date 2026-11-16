import { parseEvent } from "./model";

/** Observation only. Native launch independently verifies the current target. */
export type EditorLocation = {
  schema: 1;
  component: "VSCodium";
  platform: "linux";
  status: "verified";
  reason: "verified";
  root: string;
  executable: string;
  cli: string;
  version: string;
  electronVersion: string;
  selectionId: string;
  maintenanceEligibility: "notEvaluated";
};
export function editorLocation(line: string): EditorLocation | null {
  const event = parseEvent(line);
  if (
    event?.kind !== "application" ||
    event.key !== "VSCodium" ||
    event.message.length > 32768
  )
    return null;
  try {
    const value = JSON.parse(event.message);
    const fields = [
      "schema",
      "component",
      "platform",
      "status",
      "reason",
      "root",
      "executable",
      "cli",
      "version",
      "electronVersion",
      "selectionId",
      "maintenanceEligibility",
    ];
    if (
      !value ||
      typeof value !== "object" ||
      Object.keys(value).length !== fields.length ||
      Object.keys(value).some((k) => !fields.includes(k)) ||
      value.schema !== 1 ||
      value.component !== "VSCodium" ||
      value.platform !== "linux" ||
      value.status !== "verified" ||
      value.reason !== "verified" ||
      value.maintenanceEligibility !== "notEvaluated"
    )
      return null;
    const path = (input: unknown): input is string =>
      typeof input === "string" &&
      input.length <= 4096 &&
      input.startsWith("/") &&
      !/[\x00-\x1f\x7f|]/.test(input) &&
      !input.includes("//") &&
      !input.split("/").some((p) => p === "." || p === "..");
    if (
      !path(value.root) ||
      !path(value.executable) ||
      !path(value.cli) ||
      value.executable !== `${value.root.replace(/\/$/, "")}/codium` ||
      value.cli !==
        `${value.root.replace(/\/$/, "")}/resources/app/out/cli.js` ||
      typeof value.version !== "string" ||
      !/^\d+\.\d+\.\d+(?:\.\d+)?$/.test(value.version) ||
      value.version.length > 80 ||
      typeof value.electronVersion !== "string" ||
      !/^\d+\.\d+\.\d+(?:[-+][\w.-]+)?$/.test(value.electronVersion) ||
      value.electronVersion.length > 80 ||
      typeof value.selectionId !== "string" ||
      !/^[a-f0-9]{64}$/.test(value.selectionId)
    )
      return null;
    return value;
  } catch {
    return null;
  }
}
export function selectedEditorId(lines: string[]): string | undefined {
  let result: string | undefined;
  for (const line of lines) {
    const event = parseEvent(line);
    if (event?.kind === "application" && event.key === "VSCodium")
      result = editorLocation(line)?.selectionId;
  }
  return result;
}
