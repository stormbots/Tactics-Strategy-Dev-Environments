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

pub fn request() -> Result<(), &'static str> {
    // Independent backend refusal: a modified/stale GUI cannot bypass this gate.
    // No caller-supplied command, path, candidate, policy or privilege parameters.
    Err("Update Now is unavailable pending native validation and deployment. No request was submitted.")
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
pub fn close(_id: &str) -> Result<(), &'static str> {
    // Never exit a GUI or release its S lease based on an observation.
    Err("Close for installation is disabled pending native validation")
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
