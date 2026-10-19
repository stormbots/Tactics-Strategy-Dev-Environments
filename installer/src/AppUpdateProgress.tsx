import { useEffect, useState } from "react";
import { inspectAppUpdateProgress } from "./bridge";
import {
  acceptProgress,
  parseUpdateProgress,
  requestIdPattern,
  type UpdateProgress,
} from "./appUpdate";
const labels: Record<UpdateProgress["state"], string> = {
  preparing: "Checking update prerequisites",
  downloading: "Downloading the SDE installer",
  verifying: "Verifying the SDE installer",
  ready: "Ready to install",
  committing: "Committing installation",
  installing: "Installing SDE",
  postchecking: "Checking the installed application",
  current: "No newer eligible update",
  paused: "Paused by administrator",
  deferred: "Update deferred",
  updated: "Update completed",
  recoveryRequired: "Mentor recovery review required",
};
const terminal = (s: UpdateProgress["state"]) =>
  ["current", "paused", "deferred", "updated", "recoveryRequired"].includes(s);
/** Mounted only for an explicitly correlated request, never a URL/storage ID or
 * last maintenance result. Parent keys by ID. No authority derives from polling. */
export function AppUpdateProgress({ requestId }: { requestId: string }) {
  const [view, setView] = useState<{
    data: UpdateProgress;
    received: number;
  } | null>(null);
  const [error, setError] = useState(false);
  const [clock, setClock] = useState(() => performance.now());
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let watchdog: ReturnType<typeof setTimeout> | undefined;
    let previous: UpdateProgress | null = null;
    let snapshot: { data: UpdateProgress; received: number } | null = null;
    let attempts = 0;
    const start = performance.now();
    setView(null);
    setError(false);
    const fail = () => {
      if (active) {
        setView(null);
        setError(true);
        active = false;
        clearInterval(tick);
      }
    };
    const tick = setInterval(() => {
      const time = performance.now();
      setClock(time);
      if (time - start >= 900_000) clearInterval(tick);
    }, 1000);
    async function poll() {
      if (!active) return;
      if (
        !requestIdPattern.test(requestId) ||
        attempts >= 450 ||
        performance.now() - start >= 900_000
      ) {
        fail();
        return;
      }
      attempts++;
      // Read timeout halts polling; it never cancels a worker or clears intent.
      watchdog = setTimeout(fail, 5000);
      try {
        const data = parseUpdateProgress(
          await inspectAppUpdateProgress(requestId),
          requestId,
        );
        if (!active) return;
        if (performance.now() - start >= 900_000) {
          fail();
          return;
        }
        clearTimeout(watchdog);
        previous = acceptProgress(previous, data);
        const received = performance.now();
        if (snapshot && received < snapshot.received) {
          fail();
          return;
        }
        // A cached/same-age reply cannot restart the local freshness window.
        const elapsed = snapshot ? received - snapshot.received : 0;
        const carriedAge = snapshot
          ? Math.max(
              0,
              snapshot.data.ageMs +
                elapsed -
                (data.observedMs - snapshot.data.observedMs),
            )
          : 0;
        const ageMs = Math.max(data.ageMs, carriedAge);
        const remainingMs = snapshot
          ? Math.min(
              data.remainingMs,
              Math.max(0, snapshot.data.remainingMs - elapsed),
            )
          : data.remainingMs;
        const precommit = [
          "preparing",
          "downloading",
          "verifying",
          "ready",
        ].includes(data.state);
        const effective = {
          ...data,
          ageMs,
          remainingMs,
          fresh:
            data.fresh && ageMs <= 10_000 && (!precommit || remainingMs > 0),
        };
        snapshot = { data: effective, received };
        setClock(received);
        setView(snapshot);
        if (!terminal(data.state)) timer = setTimeout(() => void poll(), 2000);
      } catch {
        clearTimeout(watchdog);
        fail();
      }
    }
    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
      clearTimeout(watchdog);
      clearInterval(tick);
    };
  }, [requestId]);
  const visible = view?.data.requestId === requestId ? view : null;
  const elapsed = visible ? Math.max(0, clock - visible.received) : 0;
  const fresh =
    visible &&
    visible.data.fresh &&
    visible.data.ageMs + elapsed <= 10_000 &&
    (!["preparing", "downloading", "verifying", "ready"].includes(
      visible.data.state,
    ) ||
      elapsed < visible.data.remainingMs);
  return (
    <section aria-labelledby="app-update-progress-heading">
      <h3 id="app-update-progress-heading">SDE update progress</h3>
      <p role="status" aria-live="polite" aria-atomic="true">
        {error
          ? "Protected progress is unavailable. This does not mean installation stopped or cancellation succeeded. Ask a mentor to inspect protected status."
          : !visible
            ? "Reading protected update progress…"
            : `Last protected report: ${labels[visible.data.state]}.${fresh ? "" : " This observation is stale or expired; it is not confirmation of a running or completed worker."}`}
      </p>
      {visible?.data.candidateVersion && (
        <p>Reported candidate: SDE {visible.data.candidateVersion}</p>
      )}
      {visible &&
        ["preparing", "downloading", "verifying"].includes(
          visible.data.state,
        ) &&
        fresh && <progress aria-label="SDE update preparation" />}
      {visible?.data.state === "ready" && (
        <>
          <p id="app-update-close-disabled">
            Closing for installation remains disabled pending native validation.
            This report is not permission to close SDE.
          </p>
          <button
            className="secondary"
            disabled
            aria-describedby="app-update-close-disabled"
          >
            Close SDE &amp; install
          </button>
        </>
      )}
      {visible && terminal(visible.data.state) && (
        <p>
          This is an observed outcome, not clearance of a startup or recovery
          barrier.
        </p>
      )}
    </section>
  );
}
