import { toolForCheck, type Check, type ToolRecord } from "./model";

export type Guidance = {
  title: string;
  impact: string;
  next: string;
  category: "Repair" | "Update" | "Manual step" | "Diagnostic review";
  operation?: "repair" | "update";
  destination?: "schedule";
};
export const operationScope = {
  repair:
    "Repair runs the full workflow for managed tools, workspace/editor configuration, and weekly maintenance. It can change settings for other checks as well.",
  update:
    "Update refreshes the managed development-tool set within the approved runtime families. SDE application updates have a separate maintenance policy.",
};
const repair = (title: string, impact: string): Guidance => ({
  title,
  impact,
  next: "Review Repair to restore the managed setup, then run validation again. If the check still fails, keep the diagnostic details and create a support report.",
  category: "Repair",
  operation: "repair",
});
const diagnostics = (title: string, impact: string, next: string): Guidance => ({
  title,
  impact,
  next,
  category: "Diagnostic review",
});
const manual = (title: string, impact: string, next: string): Guidance => ({
  title,
  impact,
  next,
  category: "Manual step",
});
const extensions = new Set([
  "dbaeumer.vscode-eslint",
  "esbenp.prettier-vscode",
  "editorconfig.editorconfig",
  "usernamehw.errorlens",
  "streetsidesoftware.code-spell-checker",
  "humao.rest-client",
  "mhutchie.git-graph",
  "vitest.explorer",
]);
const tools =
  "Git|GitHub CLI|Node\\.js|npm|Python(?: 3\\.14)?|pip|VSCodium|DBeaver|PyCharm|Chrome|Firefox|PowerShell 7|OpenSSH|7-Zip";
const missingTool = new RegExp(`^(${tools})(?:: not installed| not found)$`);
const runtimeFailure = new RegExp(
  `^(${tools}): expected runtime family or usable command; detected `,
);

/** Recognize messages narrowly; unknown checks offer diagnostics, not inferred repairs. */
export function validationGuidance(
  check: Check,
  record?: ToolRecord,
  supported = true,
): Guidance | undefined {
  if (check.status === "INFO") return;
  if (check.status === "PASS") {
    if (
      supported &&
      record?.updateAvailable &&
      record.updateCheck === "current" &&
      record.tool === toolForCheck(check)
    ) {
      return {
        title: `Managed update available for ${record.tool}`,
        impact:
          "This tool passed validation. A newer managed version is available.",
        next: "Review Update if you want to refresh the managed tools, then validate again.",
        category: "Update",
        operation: "update",
      };
    }
    return;
  }
  if (!supported)
    return diagnostics(
      "This platform needs verification",
      "SDE has not confirmed a supported workstation platform.",
      "Check the operating-system information against SDE's supported platforms before setup or maintenance. Keep the details in a support report if it cannot be verified.",
    );
  const message = check.message;
  const match = missingTool.exec(message);
  if (
    check.status === "FAIL" &&
    (match || message === "Google Chrome not found")
  ) {
    const name = match?.[1] ?? "Chrome";
    return repair(
      `${name} could not be found`,
      `The ${name} check did not find the required managed tool. Work that depends on it may be blocked.`,
    );
  }
  if (
    check.status === "FAIL" &&
    (runtimeFailure.test(message) ||
      /^Node\.js must remain on 24\.x; detected /.test(message) ||
      /^Expected Python 3\.14\.x; detected /.test(message))
  ) {
    return diagnostics(
      "A required command or runtime could not be verified",
      "The command did not run as expected or the required runtime family was not detected. Managed projects may not run correctly.",
      "Review the detected version and command path in Technical details. Preserve Linux system Python and existing project environments. Keep a support report before choosing a repair; do not infer a package change from this message alone.",
    );
  }
  if (
    check.status === "FAIL" &&
    message === "Python 3.14 could not create a venv with pip"
  )
    return repair(
      "Python project environments are not ready",
      "SDE could not create an isolated Python environment with pip. Python projects may be unable to install their dependencies.",
    );
  if (
    check.status === "FAIL" &&
    (message === "Development folder" ||
      /^Development workspace missing: .+/.test(message))
  )
    return repair(
      "The development workspace could not be found",
      "The standard location for student projects was not found. Existing projects may be stored elsewhere.",
    );
  if (
    check.status === "FAIL" &&
    (message === "VSCodium settings present" ||
      /^VSCodium settings file missing: .+/.test(message))
  )
    return repair(
      "Editor setup is incomplete",
      "SDE could not find the editor settings file. The standard editing defaults may be unavailable.",
    );
  const extension =
    /^(?:Editor extension: |VSCodium extension missing: )(.+)$/.exec(
      message,
    )?.[1];
  if (
    check.status === "FAIL" &&
    extension &&
    extensions.has(extension.toLowerCase())
  )
    return repair(
      `An editor extension is missing: ${extension}`,
      "A standard editor feature may be unavailable until the extension is installed.",
    );
  if (
    check.status === "FAIL" &&
    message === "Managed PyCharm installation/symlink is missing"
  )
    return repair(
      "The managed PyCharm installation is unavailable",
      "The approved PyCharm launcher could not be verified. Python IDE work may be blocked.",
    );
  if (
    check.status === "FAIL" &&
    ["Windows long paths enabled", "Windows developer mode enabled"].includes(
      message,
    )
  )
    return repair(
      "A Windows development setting needs attention",
      "A required Windows or File Explorer setting did not match the development baseline.",
    );
  if (check.status === "FAIL" && message === "File extensions visible")
    return manual(
      "File-name visibility could not be verified",
      "Hidden file extensions can make it difficult to recognize project file types.",
      "In File Explorer, choose View > Show > File name extensions, then validate again.",
    );
  const gitDefaults: Record<string, string> = {
    "Git default init.defaultBranch = main":
      "Use main as the default branch for new repositories.",
    "Git init.defaultBranch is not main":
      "Use main as the default branch for new repositories.",
    "Git default fetch.prune = true":
      "Enable pruning of obsolete remote references when fetching.",
    "Git fetch.prune is not true":
      "Enable pruning of obsolete remote references when fetching.",
    "Git default pull.ff = only":
      "Use fast-forward-only pulls to avoid unexpected merge commits.",
    "Git pull.ff is not only":
      "Use fast-forward-only pulls to avoid unexpected merge commits.",
  };
  if (check.status === "FAIL" && Object.hasOwn(gitDefaults, message))
    return manual(
      "A Git default differs from the baseline",
      "The standard Git workflow settings were not verified. Repository operations may behave differently from course instructions.",
      `${gitDefaults[message]} Review the global setting before changing an intentional customization, then validate again. Git identity remains optional.`,
    );
  if (/^Weekly maintenance/.test(message))
    return {
      ...diagnostics(
        "Weekly maintenance needs review",
        "SDE could not confirm that the managed maintenance schedule is available and enabled. Automatic tool maintenance may be affected.",
        "Open Schedule to review the task or timer and its last result. Check whether it was intentionally disabled before choosing Repair or changing the schedule.",
      ),
      destination: "schedule",
    };
  if (
    /^(?:Configured repository: |Configured repository missing: )/.test(
      message,
    ) &&
    check.status === "FAIL"
  )
    return diagnostics(
      "A configured project could not be verified",
      "The configured project folder was not recognized as a Git repository. This check does not establish whether your work is missing.",
      "Confirm the configured repository, its location, and your access against the project setup instructions. Preserve existing folders and keep the diagnostic details if access remains unavailable.",
    );
  if (
    message.startsWith("Expected Linux Mint; detected ") ||
    message === "/etc/os-release is unavailable"
  )
    return diagnostics(
      "The supported Linux platform could not be confirmed",
      "SDE could not verify Linux Mint. Provisioning on an unsupported system may be unsafe.",
      "Confirm the operating system against SDE's supported-platform requirements before changing packages or system settings. Save a support report if it cannot be verified.",
    );
  if (
    check.status === "WARNING" &&
    message === "Cinnamon desktop session not detected in this shell"
  )
    return manual(
      "The desktop session could not be confirmed",
      "This warning does not count as a failed check. Desktop-specific behavior has not been verified in this session.",
      "Open SDE from your Cinnamon desktop and validate again. If you are already using Cinnamon, keep the session details in a support report.",
    );
  if (
    check.status === "WARNING" &&
    message ===
      "Could not verify all VSCodium baseline settings (file may contain JSONC or user customizations)"
  )
    return manual(
      "Some editor defaults could not be verified",
      "Existing editor customizations or comments may prevent this check. Your preferences have been preserved.",
      "Compare the editor settings with the installed baseline. Preserve intentional customizations, then validate again.",
    );
  if (
    check.status === "WARNING" &&
    message === "Tool version and update metadata is unavailable"
  )
    return manual(
      "Tool update availability could not be checked",
      "Installed-tool checks still apply, but this attempt did not establish which managed updates are available.",
      "Check your connection and try validation with managed package update inspection enabled under Advanced. Keep the details in a support report if the warning persists.",
    );
  return diagnostics(
    "This check needs diagnostic review",
    check.status === "FAIL"
      ? "SDE could not confirm this requirement. Workstation readiness cannot be fully verified."
      : "A validation warning needs review. It does not count as a failed check.",
    "Expand Technical details and save a support report. Do not treat unknown diagnostic text as a command or infer a repair from it. Recheck after reviewing the documented setup requirements.",
  );
}
