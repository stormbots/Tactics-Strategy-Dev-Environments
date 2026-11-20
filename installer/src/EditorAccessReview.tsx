import { useId, useState } from "react";
import { editorAccessMessage } from "./editorPreferences";

export function EditorAccessReview({
  path,
  busy,
  onCheck,
  onSupport,
  showHeading = true,
}: {
  path: string;
  busy: boolean;
  onCheck: () => void;
  onSupport: () => void;
  showHeading?: boolean;
}) {
  const [reviewing, setReviewing] = useState(false);
  const id = useId();
  return (
    <div className="validation-guidance">
      {showHeading && <strong>We couldn’t finish checking VSCodium</strong>}
      <p>
        <b>Check incomplete</b>
      </p>
      <p>{editorAccessMessage}</p>
      <button
        className="secondary"
        disabled={busy}
        aria-expanded={reviewing}
        aria-controls={id}
        onClick={() => setReviewing((value) => !value)}
      >
        Review access problem
      </button>
      {reviewing && (
        <section id={id} aria-label="VSCodium access review">
          <p>
            VSCodium is the app you use to write code. SDE could not read this
            preferences file:
          </p>
          <p className="log-path">
            <code>{path}</code>
          </p>
          <ol>
            <li>
              Use the account that owns these preferences. Keep SDE open as your
              normal desktop user.
            </li>
            <li>
              Ask your teacher or administrator to check whether that account
              can read the file. Keep the file and its settings. Do not give
              everyone access or run SDE as an administrator to get around this
              problem.
            </li>
            <li>
              After access is checked, choose Check VSCodium again. SDE will run
              its normal setup checks. It will not install apps or change your
              preferences.
            </li>
          </ol>
          <p>
            If access is still denied, keep this review open and create a
            support report. You can review the report before sharing it.
          </p>
          <div className="result-actions">
            <button className="secondary" disabled={busy} onClick={onCheck}>
              {busy ? "Checking…" : "Check VSCodium again"}
            </button>
            <button className="secondary" disabled={busy} onClick={onSupport}>
              Create access support report
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
