import { invoke } from "@tauri-apps/api/core";
import { native, appVersion } from "./bridge";
import { toolRecord, type ToolRecord } from "./model";
export type AppDiscovery = {
  version: string;
  checkedAt: number;
  candidate: null | {
    tag: string;
    version: string;
    platform: string;
    installer: string;
  };
  failure: string | null;
};
export type ToolPreview = { tools: ToolRecord[]; checkedAt: number };
export type PreflightCheck = {
  name: string;
  status: "pass" | "blocking" | "warning" | "unavailable";
  detail: string;
};
export async function checkApplication(): Promise<AppDiscovery> {
  if (native) return invoke("check_application");
  return {
    version: appVersion,
    checkedAt: Date.now() / 1000,
    candidate: null,
    failure: null,
  };
}
export async function checkTools(snapshot: ToolRecord[]): Promise<ToolPreview> {
  if (!native)
    return {
      tools: snapshot.map((t) => ({
        ...t,
        updateCheck:
          t.updateCheck === "notChecked" ? "unavailable" : t.updateCheck,
      })),
      checkedAt: Date.now() / 1000,
    };
  const result = await invoke<ToolPreview>("check_tools", {
    snapshot: snapshot.map(({ tool, installedVersion }) => ({
      tool,
      installedVersion,
    })),
  });
  if (
    !Array.isArray(result.tools) ||
    result.tools.length > 14 ||
    !Number.isFinite(result.checkedAt)
  )
    throw new Error("Incomplete tool metadata. Refresh preview.");
  const tools = result.tools.map((r) =>
    toolRecord({ kind: "tool", key: r.tool, message: JSON.stringify(r) }),
  );
  if (
    tools.some((t) => !t) ||
    new Set(tools.map((t) => t!.tool)).size !== tools.length
  )
    throw new Error("Incomplete tool metadata. Refresh preview.");
  return { tools: tools as ToolRecord[], checkedAt: result.checkedAt };
}
export async function checkPreflight(): Promise<PreflightCheck[]> {
  return native
    ? invoke("check_update_preflight")
    : [
        {
          name: "Simulated preflight",
          status: "pass",
          detail:
            "Browser preview only. Native preflight runs on the installed workstation.",
        },
      ];
}
export async function openRelease(tag: string | null, installer = false) {
  if (native) return invoke("open_release", { tag, installer });
}
export const failureText: Record<string, string> = {
  offline:
    "GitHub could not be reached within the check deadline. Check your connection and try again.",
  rateLimited:
    "GitHub temporarily limited update checks. Wait before checking again.",
  incomplete:
    "The release listing is incomplete or the newest release lacks compatible assets. View the official releases or try again later.",
  malformed:
    "GitHub release information could not be understood. Try again later or ask a mentor.",
  untrusted:
    "Release information does not match the official download policy. Ask a mentor; do not use an alternate download.",
  unsupported:
    "SDE update checks support Windows 11 x64 and Linux Mint Cinnamon 22.x amd64.",
  invalidInstalled:
    "The running SDE version could not be compared. Ask a mentor.",
};
export function toolExplanation(t: ToolRecord): string {
  if (t.updateReason === "metadataMismatch")
    return "Executable and package versions disagree. Package ownership was not changed; ask a mentor if this persists.";
  if (t.updateCheck === "native")
    return "Managed separately by the application or its runtime.";
  if (t.updateCheck === "notChecked") return "Not checked.";
  if (t.updateCheck === "unavailable")
    return t.updateReason === "timeout"
      ? "Source check timed out. Retry later."
      : "Available version could not be confirmed. Check your connection or ask a mentor; local package metadata may be incomplete.";
  return t.updateAvailable
    ? "Confirmed newer version in the checked source."
    : "No newer version found in the checked source.";
}
