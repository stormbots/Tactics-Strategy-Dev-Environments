import { useEffect, useState } from "react";
import {
  checksFrom,
  collectionTime,
  parseEvent,
  toolForCheck,
  type Report,
} from "./model";
import {
  pythonObservation,
  type PythonObservation,
} from "./runtimeObservation";

/** Complete collection and one consistent runtime record, not a diagnostic-text guess. */
export function completePythonObservation(
  report: Report,
): PythonObservation | null {
  const events = report.lines.map(parseEvent);
  const runtime = report.lines.filter(
    (_, index) =>
      events[index]?.kind === "runtime" && events[index]?.key === "Python",
  );
  const checks = checksFrom(report.lines),
    failures = checks.filter((c) => c.status === "FAIL").length;
  const terminal = events
    .filter((e) => e && ["validation", "summary", "error"].includes(e.kind))
    .at(-1);
  if (
    runtime.length !== 1 ||
    !checks.length ||
    collectionTime(report.validation_collected_at) === null ||
    terminal?.kind !== "summary" ||
    terminal.key !== String(failures) ||
    ![0, 1].includes(report.code) ||
    report.success !== (failures === 0) ||
    (report.code === 0) !== (failures === 0)
  )
    return null;
  const value = pythonObservation(runtime[0]);
  if (!value) return null;
  const paired = checks.filter((c) => toolForCheck(c) === "Python");
  if (
    paired.length !== 1 ||
    paired[0].status !== (value.status === "passed" ? "PASS" : "FAIL")
  )
    return null;
  if (
    ["venvFailed", "pipFailed"].includes(value.reason) &&
    (!value.version || !value.executable)
  )
    return null;
  if (
    value.status === "unusable" &&
    !["interpreterFailed", "venvFailed", "pipFailed"].includes(value.reason)
  )
    return null;
  if (
    value.status === "incomplete" &&
    ![
      "discoveryIncomplete",
      "interpreterTimeout",
      "venvTimeout",
      "pipTimeout",
    ].includes(value.reason)
  )
    return null;
  return value;
}
function wording(value: PythonObservation | null) {
  if (!value)
    return {
      title: "We couldn’t confirm the Python result",
      detail:
        "SDE did not get one complete, consistent Python result. This does not mean Python is missing.",
    };
  if (value.status === "notFound")
    return {
      title: "Python 3.14 wasn’t found by this check",
      detail:
        "SDE’s supported search did not find Python 3.14. Other Python versions can stay installed. Checking again will not install the required version.",
    };
  if (value.status === "incomplete")
    return {
      title: value.reason.endsWith("Timeout")
        ? "The Python check took too long"
        : "We couldn’t finish checking Python",
      detail: value.reason.endsWith("Timeout")
        ? "SDE couldn’t finish checking Python because one step took too long. This does not mean Python is missing."
        : "SDE could not finish looking for or checking Python 3.14. It cannot yet confirm whether the required version is usable.",
    };
  if (value.reason === "venvFailed")
    return {
      title: "Python’s test project could not be set up",
      detail:
        "SDE found Python 3.14, but could not create its small test project environment. This check does not change your existing projects.",
    };
  if (value.reason === "pipFailed")
    return {
      title: "Python’s test project could not use pip",
      detail:
        "SDE’s test project could not use pip, the tool that installs Python packages. Review the check before choosing any setup change.",
    };
  return {
    title: "Python 3.14 could not be used",
    detail:
      "The selected Python command did not complete its required check. This does not show that another installed version caused the problem.",
  };
}

export function PythonReadinessCard({
  report,
  pending,
  busy,
  onReview,
  onCheck,
  onSupport,
}: {
  report: Report | null;
  pending: boolean;
  busy: boolean;
  onReview: () => void;
  onCheck: () => void;
  onSupport: () => void;
}) {
  const [earlier, setEarlier] = useState<Report | null>(null);
  useEffect(() => {
    if (report) setEarlier(report);
  }, [report]);
  const shown = report ?? earlier;
  if (!shown) return null;
  const value = completePythonObservation(shown);
  const checks = checksFrom(shown.lines).filter(
    (c) => toolForCheck(c) === "Python",
  );
  if (
    value?.status === "passed" ||
    (!value &&
      !checks.some((c) => c.status === "FAIL" || c.status === "WARNING"))
  )
    return null;
  const text = wording(value);
  return (
    <section
      className="information-card"
      aria-labelledby="python-readiness-heading"
      aria-busy={pending}
    >
      <p className="eyebrow">Tool readiness · Python</p>
      <h2 id="python-readiness-heading">{text.title}</h2>
      {!report && (
        <p role="status">
          {pending
            ? "Checking setup again. The earlier Python result stays below until the new check finishes."
            : "The new check did not provide a Python result. These are earlier findings. Check again or create a support report."}
        </p>
      )}
      <p>{text.detail}</p>
      <p>
        Required: <strong>Python 3.14.x</strong>
        {value?.version && (
          <>
            {" "}
            · Detected required version: <strong>{value.version}</strong>
          </>
        )}
      </p>
      <p>
        Review the validation result before choosing a setup change. SDE must
        show the full scope of any installation before you approve it.
      </p>
      <details>
        <summary>Python check details</summary>
        {value?.executable && <p>{value.executable}</p>}
        {checks.map((c, index) => (
          <p key={index}>{c.message}</p>
        ))}
      </details>
      <div className="result-actions">
        <button className="secondary" disabled={busy} onClick={onReview}>
          Review Python check
        </button>
        <button className="secondary" disabled={busy} onClick={onCheck}>
          Check setup again
        </button>
        <button className="secondary" disabled={busy} onClick={onSupport}>
          Create Python support report
        </button>
      </div>
    </section>
  );
}
