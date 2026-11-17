import { expect, it } from "../testing/unitApi";
import { editorLocation, selectedEditorId } from "./editorLocation";

const record = {
  schema: 1,
  component: "VSCodium",
  platform: "linux",
  status: "verified",
  reason: "verified",
  root: "/home/student/My Editor",
  executable: "/home/student/My Editor/codium",
  cli: "/home/student/My Editor/resources/app/out/cli.js",
  version: "1.106.0.25351",
  electronVersion: "38.0.0",
  selectionId: "a".repeat(64),
  maintenanceEligibility: "notEvaluated",
};
const line = (value: unknown) =>
  `SKYVIEW_EVENT|application|VSCodium|${JSON.stringify(value)}`;

it("accepts a checked Windows installation while rejecting commands, UNC and escaped resources", () => {
  const windows = {
    ...record,
    platform: "windows",
    root: "C:\\Users\\Student\\My Editor",
    executable: "C:\\Users\\Student\\My Editor\\VSCodium.exe",
    cli: "C:\\Users\\Student\\My Editor\\resources\\app\\out\\cli.js",
  };
  expect(editorLocation(line(windows))).toEqual(windows);
  expect(selectedEditorId([line(windows)])).toBe(record.selectionId);
  for (const patch of [
    { executable: "C:\\Windows\\System32\\cmd.exe" },
    { root: "\\\\server\\app" },
    { root: "C:\\Users\\..\\Other" },
    { cli: "C:\\Other\\cli.js" },
  ]) {
    expect(editorLocation(line({ ...windows, ...patch }))).toBeNull();
  }
});

it("keeps a verified selection as data without granting update authority", () => {
  expect(editorLocation(line(record))).toEqual(record);
  expect(selectedEditorId([line(record)])).toBe(record.selectionId);
});
it.each([
  { schema: true },
  { status: "candidate" },
  { maintenanceEligibility: "allowed" },
  { platform: "other" },
  { extra: true },
  { root: "/home/../student/My Editor" },
  { executable: "/bin/sh" },
  { cli: "/tmp/other.js" },
  { selectionId: "A".repeat(64) },
  { version: "unknown" },
  { electronVersion: "" },
])("rejects incomplete or mismatched observations %j", (changed) => {
  expect(editorLocation(line({ ...record, ...changed }))).toBeNull();
});
it("invalidates an old selection when the newest check cannot verify it", () => {
  expect(
    selectedEditorId([
      line(record),
      line({ ...record, status: "incomplete", selectionId: null }),
    ]),
  ).toBeUndefined();
  expect(
    selectedEditorId([
      line(record),
      "SKYVIEW_EVENT|application|VSCodium|{invalid",
    ]),
  ).toBeUndefined();
  expect(
    selectedEditorId([
      line(record),
      "SKYVIEW_EVENT|validation|PASS|Other check",
    ]),
  ).toBe(record.selectionId);
});
