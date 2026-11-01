//! Evidence collection/decision for the GUI and the future leased mutation path.
pub use crate::recovery::restart::RestartEvidence;
use crate::{
    inspection::{NativeFacts, Reason},
    recovery,
    safety::{self, Activity, Decision, PackageHealth, Trust},
    Error, Result,
};
use serde::Serialize;
use std::{
    path::Path,
    time::{SystemTime, UNIX_EPOCH},
};

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ActivityReason {
    GateBusy,
    PackageActive,
    NativeInspectionUnavailable,
    EarlierProcessLifetimeUnknown,
    RestartEvidenceUnavailable,
    NoPackageActivity,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Observation {
    pub observed_at: u64,
    pub trust: Trust,
    pub activity: Activity,
    pub activity_reason: ActivityReason,
    pub package_health: PackageHealth,
    pub health_reason: Reason,
    pub diagnostics: Vec<crate::inspection::Failure>,
    pub restart: RestartEvidence,
    pub interrupted: bool,
    pub acknowledged: bool,
    pub decision: Decision,
}

/// Non-authoritative read-only UI snapshot. A mutation must collect again under
/// its own lease; there is no deserializable permit or caller-supplied override.
pub fn inspect() -> Observation {
    inspect_at(&crate::root())
}

pub(crate) fn inspect_at(dir: &Path) -> Observation {
    match crate::acquire_at(dir, "operations.gate", false) {
        Ok(_lease) => match recovery::acknowledgment::public_locked(dir)
            .and_then(|ack| collect_locked(dir, ack.is_some(), crate::inspection::collect()))
        {
            Ok(observation) => observation,
            Err(error) => failed(error),
        },
        Err(error) => failed(error),
    }
}

fn failed(error: Error) -> Observation {
    let trust = if error == Error::Untrusted {
        Trust::Untrusted
    } else if error == Error::Busy {
        Trust::Trusted
    } else {
        Trust::Unknown
    };
    let activity = if error == Error::Busy {
        Activity::Active
    } else {
        Activity::Unknown
    };
    let mut observation = from_facts(
        trust,
        activity,
        PackageHealth::Unknown,
        false,
        false,
        RestartEvidence::Unavailable,
    );
    observation.activity_reason = if error == Error::Busy {
        ActivityReason::GateBusy
    } else {
        ActivityReason::NativeInspectionUnavailable
    };
    observation
}

pub(crate) fn collect_locked(
    dir: &Path,
    acknowledged: bool,
    facts: NativeFacts,
) -> Result<Observation> {
    let interrupted = match crate::no_interruption(dir) {
        Ok(()) => false,
        Err(Error::Interrupted) => true,
        Err(error) => return Err(error),
    };
    let restart = if interrupted {
        recovery::restart::evidence_at(dir, facts.boot_key.as_deref())?
    } else {
        RestartEvidence::Unavailable
    };
    let activity = match facts.activity {
        Activity::Inactive if interrupted && restart != RestartEvidence::Confirmed => {
            Activity::Unknown
        }
        activity => activity,
    };
    let mut observation = from_facts(
        Trust::Trusted,
        activity,
        facts.health,
        interrupted,
        acknowledged,
        restart,
    );
    observation.health_reason = facts.health_reason;
    observation.diagnostics = facts.diagnostics;
    observation.activity_reason = match (facts.activity, activity, restart) {
        (Activity::Active, _, _) => ActivityReason::PackageActive,
        (Activity::Unknown, _, _) => ActivityReason::NativeInspectionUnavailable,
        (_, Activity::Unknown, RestartEvidence::SameSession) => {
            ActivityReason::EarlierProcessLifetimeUnknown
        }
        (_, Activity::Unknown, _) => ActivityReason::RestartEvidenceUnavailable,
        _ => ActivityReason::NoPackageActivity,
    };
    Ok(observation)
}

fn from_facts(
    trust: Trust,
    activity: Activity,
    health: PackageHealth,
    interrupted: bool,
    acknowledged: bool,
    restart: RestartEvidence,
) -> Observation {
    Observation {
        observed_at: SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs(),
        trust,
        activity,
        activity_reason: ActivityReason::NativeInspectionUnavailable,
        package_health: health,
        health_reason: Reason::Unavailable,
        diagnostics: Vec::new(),
        restart,
        interrupted,
        acknowledged,
        decision: safety::decide(trust, activity, health, interrupted, acknowledged),
    }
}
