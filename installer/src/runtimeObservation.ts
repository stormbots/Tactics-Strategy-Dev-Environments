import { parseEvent } from "./model";

/** Read-only evidence, never an executable command, saved preference or permit. */
export type PythonObservation = {
  schema: 1;
  component: "Python";
  requiredFamily: "3.14";
  status: "passed" | "notFound" | "unusable" | "incomplete";
  reason:
    | "verified"
    | "notDiscovered"
    | "interpreterFailed"
    | "interpreterTimeout"
    | "venvFailed"
    | "venvTimeout"
    | "pipFailed"
    | "pipTimeout"
    | "discoveryIncomplete";
  version: string | null;
  executable: string | null;
  pipVersion: string | null;
};

export function pythonObservation(line: string): PythonObservation | null {
  const event = parseEvent(line);
  if (
    event?.kind !== "runtime" ||
    event.key !== "Python" ||
    event.message.length > 8192
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
      "pipVersion",
    ];
    if (
      !value ||
      typeof value !== "object" ||
      Object.keys(value).length !== fields.length ||
      Object.keys(value).some((key) => !fields.includes(key))
    )
      return null;
    if (
      value.schema !== 1 ||
      value.component !== "Python" ||
      value.requiredFamily !== "3.14"
    )
      return null;
    if (
      !["passed", "notFound", "unusable", "incomplete"].includes(value.status)
    )
      return null;
    if (
      ![
        "verified",
        "notDiscovered",
        "interpreterFailed",
        "interpreterTimeout",
        "venvFailed",
        "venvTimeout",
        "pipFailed",
        "pipTimeout",
        "discoveryIncomplete",
      ].includes(value.reason)
    )
      return null;
    const version = (input: unknown) =>
      input === null ||
      (typeof input === "string" &&
        !/\s/.test(input) &&
        /^3\.14\.\d{1,8}$/.test(input));
    if (
      !version(value.version) ||
      !(
        value.pipVersion === null ||
        (typeof value.pipVersion === "string" &&
          !/\s/.test(value.pipVersion) &&
          /^[0-9][A-Za-z0-9.!+_-]{0,119}$/.test(value.pipVersion))
      )
    )
      return null;
    if (!(
      value.executable === null ||
      (typeof value.executable === "string" &&
        value.executable.length <= 4096 &&
        !/[\x00-\x1f|]/.test(value.executable) &&
        (/^[A-Za-z]:\\[^\r\n\x00-\x1f|]+\.exe$/i.test(value.executable) ||
          value.executable.startsWith("/")))
    ))
      return null;
    if (value.status === "passed") {
      if (
        value.reason !== "verified" ||
        !value.version ||
        !value.executable ||
        !value.pipVersion
      )
        return null;
    } else if (value.reason === "verified" || value.pipVersion !== null)
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
