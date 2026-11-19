import type { Schedule } from "./model";

export function MaintenanceDisabledChoice({
  data,
  saved,
  busy,
  onSave,
}: {
  data: Schedule | null;
  saved: boolean;
  busy: boolean;
  onSave: () => void;
}) {
  if (
    !data ||
    data.status !== "disabled" ||
    data.inspectionScope !== "schedule" ||
    data.inspectionReason !== "verified"
  )
    return null;
  return (
    <div>
      {saved ? (
        <p>
          Your choice to leave maintenance disabled is saved for your account on
          this computer. The schedule is still disabled.
        </p>
      ) : (
        <>
          <p>
            You can leave maintenance disabled. Saving this choice does not turn
            maintenance on or off, change earlier results, or allow another
            operation.
          </p>
          {data.choiceContext ? (
            <button className="secondary" disabled={busy} onClick={onSave}>
              Leave maintenance disabled
            </button>
          ) : (
            <p>
              Saving a choice is not available for this schedule. You can check
              its status again or ask your teacher to review it with you.
            </p>
          )}
        </>
      )}
    </div>
  );
}
