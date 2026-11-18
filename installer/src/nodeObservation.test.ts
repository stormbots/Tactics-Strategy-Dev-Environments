import { expect, it } from "../testing/unitApi";
import { nodeObservation } from "./nodeObservation";
const record = {
  schema: 1,
  component: "Node.js",
  requiredFamily: "24",
  status: "passed",
  reason: "verified",
  version: "24.19.0",
  executable: "C:\\Node 24\\node.exe",
  npmVersion: "11.9.0",
  npmCli: "C:\\Node 24\\node_modules\\npm\\bin\\npm-cli.js",
  maintenanceEligibility: "notEvaluated",
};
const line = (value: unknown) =>
  `SKYVIEW_EVENT|runtime|Node.js|${JSON.stringify(value)}`;
it("retains the selected Node/npm pair without maintenance permission", () => {
  expect(nodeObservation(line(record))).toEqual(record);
  expect(
    nodeObservation(line({ ...record, npmVersion: "12.0.0-beta.1" })),
  ).not.toBeNull();
});
it("preserves incomplete and unusable evidence without fabricating a pass", () => {
  for (const [status, reason] of [
    ["incomplete", "npmTimeout"],
    ["unusable", "npmFailed"],
  ]) {
    const value = { ...record, status, reason, npmVersion: null, npmCli: null };
    expect(nodeObservation(line(value))).toEqual(value);
  }
  const missing = {
    ...record,
    status: "notFound",
    reason: "notDiscovered",
    version: null,
    executable: null,
    npmVersion: null,
    npmCli: null,
  };
  expect(nodeObservation(line(missing))).toEqual(missing);
});
it("rejects incomplete passes, another installation's npm and injected authority", () => {
  for (const patch of [
    { schema: 2 },
    { component: "Python" },
    { version: "26.1.0" },
    { requiredFamily: "26" },
    { version: null },
    { npmVersion: null },
    { npmCli: null },
    { executable: null },
    { npmCli: "C:\\Node26\\node_modules\\npm\\bin\\npm-cli.js" },
    { npmCli: "C:\\Node 24\\npm.cmd" },
    { maintenanceEligibility: "allowed" },
    { permission: "repair" },
    { npmVersion: "11.9.0\n" },
    { executable: "node" },
    { executable: "C:\\Node 24\\node.exe\n" },
    { executable: `C:\\${"x".repeat(5000)}.exe` },
  ])
    expect(nodeObservation(line({ ...record, ...patch }))).toBeNull();
  expect(nodeObservation(line({ ...record, status: "incomplete" }))).toBeNull();
});
it("does not derive executable evidence from raw diagnostics or another event", () => {
  expect(
    nodeObservation("SKYVIEW_EVENT|validation|FAIL|Node.js not found"),
  ).toBeNull();
  expect(nodeObservation("SKYVIEW_EVENT|runtime|Node.js|{broken")).toBeNull();
  expect(
    nodeObservation(`SKYVIEW_EVENT|runtime|Python|${JSON.stringify(record)}`),
  ).toBeNull();
});
it("accepts bounded Linux pairs without importing npm from another installation", () => {
  for (const [executable, npmCli] of [
    [
      "/home/student/.nvm/versions/node/v24.19.0/bin/node",
      "/home/student/.nvm/versions/node/v24.19.0/lib/node_modules/npm/bin/npm-cli.js",
    ],
    ["/usr/bin/node", "/usr/share/nodejs/npm/bin/npm-cli.js"],
    ["/usr/bin/node", "/usr/lib/node_modules/npm/bin/npm-cli.js"],
    [
      "/opt/Node 24/bin/node",
      "/opt/Node 24/lib/node_modules/npm/bin/npm-cli.js",
    ],
  ]) {
    const pair = { ...record, executable, npmCli };
    expect(nodeObservation(line(pair))).toEqual(pair);
    for (const bad of [
      "/usr/local/lib/node_modules/npm/bin/npm-cli.js",
      "/usr/bin/npm",
      "/tmp/../usr/share/nodejs/npm/bin/npm-cli.js",
      "C:\\Node 24\\node_modules\\npm\\bin\\npm-cli.js",
    ]) {
      expect(nodeObservation(line({ ...pair, npmCli: bad }))).toBeNull();
    }
  }
  for (const executable of [
    "/usr//bin/node",
    "/usr/../bin/node",
    "/usr/bin/node\n",
    "/usr/bin\\node",
  ]) {
    expect(
      nodeObservation(
        line({
          ...record,
          executable,
          npmCli: "/usr/share/nodejs/npm/bin/npm-cli.js",
        }),
      ),
    ).toBeNull();
  }
});
