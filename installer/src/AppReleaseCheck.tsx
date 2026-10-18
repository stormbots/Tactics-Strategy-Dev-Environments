import { useEffect, useRef, useState } from "react";
import { discoverAppUpdate } from "./bridge";
import type { ReleaseCheck } from "./appUpdate";

export function AppReleaseCheck() {
  const [result, setResult] = useState<ReleaseCheck | null>(null);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [halted, setHalted] = useState(false);
  const [cooling, setCooling] = useState(false);
  const cooldown = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const inFlight = useRef(false);
  const mounted = useRef(false);
  const watchdog = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      clearTimeout(watchdog.current);
      clearTimeout(cooldown.current);
    };
  }, []);
  async function check() {
    if (inFlight.current || cooling || halted) return;
    inFlight.current = true;
    setCooling(true);
    cooldown.current = setTimeout(() => {
      if (mounted.current) setCooling(false);
    }, 30_000);
    setBusy(true);
    setError(false);
    setResult(null);
    let timedOut = false;
    watchdog.current = setTimeout(() => {
      timedOut = true;
      if (mounted.current) {
        setHalted(true);
        setBusy(false);
        setError(true);
      }
    }, 20_000);
    try {
      const value = await discoverAppUpdate();
      if (mounted.current && !timedOut) setResult(value);
    } catch {
      if (mounted.current && !timedOut) setError(true);
    } finally {
      clearTimeout(watchdog.current);
      inFlight.current = false;
      if (mounted.current && !timedOut) setBusy(false);
    }
  }
  return (
    <div>
      <button
        className="secondary"
        disabled={busy || halted || cooling}
        onClick={() => void check()}
      >
        Check SDE release
      </button>
      {cooling && (
        <p className="muted">
          Release checks can be repeated after 30 seconds.
        </p>
      )}
      <p role="status">
        {busy
          ? "Checking official release metadata…"
          : error
            ? "Release metadata could not be verified. No update request was submitted."
            : result?.status === "available"
              ? `Signed metadata verified for SDE ${result.candidate.version}. Installer bytes have not been downloaded or verified. Update Now remains disabled.`
              : result?.status === "no_newer_listing"
                ? "No newer stable release was listed for this window’s app version. This does not verify the installed app or guarantee the latest release."
                : "Check official stable SDE release metadata without downloading an installer. This does not enable Update Now."}
      </p>
    </div>
  );
}
