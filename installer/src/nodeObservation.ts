import { parseEvent } from "./model";

/** Verification data only. A passing pair grants no package-maintenance authority. */
export type NodeObservation = {
  schema: 1;
  component: "Node.js";
  requiredFamily: "24";
  status: "passed" | "notFound" | "unusable" | "incomplete";
  reason:
    | "verified"
    | "notDiscovered"
    | "nodeFailed"
    | "npmFailed"
    | "npmTimeout"
    | "discoveryIncomplete";
  version: string | null;
  executable: string | null;
  npmVersion: string | null;
  npmCli: string | null;
  maintenanceEligibility: "notEvaluated";
};
export function nodeObservation(line: string): NodeObservation | null {
  const event = parseEvent(line);
  if (
    event?.kind !== "runtime" ||
    event.key !== "Node.js" ||
    event.message.length > 16384
  )
    return null;
  try {
    const value = JSON.parse(event.message);
    const fields = [
      "schema",
      "component",
      "requiredFamily",
      "status",
      "reason",
      "version",
      "executable",
      "npmVersion",
      "npmCli",
      "maintenanceEligibility",
    ];
    if (
      !value ||
      typeof value !== "object" ||
      Object.keys(value).length !== fields.length ||
      Object.keys(value).some((k) => !fields.includes(k))
    )
      return null;
    if (
      value.schema !== 1 ||
      value.component !== "Node.js" ||
      value.requiredFamily !== "24" ||
      value.maintenanceEligibility !== "notEvaluated"
    )
      return null;
    if (
      !["passed", "notFound", "unusable", "incomplete"].includes(
        value.status,
      ) ||
      ![
        "verified",
        "notDiscovered",
        "nodeFailed",
        "npmFailed",
        "npmTimeout",
        "discoveryIncomplete",
      ].includes(value.reason)
    )
      return null;
    const text = (input: unknown, pattern: RegExp, limit: number) =>
      typeof input === "string" &&
      input.length <= limit &&
      !/[\x00-\x1f\x7f|]/.test(input) &&
      pattern.test(input);
    const linuxPath = (input: unknown) =>
      text(input, /^\/.+$/, 4096) &&
      !(input as string)
        .split("/")
        .some(
          (part, index) =>
            part === ".." || part === "." || (index > 0 && part === ""),
        ) &&
      !(input as string).includes("\\");
    if (!(
      value.version === null ||
      text(value.version, /^24\.\d{1,8}\.\d{1,8}$/, 30)
    ))
      return null;
    if (!(
      value.executable === null ||
      text(value.executable, /^[A-Za-z]:\\.+\.exe$/i, 4096) ||
      linuxPath(value.executable)
    ))
      return null;
    if (!(
      value.npmCli === null ||
      text(
        value.npmCli,
        /^[A-Za-z]:\\.+\\node_modules\\npm\\bin\\npm-cli\.js$/i,
        4096,
      ) ||
      linuxPath(value.npmCli)
    ))
      return null;
    if (!(
      value.npmVersion === null ||
      text(value.npmVersion, /^[0-9][A-Za-z0-9.!+_-]{0,119}$/, 120)
    ))
      return null;
    if (value.status === "passed") {
      if (
        value.reason !== "verified" ||
        !value.version ||
        !value.executable ||
        !value.npmVersion ||
        !value.npmCli
      )
        return null;
      if (value.executable.startsWith("/")) {
        if (!value.executable.endsWith("/bin/node")) return null;
        const expected =
          value.executable.slice(0, -"bin/node".length) +
          "lib/node_modules/npm/bin/npm-cli.js";
        if (
          value.npmCli !== expected &&
          !(
            value.executable === "/usr/bin/node" &&
            value.npmCli === "/usr/share/nodejs/npm/bin/npm-cli.js"
          )
        )
          return null;
      } else {
        const expected =
          value.executable.replace(/[\\/][^\\/]+$/, "") +
          "\\node_modules\\npm\\bin\\npm-cli.js";
        if (value.npmCli.toLowerCase() !== expected.toLowerCase()) return null;
      }
    } else if (
      value.reason === "verified" ||
      value.npmVersion !== null ||
      value.npmCli !== null
    )
      return null;
    if (
      value.status === "notFound" &&
      (value.reason !== "notDiscovered" ||
        value.version !== null ||
        value.executable !== null)
    )
      return null;
    return value;
  } catch {
    return null;
  }
}
