import { useEffect, useRef, useState } from "react";
import { inspectAppUpdate, requestAppUpdate } from "./bridge";
import { unavailableAppUpdate, type AppUpdateAvailability } from "./appUpdate";

/** Initial disabled integration. Consent is exercised only with mocked
 * eligibility; the real bridge and backend independently refuse enablement. */
export function AppUpdateControl() {
  const [availability, setAvailability] =
    useState<AppUpdateAvailability | null>(null);
  const [phase, setPhase] = useState<
    "idle" | "consent" | "authorizing" | "blocked"
  >("idle");
  const [consent, setConsent] = useState(false);
  const inFlight = useRef(false);
  const mounted = useRef(false);
  const confirmHeading = useRef<HTMLHeadingElement>(null);
  const updateButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    mounted.current = true;
    let active = true;
    void inspectAppUpdate().then(
      (value) => {
        if (active) setAvailability(value);
      },
      () => {
        if (active) setAvailability({ ...unavailableAppUpdate });
      },
    );
    return () => {
      active = false;
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (phase === "consent") confirmHeading.current?.focus();
  }, [phase]);
  async function authorize() {
    if (
      !availability?.enabled ||
      !consent ||
      inFlight.current ||
      phase !== "consent"
    )
      return;
    inFlight.current = true;
    setPhase("authorizing");
    try {
      await requestAppUpdate();
    } catch {
      // Never display raw privilege errors or infer that a worker was cancelled.
    } finally {
      if (mounted.current) setPhase("blocked");
      // No automatic retry after an ambiguous authorization outcome.
    }
  }
  const explanation =
    availability === null
      ? "Checking Update Now availability…"
      : availability.enabled
        ? "Update SDE only. Development tools and the maintenance schedule are unchanged."
        : availability.reason === "preview"
          ? "Update Now is unavailable in browser preview."
          : availability.reason === "native_validation_pending"
            ? "Update Now is not enabled on this installation. Native validation and deployment are pending."
            : "Update Now availability could not be confirmed. No request has been submitted.";
  return (
    <div
      className="app-update-control"
      role="group"
      aria-label="Update SDE now"
    >
      <p id="app-update-availability" role="status">
        {explanation}
      </p>
      {phase === "idle" && (
        <button
          ref={updateButton}
          className="secondary"
          disabled={!availability?.enabled}
          aria-describedby="app-update-availability"
          onClick={() => setPhase("consent")}
        >
          Update Now
        </button>
      )}
      {phase === "consent" && (
        <div role="group" aria-labelledby="app-update-consent-heading">
          <h3
            id="app-update-consent-heading"
            tabIndex={-1}
            ref={confirmHeading}
          >
            Authorize an SDE update
          </h3>
          <p>
            This authorizes one official stable SDE-only update. After system
            approval, preparation continues independently. Closing SDE normally
            or a crash may allow installation; closing the window is not
            cancellation.
          </p>
          <p>
            There is no immediate cancellation after approval. Keeping any SDE
            window open prevents installation until the attempt defers. Before
            installation is committed, the attempt expires after 15 minutes, or
            after 2 minutes waiting for windows to close once ready, whichever
            is earlier.
          </p>
          <p>
            An administrator pause is respected until the final policy check
            before installation is committed. An installation already committed
            is allowed to finish.
          </p>
          <label>
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />{" "}
            I authorize installation under these conditions.
          </label>
          <div className="section-header">
            <button
              className="secondary"
              onClick={() => {
                setConsent(false);
                setPhase("idle");
                requestAnimationFrame(() => updateButton.current?.focus());
              }}
            >
              Back
            </button>
            <button disabled={!consent} onClick={() => void authorize()}>
              Authorize update
            </button>
          </div>
        </div>
      )}
      {phase === "authorizing" && (
        <p role="status">
          Waiting for system authorization. No installation has been confirmed.
        </p>
      )}
      {phase === "blocked" && (
        <p role="status">
          No installation request was confirmed. Ask a mentor to inspect
          protected status before trying again. This message does not confirm
          cancellation of any independent worker.
        </p>
      )}
    </div>
  );
}
