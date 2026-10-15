import { validationGuidance, type Guidance } from "./validationGuidance";
import type { Check, ToolRecord } from "./model";

export function ValidationCheck({
  check,
  record,
  supported,
  busy,
  onReview,
  onSchedule,
}: {
  check: Check;
  record?: ToolRecord;
  supported: boolean;
  busy: boolean;
  onReview: (operation: NonNullable<Guidance["operation"]>) => void;
  onSchedule: () => void;
}) {
  const guidance = validationGuidance(check, record, supported);
  if (!guidance) return <>{check.message}</>;
  return (
    <div className="validation-guidance">
      <strong>{guidance.title}</strong>
      <p>{guidance.impact}</p>
      <p>
        <b>Next step · {guidance.category}:</b> {guidance.next}
      </p>
      {guidance.operation && (
        <button
          className="secondary"
          disabled={busy}
          onClick={() => onReview(guidance.operation!)}
          aria-label={`Review ${guidance.category} for ${guidance.title}`}
        >
          Review {guidance.category}
        </button>
      )}
      {guidance.destination === "schedule" && (
        <button className="secondary" onClick={onSchedule}>
          View Schedule
        </button>
      )}
      <details className="check-diagnostics">
        <summary>Technical details</summary>
        <p>{check.message}</p>
      </details>
    </div>
  );
}
