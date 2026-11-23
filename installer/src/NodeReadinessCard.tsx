import { useEffect, useState } from "react";
import { checksFrom, toolForCheck, type Report } from "./model";
import {
  completeNodeObservation,
  type NodeObservation,
} from "./nodeObservation";
function wording(value: NodeObservation | null) {
  if (!value)
    return {
      title: "We couldn’t confirm the Node.js/npm result",
      detail:
        "SDE did not get one complete, consistent result for Node.js and its npm package tool. This does not mean they are missing.",
    };
  if (value.status === "notFound")
    return {
      title: "Node.js 24 wasn’t found by this check",
      detail:
        "SDE’s supported search did not find Node.js 24. Other versions can stay installed. Checking again will not install it.",
    };
  if (value.status === "incomplete")
    return {
      title:
        value.reason === "npmTimeout"
          ? "The npm check took too long"
          : "We couldn’t finish checking Node.js and npm",
      detail:
        "SDE could not finish checking the required Node.js version and its associated npm. This does not mean either tool is missing.",
    };
  if (value.reason === "npmFailed")
    return {
      title: "Node.js 24 was found, but its npm check failed",
      detail:
        "npm installs packages for JavaScript projects. The npm paired with this Node.js installation did not pass its check. This does not show that another installed Node.js version caused the problem.",
    };
  return {
    title: "The Node.js command could not be used",
    detail:
      "A required Node.js command did not pass its check. Review the result before choosing any setup change.",
  };
}
export function NodeReadinessCard({
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
  const value = completeNodeObservation(shown),
    checks = checksFrom(shown.lines).filter(
      (c) => toolForCheck(c) === "Node.js" || /^npm:/.test(c.message),
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
      aria-labelledby="node-readiness-heading"
      aria-busy={pending}
    >
      <p className="eyebrow">Tool readiness · Node.js/npm</p>
      <h2 id="node-readiness-heading">{text.title}</h2>
      {!report && (
        <p role="status">
          {pending
            ? "Checking setup again. The earlier Node.js/npm result stays below until the new check finishes."
            : "The new check did not provide a Node.js/npm result. These are earlier findings. Check again or create a support report."}
        </p>
      )}
      <p>{text.detail}</p>
      <p>
        Required: <strong>Node.js 24.x and its npm</strong>
        {value?.version && (
          <>
            {" "}
            · Detected required version: <strong>{value.version}</strong>
          </>
        )}
      </p>
      <p>
        Recognizing these tools does not give SDE permission to replace them or
        manage their installation. Review the full scope before approving any
        setup change.
      </p>
      <details>
        <summary>Node.js/npm check details</summary>
        {value?.executable && <p>Node.js: {value.executable}</p>}
        {value?.npmCli && <p>Associated npm: {value.npmCli}</p>}
        {checks.map((c, i) => (
          <p key={i}>{c.message}</p>
        ))}
      </details>
      <div className="result-actions">
        <button className="secondary" disabled={busy} onClick={onReview}>
          Review Node.js/npm check
        </button>
        <button className="secondary" disabled={busy} onClick={onCheck}>
          Check setup again
        </button>
        <button className="secondary" disabled={busy} onClick={onSupport}>
          Create Node.js support report
        </button>
      </div>
    </section>
  );
}
