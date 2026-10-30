import { describe, expect, it } from "vitest";
import { validationGuidance } from "./validationGuidance";
import type { Check, ToolRecord } from "./model";
const fail = (message: string): Check => ({ status: "FAIL", message });

describe("backend validation guidance", () => {
  it.each([
    ["Windows", "Git: not installed"],
    ["Windows", "pip: not installed"],
    ["Windows", "Chrome: not installed"],
    ["Windows", "Development folder"],
    ["Windows", "VSCodium settings present"],
    ["Windows", "Editor extension: EditorConfig.EditorConfig"],
    ["Windows", "Windows long paths enabled"],
    ["Windows", "Windows developer mode enabled"],
    ["Mint", "GitHub CLI not found"],
    ["Mint", "Python 3.14 not found"],
    ["Mint", "Google Chrome not found"],
    ["Mint", "Python 3.14 could not create a venv with pip"],
    ["Mint", "Development workspace missing: /home/student/Development"],
    [
      "Mint",
      "VSCodium settings file missing: /home/student/.config/VSCodium/User/settings.json",
    ],
    ["Mint", "VSCodium extension missing: esbenp.prettier-vscode"],
    ["Mint", "Managed PyCharm installation/symlink is missing"],
  ])("%s check offers full Repair review: %s", (_platform, message) => {
    const result = validationGuidance(fail(message));
    expect(result?.operation).toBe("repair");
    expect(result?.title).toBeTruthy();
    expect(result?.impact).toBeTruthy();
    expect(result?.next).toContain("Review Repair");
  });
  it.each([
    "Node.js: expected runtime family or usable command; detected v25.0.0",
    "Python: expected runtime family or usable command; detected Python 3.13.0",
    "Node.js must remain on 24.x; detected v22.0.0",
    "Expected Python 3.14.x; detected Python 3.13.0",
    "Expected Linux Mint; detected Ubuntu",
    "/etc/os-release is unavailable",
    "Configured repository: Robotics",
    "Configured repository missing: /home/student/Development/robotics",
    "Weekly maintenance is disabled. Run Repair to enable it.",
    "Weekly maintenance timer is not active",
    "Weekly maintenance task cannot be read by this account. Run Repair to restore read access.",
  ])(
    "directs runtime/platform/schedule/project uncertainty to diagnostic review: %s",
    (message) => {
      const result = validationGuidance(fail(message));
      expect(result?.category).toBe("Diagnostic review");
      expect(result?.operation).toBeUndefined();
    },
  );
  it.each([
    "Git default init.defaultBranch = main",
    "Git init.defaultBranch is not main",
    "Git default fetch.prune = true",
    "Git fetch.prune is not true",
    "Git default pull.ff = only",
    "Git pull.ff is not only",
    "File extensions visible",
  ])(
    "explains known Git settings without running a broad operation: %s",
    (message) => {
      const result = validationGuidance(fail(message));
      expect(result?.category).toBe("Manual step");
      expect(result?.operation).toBeUndefined();
    },
  );
  it.each([
    "Git identity: not configured (optional)",
    "GitHub authentication: not configured (optional)",
    "Git user identity is intentionally unset",
    "GitHub CLI is installed but intentionally not authenticated",
  ])("leaves optional information informational: %s", (message) => {
    const check: Check = { status: "INFO", message };
    expect(validationGuidance(check)).toBeUndefined();
    expect(check.status).toBe("INFO");
  });
  it("offers Update only for a passing check with matching known update metadata", () => {
    const record: ToolRecord = {
      tool: "Git",
      installedVersion: "2.49.0",
      availableVersion: "2.50.0",
      updateAvailable: true,
      updateCheck: "current",
    };
    expect(
      validationGuidance({ status: "PASS", message: "Git: 2.49.0" }, record)
        ?.operation,
    ).toBe("update");
    expect(
      validationGuidance(fail("Git: unknown error"), record)?.operation,
    ).toBeUndefined();
    expect(
      validationGuidance(
        { status: "PASS", message: "Node.js: v24.0.0" },
        record,
      ),
    ).toBeUndefined();
    expect(
      validationGuidance(
        { status: "PASS", message: "Git: 2.49.0" },
        { ...record, updateCheck: "unavailable" },
      ),
    ).toBeUndefined();
  });
  it.each([
    "Git: unexpected permission problem",
    "Editor extension: unrecognized.extension",
    "VSCodium extension missing: unknown.extension",
    "Future check: unknown failure",
    "<script>alert('example')</script>",
  ])(
    "fails safely to diagnostic review for unknown diagnostics: %s",
    (message) => {
      const result = validationGuidance(fail(message));
      expect(result?.category).toBe("Diagnostic review");
      expect(result?.operation).toBeUndefined();
      expect(result?.next).toContain("Technical details");
    },
  );
  it("never suggests provisioning an unsupported platform", () => {
    expect(
      validationGuidance(fail("Git: not installed"), undefined, false)
        ?.operation,
    ).toBeUndefined();
  });
  it("preserves warnings and supplies manual next steps", () => {
    const check: Check = {
      status: "WARNING",
      message: "Cinnamon desktop session not detected in this shell",
    };
    expect(validationGuidance(check)?.category).toBe("Manual step");
    expect(check.status).toBe("WARNING");
    expect(
      validationGuidance({ status: "WARNING", message: "An unknown warning" })
        ?.impact,
    ).toContain("does not count as a failed check");
  });
});
