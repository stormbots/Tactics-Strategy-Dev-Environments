//! Recovery policy, deliberately separate from evidence collection and execution.
//! An inactive SDE gate alone is NOT an Activity::Inactive observation: native
//! package-process/lock inspection must also have completed before using it.
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Activity {
    Active,
    Inactive,
    Unknown,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum PackageHealth {
    Healthy,
    Incomplete,
    Unknown,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Trust {
    Trusted,
    Untrusted,
    Unknown,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Decision {
    BlockUntrusted,
    BlockTrustUnknown,
    BlockActive,
    BlockActivityUnknown,
    BlockIncomplete,
    NeedsAcknowledgment,
    Allow,
    AllowWithHealthWarning,
}

/// `acknowledged` means a protected, reconciled incident disposition, NOT simply
/// the presence of a writable intent. This decision never grants OS privilege or
/// overrides installation policy, signature/identity checks, or native locks.
pub fn decide(
    trust: Trust,
    activity: Activity,
    health: PackageHealth,
    interrupted: bool,
    acknowledged: bool,
) -> Decision {
    match (trust, activity, health) {
        (Trust::Untrusted, _, _) => Decision::BlockUntrusted,
        (Trust::Unknown, _, _) => Decision::BlockTrustUnknown,
        (_, Activity::Active, _) => Decision::BlockActive,
        (_, Activity::Unknown, _) => Decision::BlockActivityUnknown,
        (_, _, PackageHealth::Incomplete) => Decision::BlockIncomplete,
        _ if interrupted && !acknowledged => Decision::NeedsAcknowledgment,
        (_, _, PackageHealth::Unknown) => Decision::AllowWithHealthWarning,
        _ => Decision::Allow,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_policy_combinations_keep_safety_independent_of_acknowledgment() {
        for trust in [Trust::Trusted, Trust::Untrusted, Trust::Unknown] {
            for activity in [Activity::Active, Activity::Inactive, Activity::Unknown] {
                for health in [
                    PackageHealth::Healthy,
                    PackageHealth::Incomplete,
                    PackageHealth::Unknown,
                ] {
                    for interrupted in [false, true] {
                        for acknowledged in [false, true] {
                            let result = decide(trust, activity, health, interrupted, acknowledged);
                            let permits = matches!(
                                result,
                                Decision::Allow | Decision::AllowWithHealthWarning
                            );
                            assert_eq!(
                                permits,
                                trust == Trust::Trusted
                                    && activity == Activity::Inactive
                                    && health != PackageHealth::Incomplete
                                    && (!interrupted || acknowledged)
                            );
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn unknown_health_is_a_warning_only_when_activity_is_known_inactive() {
        assert_eq!(
            decide(
                Trust::Trusted,
                Activity::Inactive,
                PackageHealth::Unknown,
                true,
                true
            ),
            Decision::AllowWithHealthWarning
        );
        assert_eq!(
            decide(
                Trust::Trusted,
                Activity::Unknown,
                PackageHealth::Unknown,
                true,
                true
            ),
            Decision::BlockActivityUnknown
        );
        assert_eq!(
            decide(
                Trust::Trusted,
                Activity::Active,
                PackageHealth::Unknown,
                true,
                true
            ),
            Decision::BlockActive
        );
    }
}
