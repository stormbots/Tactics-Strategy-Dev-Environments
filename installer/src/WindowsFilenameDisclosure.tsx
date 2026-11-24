import type { OperationKind } from "./safeOperations";

/** Explains existing behavior only; it never changes settings or admission. */
export function WindowsFilenameDisclosure({
  platformLabel,
  operation,
}: {
  platformLabel: string;
  operation: OperationKind;
}) {
  if (!/^Windows\b/i.test(platformLabel)) return null;
  const label = { install: "Install", repair: "Repair", update: "Update" }[
    operation
  ];
  return (
    <aside aria-label="Required Windows setting">
      <h3>Windows must show file-name extensions</h3>
      <p>
        SDE requires complete filenames, such as <code>robot.py</code> and{" "}
        <code>settings.json</code>, so students and instructors can identify the
        files.
      </p>
      <p>
        {label} includes a profile setup step that turns on file-name extensions
        if they are hidden. This required setting can replace your current
        preference.
      </p>
      <p>
        This setting changes how File Explorer displays filenames. Review the
        full operation before approving it.
      </p>
    </aside>
  );
}
