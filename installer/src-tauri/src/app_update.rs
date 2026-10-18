//! Disabled Schedule integration boundary. No discovery, policy changes, process
//! launch or filesystem access until separately reviewed native enablement.
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
    fn direct_requests_always_refused() {
        for _ in 0..3 {
            assert!(request().is_err());
            assert!(!inspect().enabled);
        }
    }
}
