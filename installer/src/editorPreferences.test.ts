import { expect, it } from "../testing/unitApi";
import {
  completeEditorPreferences,
  editorPreferences,
  editorAccessMessage,
} from "./editorPreferences";
import type { Report } from "./model";
const denied = {
  schema: 1,
  component: "VSCodium",
  scope: "standardUserFile",
  path: "C:\\Users\\Student\\VSCodium\\settings.json",
  status: "unreadable",
  reason: "accessDenied",
  recommendations: [],
};
const line = (value: unknown) =>
  `SKYVIEW_EVENT|preferences|VSCodium|${JSON.stringify(value)}`;
const report = (changes: Partial<Report> = {}): Report => ({
  code: 0,
  success: true,
  platform: { supported: true, label: "Windows 11" },
  log_path: "test",
  validation_collected_at: 100,
  lines: [
    line(denied),
    "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
    `SKYVIEW_EVENT|validation|WARNING|${editorAccessMessage}`,
    "SKYVIEW_EVENT|summary|0|Done",
  ],
  ...changes,
});
it("accepts Windows and Linux display locations without turning them into commands", () => {
  for (const path of [
    denied.path,
    "/home/student café/.config/VSCodium/User/settings.json",
  ])
    expect(editorPreferences([line({ ...denied, path })])?.path).toBe(path);
});
it.each([
  { schema: true },
  { status: ["unreadable"], reason: "accessDenied" },
  { component: "Other editor" },
  { scope: "workspace" },
  { status: "read", reason: "accessDenied" },
  { reason: "unknown" },
  { path: "relative/settings.json" },
  { path: "/tmp/bad\npath" },
  { path: "/tmp/hidden\u202eexe" },
  { path: "x".repeat(4097) },
  { recommendations: ["unexpected"] },
  { command: "do something" },
])("rejects malformed/ambiguous evidence: %j", (changes) => {
  expect(editorPreferences([line({ ...denied, ...changes })])).toBeNull();
});
it("does not reuse a valid record when another record is malformed or duplicated", () => {
  expect(editorPreferences([line(denied), line(denied)])).toBeNull();
  expect(
    editorPreferences([
      line(denied),
      "SKYVIEW_EVENT|preferences|VSCodium|{bad",
    ]),
  ).toBeNull();
});
it("requires complete collection before settling an earlier finding", () => {
  expect(completeEditorPreferences(report())?.reason).toBe("accessDenied");
  for (const changes of [
    { validation_collected_at: null },
    { code: 1 },
    { success: false },
    { code: 75, success: false },
    { lines: report().lines.slice(0, -1) },
    { lines: [...report().lines, "SKYVIEW_EVENT|error|collection|Stopped"] },
    { lines: report().lines.slice(1) },
  ])
    expect(completeEditorPreferences(report(changes))).toBeNull();
});
it("a complete preferences result does not depend on unrelated tool success", () => {
  const value = completeEditorPreferences(
    report({
      code: 1,
      success: false,
      lines: [
        line({ ...denied, status: "missing", reason: "defaults" }),
        "SKYVIEW_EVENT|validation|FAIL|Python 3.14 not found",
        "SKYVIEW_EVENT|summary|1|Done",
      ],
    }),
  );
  expect(value?.status).toBe("missing");
});
it("requires all three supported recommendation records for a successful read", () => {
  const recommendations = [
    {
      key: "editor.formatOnSave",
      recommended: true,
      value: false,
      status: "different",
    },
    {
      key: "editor.defaultFormatter",
      recommended: "esbenp.prettier-vscode",
      value: null,
      status: "unset",
    },
    { key: "files.eol", recommended: "\n", value: "\n", status: "matches" },
  ];
  const read = {
    ...denied,
    status: "read",
    reason: "verified",
    recommendations,
  };
  expect(editorPreferences([line(read)])?.status).toBe("read");
  expect(
    editorPreferences([line({ ...read, recommendations: [] })]),
  ).toBeNull();
  expect(
    editorPreferences([
      line({
        ...read,
        recommendations: [
          ...recommendations.slice(0, 2),
          { ...recommendations[2], value: "\r\n" },
        ],
      }),
    ]),
  ).toBeNull();
});
