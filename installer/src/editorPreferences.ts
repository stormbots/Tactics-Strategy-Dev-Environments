import { checksFrom, collectionTime, parseEvent, type Report } from "./model";

export const editorAccessMessage =
  "SDE could not open the file that stores your VSCodium preferences because it did not have permission to read it. Your settings have not been changed, and VSCodium may still work normally.";

export type EditorPreferences = {
  schema: 1;
  component: "VSCodium";
  scope: "standardUserFile";
  path: string | null;
  status: "read" | "missing" | "unreadable" | "invalid" | "unavailable";
  reason: string;
  recommendations: unknown[];
};
const reasons = {
  read: ["verified"],
  missing: ["defaults"],
  unreadable: ["accessDenied", "readFailed"],
  invalid: ["invalidContents"],
  unavailable: [
    "parserUnavailable",
    "inspectionLimit",
    "locationUnavailable",
    "encodingUnavailable",
  ],
};
const fields = [
  "schema",
  "component",
  "scope",
  "path",
  "status",
  "reason",
  "recommendations",
];
const safePath = (value: unknown): value is string =>
  typeof value === "string" &&
  value.length > 1 &&
  value.length <= 4096 &&
  (/^[A-Za-z]:\\/.test(value) || value.startsWith("/")) &&
  !/[\x00-\x1f\x7f|\u202a-\u202e\u2066-\u2069]/.test(value);

/** Display evidence only: no path is sent to Open, a settings writer or elevation. */
export function editorPreferences(lines: string[]): EditorPreferences | null {
  const events = lines
    .map(parseEvent)
    .filter(
      (event) => event?.kind === "preferences" && event.key === "VSCodium",
    );
  if (events.length !== 1 || events[0]!.message.length > 16384) return null;
  try {
    const value = JSON.parse(events[0]!.message);
    if (
      !value ||
      typeof value !== "object" ||
      Object.keys(value).length !== fields.length ||
      Object.keys(value).some((key) => !fields.includes(key)) ||
      value.schema !== 1 ||
      value.component !== "VSCodium" ||
      value.scope !== "standardUserFile" ||
      typeof value.status !== "string" ||
      !Object.hasOwn(reasons, value.status) ||
      !reasons[value.status as keyof typeof reasons].includes(value.reason) ||
      !(
        safePath(value.path) ||
        (value.path === null && value.reason === "locationUnavailable")
      ) ||
      !Array.isArray(value.recommendations)
    )
      return null;
    if (value.status !== "read")
      return value.recommendations.length === 0 ? value : null;
    const expected = [
      ["editor.formatOnSave", true],
      ["editor.defaultFormatter", "esbenp.prettier-vscode"],
      ["files.eol", "\n"],
    ];
    if (value.recommendations.length !== expected.length) return null;
    for (const [index, row] of value.recommendations.entries()) {
      const [key, recommended] = expected[index];
      if (
        !row ||
        typeof row !== "object" ||
        Object.keys(row).sort().join(",") !== "key,recommended,status,value" ||
        row.key !== key ||
        row.recommended !== recommended ||
        !["matches", "different", "unset"].includes(row.status) ||
        !(
          row.value === null ||
          typeof row.value === "boolean" ||
          (typeof row.value === "string" && row.value.length <= 256)
        ) ||
        (row.status === "matches") !== (row.value === recommended) ||
        (row.status === "unset" && row.value !== null)
      )
        return null;
    }
    return value;
  } catch {
    return null;
  }
}

/** Partial output or a missing record cannot settle the earlier access finding.
 * Unrelated required failures do not prevent a complete preferences observation. */
export function completeEditorPreferences(
  report: Report,
): EditorPreferences | null {
  const checks = checksFrom(report.lines);
  const failures = checks.filter((check) => check.status === "FAIL").length;
  const terminal = report.lines
    .map(parseEvent)
    .filter(
      (event) =>
        event && ["validation", "summary", "error"].includes(event.kind),
    )
    .at(-1);
  if (
    !checks.length ||
    collectionTime(report.validation_collected_at) === null ||
    terminal?.kind !== "summary" ||
    terminal.key !== String(failures) ||
    ![0, 1].includes(report.code) ||
    report.success !== (failures === 0) ||
    (report.code === 0) !== (failures === 0)
  )
    return null;
  return editorPreferences(report.lines);
}
