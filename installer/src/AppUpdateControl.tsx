import { AppReleaseCheck } from "./AppReleaseCheck";
import { AppUpdateProgress } from "./AppUpdateProgress";
import { useEffect, useRef, useState } from "react";
import {
  inspectAppUpdate,
  inspectAppUpdateReceipt,
  requestAppUpdate,
} from "./bridge";
import { unavailableAppUpdate, type AppUpdateAvailability } from "./appUpdate";

/** Initial disabled integration. Consent is exercised only with mocked
 * eligibility; the real bridge and backend independently refuse enablement. */
export function AppUpdateControl({ requestId }: { requestId?: string } = {}) {
  const [availability, setAvailability] =
    useState<AppUpdateAvailability | null>(null);
  const [phase, setPhase] = useState<
    "idle" | "consent" | "authorizing" | "blocked"
  >("idle");
  const [receipt, setReceipt] = useState<
    import("./appUpdate").RequestReceipt | null
  >(null);
  const [receiptStatus, setReceiptStatus] = useState<
    "loading" | "known" | "unknown"
  >("loading");
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
    let active = true;
    const deadline = setTimeout(() => {
      active = false;
      setReceiptStatus("unknown");
    }, 5000);
    void inspectAppUpdateReceipt().then(
      (value) => {
        if (active && !inFlight.current) {
          clearTimeout(deadline);
          setReceipt(value);
          setReceiptStatus("known");
        }
      },
      () => {
        if (active) {
          clearTimeout(deadline);
          setReceiptStatus("unknown");
        }
      },
    );
    return () => {
      active = false;
      clearTimeout(deadline);
    };
  }, []);
  useEffect(() => {
    if (phase === "consent") confirmHeading.current?.focus();
  }, [phase]);
  async function authorize() {
    if (
      !availability?.enabled ||
      receiptStatus !== "known" ||
      receipt !== null ||
      !consent ||
      inFlight.current ||
      phase !== "consent"
    )
      return;
    inFlight.current = true;
    setPhase("authorizing");
    try {
      const accepted = await requestAppUpdate();
      if (mounted.current) setReceipt(accepted);
    } catch {
      // One read-only recovery lookup, never another authorization/worker launch.
      // The existing mount guard discards a late result; no cancellation inferred.
      let timeout: ReturnType<typeof setTimeout> | undefined;
      try {
        const recovered = await Promise.race([
          inspectAppUpdateReceipt(),
          new Promise<never>((_, reject) => {
            timeout = setTimeout(
              () => reject(new Error("Receipt unavailable")),
              5000,
            );
          }),
        ]);
        if (mounted.current) setReceipt(recovered);
      } catch {
        /* Preserve the uncertain outcome and prohibit retries. */
      } finally {
        clearTimeout(timeout);
      }
    } finally {
      if (mounted.current) setPhase("blocked");
      // No automatic retry after an ambiguous authorization outcome.
    }
  }
  const explanation =
    availability === null
      ? "Checking Update Now availability…"
      : availability.enabled
        ? receiptStatus === "known"
          ? "Update SDE only. Development tools and the maintenance schedule are unchanged."
          : receiptStatus === "loading"
            ? "Checking protected request status…"
            : "Protected request status is unavailable. Update Now remains disabled; ask a mentor to inspect it."
        : availability.reason === "preview"
          ? "Update Now is unavailable in browser preview."
          : availability.reason === "native_validation_pending"
            ? "Update Now is not enabled on this installation. Native validation and deployment are pending."
            : "Update Now availability could not be confirmed. No request has been submitted.";
  const correlation = receipt?.requestId ?? requestId;
  if (correlation)
    return (
      <>
        {receipt && (
          <p role="status">
            Protected request recorded ({receipt.status}).
            {receipt.expired
              ? " Its preparation deadline has passed; this does not confirm cancellation."
              : " Acceptance does not confirm readiness or installation."}
          </p>
        )}
        <AppUpdateProgress key={correlation} requestId={correlation} />
      </>
    );
  return (
    <div
      className="app-update-control"
      role="group"
      aria-label="Update SDE now"
    >
      <p id="app-update-availability" role="status">
        {explanation}
      </p>
      {phase === "idle" && <AppReleaseCheck />}
      {phase === "idle" && (
        <button
          ref={updateButton}
          className="secondary"
          disabled={!availability?.enabled || receiptStatus !== "known"}
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
