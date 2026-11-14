import { expect, it } from "vitest";
import { pythonObservation } from "./runtimeObservation";

const record = {
  schema: 1,
  component: "Python",
  requiredFamily: "3.14",
  status: "passed",
  reason: "verified",
  version: "3.14.9",
  executable: "C:\\Python 314\\python.exe",
  pipVersion: "25.3",
};
const line = (value: unknown) =>
  `SKYVIEW_EVENT|runtime|Python|${JSON.stringify(value)}`;
it("retains explicit paired interpreter evidence from the backend", () => {
  expect(pythonObservation(line(record))).toEqual(record);
});
it("distinguishes an unfinished check, a failed capability and a completed search", () => {
  for (const [status, reason] of [
    ["incomplete", "discoveryIncomplete"],
    ["unusable", "interpreterFailed"],
    ["notFound", "notDiscovered"],
  ]) {
    const observation = {
      ...record,
      status,
      reason,
      version: null,
      executable: null,
      pipVersion: null,
    };
    expect(pythonObservation(line(observation))).toEqual(observation);
  }
  const timeout = {
    ...record,
    status: "incomplete",
    reason: "pipTimeout",
    pipVersion: null,
  };
  expect(pythonObservation(line(timeout))).toEqual(timeout);
});
it("cannot turn partial, wrong-family or malformed evidence into a pass", () => {
  for (const patch of [
    { schema: 2 },
    { component: "Node.js" },
    { requiredFamily: "3.15" },
    { version: "3.15.1" },
    { version: "3.14.9\n" },
    { pipVersion: "25.3\n" },
    { executable: "C:\\Python\\python.exe\n" },
    { version: null },
    { executable: null },
    { pipVersion: null },
    { pipVersion: "pip 25" },
    { reason: "notDiscovered" },
    { executable: "python" },
    { executable: "C:\\Python\\python.exe\nrun" },
    { executable: "C:\\Python|314\\python.exe" },
    { command: "install" },
    { status: "ignored" },
  ])
    expect(pythonObservation(line({ ...record, ...patch }))).toBeNull();
  expect(
    pythonObservation(
      line({
        ...record,
        status: "notFound",
        reason: "notDiscovered",
        pipVersion: null,
      }),
    ),
  ).toBeNull();
  expect(
    pythonObservation(line({ ...record, status: "incomplete" })),
  ).toBeNull();
  expect(
    pythonObservation("SKYVIEW_EVENT|runtime|Python|{bad json"),
  ).toBeNull();
  expect(
    pythonObservation(
      line({ ...record, executable: `C:\\${"x".repeat(9000)}.exe` }),
    ),
  ).toBeNull();
});
it("does not infer observations from arbitrary diagnostic messages or other events", () => {
  expect(
    pythonObservation("SKYVIEW_EVENT|validation|FAIL|Python 3.15 is installed"),
  ).toBeNull();
  expect(
    pythonObservation(
      `SKYVIEW_EVENT|runtime|Node.js|${JSON.stringify(record)}`,
    ),
  ).toBeNull();
});
