//! Read-only Schedule observations. Request/close authority remains disabled.
use serde::Serialize;

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Availability {
    enabled: bool,
    reason: &'static str,
}

pub fn inspect() -> Availability {
    Availability {
        enabled: false,
        reason: "native_validation_pending",
    }
}

#[cfg(target_os = "linux")]
#[path = "app_update_launch.rs"]
mod launch;
const EXECUTION_ENABLED: bool = false;
pub fn request() -> Result<serde_json::Value, &'static str> {
    // Independent backend refusal: a modified/stale GUI cannot bypass this gate.
    // No caller-supplied command, path, candidate, policy or privilege parameters.
    if !EXECUTION_ENABLED {
        return Err("Update Now is unavailable pending native validation and deployment. No request was submitted.");
    }
    #[cfg(target_os = "linux")]
    {
        sde_update_trust::app_only_prerequisites()
            .map_err(|_| "App-only compatibility or recovery prerequisites are not satisfied")?;
        launch::request()
    }
    #[cfg(not(target_os = "linux"))]
    {
        Err("Authorized app-only launch is not supported on this platform yet")
    }
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Discovery {
    status: &'static str,
    candidate: Option<sde_update_trust::notification::VerifiedCandidate>,
}
static DISCOVERY: std::sync::Mutex<Option<std::time::Instant>> = std::sync::Mutex::new(None);
pub fn discover() -> Result<Discovery, &'static str> {
    let platform = if cfg!(target_os = "linux") && cfg!(target_arch = "x86_64") {
        "linux-amd64"
    } else if cfg!(windows) && cfg!(target_arch = "x86_64") {
        "windows-x86_64"
    } else {
        return Err("Unsupported release platform");
    };
    discover_with(&DISCOVERY, || {
        sde_update_trust::notification::discover(env!("CARGO_PKG_VERSION"), platform)
    })
}
fn discover_with(
    admission: &std::sync::Mutex<Option<std::time::Instant>>,
    check: impl FnOnce() -> sde_update_trust::discovery::Result<
        Option<sde_update_trust::notification::VerifiedCandidate>,
    >,
) -> Result<Discovery, &'static str> {
    let mut previous = admission
        .try_lock()
        .map_err(|_| "Release check already running")?;
    if previous.is_some_and(|v| v.elapsed() < std::time::Duration::from_secs(30)) {
        return Err("Wait before checking releases again");
    }
    *previous = Some(std::time::Instant::now());
    let candidate = check().map_err(|_| "Authenticated SDE release metadata unavailable")?;
    Ok(Discovery {
        status: if candidate.is_some() {
            "available"
        } else {
            "no_newer_listing"
        },
        candidate,
    })
}
pub fn progress(id: &str) -> Result<serde_json::Value, &'static str> {
    #[cfg(target_os = "linux")]
    {
        serde_json::to_value(
            sde_update_trust::app_only_observation(id)
                .map_err(|_| "Protected update progress unavailable")?,
        )
        .map_err(|_| "Protected progress encoding unavailable")
    }
    #[cfg(not(target_os = "linux"))]
    {
        let _ = id;
        Err("Protected app-only progress is not supported on this platform yet")
    }
}
pub fn receipt() -> Result<serde_json::Value, &'static str> {
    #[cfg(target_os = "linux")]
    {
        serde_json::to_value(
            sde_update_trust::app_only_current_receipt()
                .map_err(|_| "Protected update receipt unavailable")?,
        )
        .map_err(|_| "Protected receipt encoding unavailable")
    }
    #[cfg(not(target_os = "linux"))]
    {
        Err("Protected app-only receipts are not supported on this platform yet")
    }
}
const CLOSE_ENABLED: bool = false;
pub fn close(id: &str) -> Result<(), &'static str> {
    close_with(CLOSE_ENABLED, || {
        #[cfg(target_os = "linux")]
        {
            sde_update_trust::app_only_check_close(id)
                .map_err(|_| "Protected readiness unavailable; SDE remains open")
        }
        #[cfg(not(target_os = "linux"))]
        {
            let _ = id;
            Err("Protected app-only close is not supported on this platform yet")
        }
    })
}
fn close_with(
    enabled: bool,
    check: impl FnOnce() -> Result<(), &'static str>,
) -> Result<(), &'static str> {
    if !enabled {
        return Err("Close for installation is disabled pending native validation");
    }
    check()
}
/// Native restricted-startup notice only; never constructs a normal GUI without S.
pub fn startup_message() -> &'static str {
    #[cfg(target_os = "linux")]
    if let Ok(Some(_)) = sde_update_trust::app_only_current_receipt() {
        return "SDE admission is closed. A protected update request is recorded, but its receipt does not prove the worker is running or installation succeeded. Reopen later; ask a mentor if this persists. No update was submitted by reopening.";
    }
    "SDE admission is closed by an update or maintenance operation. Please reopen shortly; ask a mentor if this persists."
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn availability_is_disabled_and_serialization_matches_desktop_contract() {
        assert_eq!(
            serde_json::to_value(inspect()).unwrap(),
            serde_json::json!({"enabled": false, "reason": "native_validation_pending"})
        );
    }

    #[test]
    fn discovery_is_single_flight_and_failure_cannot_bypass_cooldown() {
        use sde_update_trust::discovery::Failure;
        let gate = std::sync::Mutex::new(None);
        assert!(discover_with(&gate, || {
            assert!(gate.try_lock().is_err());
            Err(Failure::Offline)
        })
        .is_err());
        assert!(discover_with(&gate, || panic!(
            "cooldown must prevent another provider call"
        ))
        .is_err());
        *gate.lock().unwrap() =
            Some(std::time::Instant::now() - std::time::Duration::from_secs(31));
        assert_eq!(
            discover_with(&gate, || Ok(None)).unwrap().status,
            "no_newer_listing"
        );
    }
    #[test]
    fn malformed_progress_correlation_rejects_before_protected_reads() {
        assert!(progress("../../policy.json").is_err());
    }
    #[test]
    fn close_gate_precedes_reads_and_rechecks_do_not_turn_failure_into_success() {
        assert!(close_with(false, || panic!("disabled gate must precede reads")).is_err());
        assert!(close_with(true, || Err("stale")).is_err());
        assert!(close_with(true, || Ok(())).is_ok());
    }
    #[test]
    fn direct_close_requests_always_refused_without_exiting() {
        for id in [
            "",
            "../../policy.json",
            "00000000-0000-4000-8000-000000000000",
        ] {
            assert!(close(id).is_err());
        }
    }
    #[test]
    fn direct_requests_always_refused() {
        for _ in 0..3 {
            assert!(request().is_err());
            assert!(!inspect().enabled);
        }
    }
}
