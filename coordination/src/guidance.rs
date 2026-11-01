//! Read-only self-service explanations. Never an execution permit, parsed
//! command, acknowledgment, repair runner or reason to clear protected state.
use crate::{observations::Observation, safety::Decision};
use serde::Serialize;

#[derive(Clone, Copy)]
pub enum Platform {
    Linux,
    Windows,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Guidance {
    pub code: &'static str,
    pub title: &'static str,
    pub steps: &'static [&'static str],
}

pub fn for_observation(observation: &Observation, platform: Platform) -> Guidance {
    for_decision(observation.decision, platform)
}

fn for_decision(decision: Decision, platform: Platform) -> Guidance {
    let (code, title, steps): (_, _, &'static [&'static str]) = match decision {
        Decision::BlockActive => ("wait_for_activity", "An operation is still active", &[
            "Wait for the current SDE or package operation to finish, then Check Again.",
            "Do not end installer processes, remove package locks, or start a second package operation.",
        ]),
        Decision::BlockActivityUnknown => ("recheck_activity", "Activity could not be established", &[
            "Save your work, use the normal operating-system Restart, then Check Again.",
            "Restart does not certify package health or acknowledge an interruption. A legacy incident may need another Restart after SDE first captures its provenance.",
            "If the check remains unavailable, collect a support report and keep the original evidence. Do not kill processes or remove locks.",
        ]),
        Decision::BlockUntrusted | Decision::BlockTrustUnknown => ("verify_coordination", "Protected coordination state could not be verified", &[
            "Check Again and keep the diagnostic findings. Do not loosen permissions, replace gates, or delete the transaction journal.",
            "If the SDE installation itself is damaged, use its authenticated application installer to repair it. A repair or restart does not acknowledge retained evidence.",
        ]),
        Decision::BlockIncomplete => match platform {
            Platform::Linux => ("review_linux_packages", "Linux package configuration is incomplete", &[
                "Pause SDE application updates. Only after all package activity has finished, inspect sudo dpkg --audit.",
                "Review sudo apt-get --simulate --fix-broken install before accepting any proposed package changes. Never remove locks or use database-force options.",
                "If the audit reports unfinished configuration, sudo dpkg --configure -a is the native completion command. Review its output, run the audit again, then Check Again. These are system-wide changes, not an automatic SDE repair.",
            ]),
            Platform::Windows => ("review_windows_installer", "Windows Installer reports incomplete work", &[
                "Identify the affected installer from its error or log. Wait for all package activity to finish.",
                "Use that application's supported Resume or Repair path. Settings > Apps > Installed apps may offer Modify or Repair; use it only for the affected application. Save work and restart if its installer requests it.",
                "Check Again afterward. Never delete Windows Installer registry state or remove package locks. SDE does not run this repair automatically.",
            ]),
        },
        Decision::NeedsAcknowledgment => ("review_interruption", "Review the interrupted operation", &[
            "Review the interruption and diagnostic findings before choosing whether to acknowledge it. An acknowledgment is not proof that work finished.",
            "SDE must recheck safety and retain normal operating-system authorization before any change. Passing Validation does not acknowledge or clear the interruption.",
        ]),
        Decision::AllowWithHealthWarning => ("health_unverified", "Package health remains unverified", &[
            "Unknown health alone is not evidence of damage. Current activity was established as inactive; normal native safeguards and fresh execution checks still apply.",
            "Validation is diagnostic, not package repair or acknowledgment.",
        ]),
        Decision::Allow => ("recheck_before_change", "No current safety blocker was detected", &[
            "This observation is not an execution permit. SDE rechecks before each change and still requires normal confirmations and operating-system authorization.",
        ]),
    };
    Guidance { code, title, steps }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn guidance_covers_every_decision_without_mentor_or_automatic_mutation() {
        for platform in [Platform::Linux, Platform::Windows] {
            for decision in [
                Decision::BlockActive,
                Decision::BlockActivityUnknown,
                Decision::BlockUntrusted,
                Decision::BlockTrustUnknown,
                Decision::BlockIncomplete,
                Decision::NeedsAcknowledgment,
                Decision::AllowWithHealthWarning,
                Decision::Allow,
            ] {
                let guide = for_decision(decision, platform);
                let encoded = serde_json::to_string(&guide).unwrap();
                assert!(!guide.steps.is_empty() && encoded.len() < 4096);
                assert!(!encoded.to_ascii_lowercase().contains("mentor"));
                assert!(!encoded.contains("transactionToken") && !encoded.contains("bootKey"));
            }
        }
    }
    #[test]
    fn guidance_separates_unknown_activity_unknown_health_and_positive_damage() {
        assert_eq!(
            for_decision(Decision::BlockActivityUnknown, Platform::Linux).code,
            "recheck_activity"
        );
        assert_eq!(
            for_decision(Decision::AllowWithHealthWarning, Platform::Linux).code,
            "health_unverified"
        );
        assert_eq!(
            for_decision(Decision::BlockIncomplete, Platform::Linux).code,
            "review_linux_packages"
        );
        assert_eq!(
            for_decision(Decision::BlockIncomplete, Platform::Windows).code,
            "review_windows_installer"
        );
        let unknown = serde_json::to_string(&for_decision(
            Decision::BlockActivityUnknown,
            Platform::Linux,
        ))
        .unwrap();
        assert!(!unknown.contains("dpkg --configure"));
        assert!(unknown.contains("does not certify package health or acknowledge"));
    }
}
