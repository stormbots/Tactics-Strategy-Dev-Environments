import { completeEditorPreferences } from "./editorPreferences";
import { EditorAccessReview } from "./EditorAccessReview";
import type { Report } from "./model";

/** A view of confirmed access denial; no settings writer or caller-selected native path. */
export function EditorAccessOverviewCard({
  report,
  stale,
  busy,
  onCheck,
  onSupport,
}: {
  report: Report | null;
  stale: boolean;
  busy: boolean;
  onCheck: () => void;
  onSupport: () => void;
}) {
  const value = editorAccessFinding(report);
  if (!value?.path) return null;
  return (
    <section
      className="information-card"
      aria-labelledby="editor-access-overview-heading"
      aria-busy={busy}
    >
      <p className="eyebrow">Tool readiness · VSCodium</p>
      <h2 id="editor-access-overview-heading" tabIndex={-1}>
        We couldn’t finish checking VSCodium
      </h2>
      {stale && (
        <p role="status">
          {busy
            ? "Checking setup again. The earlier access finding stays below until the new check finishes."
            : "The new check did not provide a complete preferences result. These are earlier findings. Keep this review open and check again or create a support report."}
        </p>
      )}
      <EditorAccessReview
        key={value.path}
        path={value.path}
        busy={busy}
        onCheck={onCheck}
        onSupport={onSupport}
        showHeading={false}
      />
    </section>
  );
}

export function editorAccessFinding(report: Report | null) {
  const value = report ? completeEditorPreferences(report) : null;
  return value?.status === "unreadable" &&
    value.reason === "accessDenied" &&
    value.path
    ? value
    : null;
}
