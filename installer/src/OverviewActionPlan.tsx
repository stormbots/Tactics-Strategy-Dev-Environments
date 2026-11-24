import { checksFrom, toolForCheck, type Report, type Schedule } from "./model";
import type { RecoveryState } from "./recovery";
import {
  completePythonObservation,
  pythonReadinessCardVisible,
} from "./PythonReadinessCard";
import { completeNodeObservation } from "./nodeObservation";
import { nodeReadinessCardVisible } from "./NodeReadinessCard";
import { editorAccessFinding } from "./EditorAccessOverviewCard";
import { completeEditorPreferences } from "./editorPreferences";
import { changeSafetyNeedsReview } from "./ChangeSafetyOverviewCard";
import { maintenanceOverviewVisible } from "./MaintenanceOverviewCard";

export type FindingLink = { heading: string; label: string };
/** Navigation only. Never supplies readiness, operation consent or native admission. */
export function overviewFindingLinks({
  report,
  accessReport,
  recovery,
  safetyError,
  maintenance,
  pending,
}: {
  report: Report | null;
  accessReport: Report | null;
  recovery: RecoveryState | null;
  safetyError: string;
  maintenance: Schedule | null;
  pending: boolean;
}): FindingLink[] {
  // Keep existing guidance while collection is unfinished or only legacy diagnostics exist.
  if (
    pending ||
    !report ||
    !(
      completePythonObservation(report) ||
      completeNodeObservation(report) ||
      completeEditorPreferences(report)
    )
  )
    return [];
  // Findings without a corresponding card keep the existing supported guidance.
  if (
    checksFrom(report.lines).some(
      (check) =>
        check.status === "FAIL" &&
        !["Python", "Node.js"].includes(toolForCheck(check) ?? ""),
    )
  )
    return [];
  const links: FindingLink[] = [];
  if (changeSafetyNeedsReview(recovery, false, safetyError))
    links.push({
      heading: "change-safety-overview-heading",
      label: "Review change safety",
    });
  if (pythonReadinessCardVisible(report))
    links.push({
      heading: "python-readiness-heading",
      label: "Review the Python requirement",
    });
  if (nodeReadinessCardVisible(report))
    links.push({
      heading: "node-readiness-heading",
      label: "Review the Node.js/npm requirement",
    });
  if (editorAccessFinding(accessReport))
    links.push({
      heading: "editor-access-overview-heading",
      label: "Review the VSCodium access problem",
    });
  if (maintenanceOverviewVisible(maintenance, false))
    links.push({
      heading: "maintenance-overview-heading",
      label: "View weekly maintenance details",
    });
  return links;
}
export function OverviewActionPlan({
  items,
  busy,
}: {
  items: FindingLink[];
  busy: boolean;
}) {
  return (
    <>
      <p>
        Open an item below to see its next steps. Reviewing an item does not
        start a change.
      </p>
      <ol aria-label="Items to review">
        {items.map((item) => (
          <li key={item.heading}>
            <button
              className="text-button"
              disabled={busy}
              onClick={() => {
                const heading = document.getElementById(item.heading);
                if (!heading) return;
                heading.focus();
                heading.scrollIntoView({ block: "center", behavior: "auto" });
              }}
            >
              {item.label}
            </button>
          </li>
        ))}
      </ol>
    </>
  );
}
