//! Scheduled tool work only. No scheduler, policy, signature, or elevation route.
//! The caller supplies only its fixed trusted embedded supervisor command.
use sde_coordination::{inspection, mutation, safety::known_backend_completion};
use std::process::Command;

fn detail(error: &mutation::BeginError) -> String {
    serde_json::to_string(error).unwrap_or_else(|_| "Coordination unavailable".into())
}

/// Both scheduled platform drivers must stop before application discovery or
/// installation when applied tool work was deferred or failed.
pub(crate) fn incomplete_outcome(code: Option<i32>) -> Option<&'static str> {
    match code {
        None | Some(0) => None,
        Some(75) => Some("deferred"),
        Some(_) => Some("failed"),
    }
}

pub(crate) fn run(command: Command) -> crate::Result<i32> {
    let mut guard = match mutation::begin(mutation::Scope::System) {
        Ok(guard) => guard,
        Err(error) => {
            // No interactive acknowledgment, automatic override or retry loop.
            // Only sanitized typed findings are logged, never private tokens.
            eprintln!(
                "SKYVIEW_EVENT|warning|deferred|Scheduled tool maintenance deferred: {}",
                detail(&error)
            );
            return Ok(75);
        }
    };
    let status = guard.run(command).map_err(|error| detail(&error))?;
    let facts = inspection::collect();
    if facts.health == sde_coordination::safety::PackageHealth::Unknown {
        eprintln!("SKYVIEW_EVENT|warning|package-health|Native package health remains unverified. Unknown health alone does not override or replace activity and completion checks.");
    }
    if known_backend_completion(status.success(), facts.activity, facts.health) {
        guard.finish_known().map_err(|error| error.to_string())?;
    } else {
        eprintln!("SKYVIEW_EVENT|warning|coordination|Scheduled tool transaction retained: completion or native inactivity was not established. No package process was terminated.");
        if status.success() {
            return Err(
                "Scheduled tool completion remains uncertain; review Recovery and Check Again."
                    .into(),
            );
        }
    }
    Ok(status.code().unwrap_or(1))
}

#[cfg(all(test, any(target_os = "linux", windows)))]
fn await_native_fixture_inactivity(
    budget: std::time::Duration,
    interval: std::time::Duration,
    mut observe: impl FnMut() -> (
        sde_coordination::safety::Activity,
        sde_coordination::safety::PackageHealth,
    ),
) -> Result<(), &'static str> {
    use sde_coordination::safety::{Activity, PackageHealth};
    let started = std::time::Instant::now();
    loop {
        let (activity, health) = observe();
        if health == PackageHealth::Incomplete {
            return Err("Native fixture package state is incomplete");
        }
        match activity {
            Activity::Inactive => return Ok(()),
            Activity::Unknown => return Err("Native fixture package activity is unknown"),
            Activity::Active => {}
        }
        let Some(remaining) = budget.checked_sub(started.elapsed()) else {
            return Err("Native fixture package activity did not become inactive before deadline");
        };
        // Test setup only: never retry a mutation, stop a package process, or
        // turn a timeout into inactivity. Production begin/run still recheck.
        std::thread::sleep(interval.min(remaining));
    }
}

#[cfg(all(test, any(target_os = "linux", windows)))]
pub(crate) fn native_contracts() {
    use sde_coordination as coordination;
    assert_eq!(std::env::var("GITHUB_ACTIONS").as_deref(), Ok("true"));
    // The Windows job has just provisioned real packages. Installer/service
    // processes may still be present after the provisioning wrapper exits.
    // Establish the harmless child's success precondition BEFORE creating any
    // synthetic interruption; consent must never override current activity.
    await_native_fixture_inactivity(
        std::time::Duration::from_secs(15 * 60),
        std::time::Duration::from_secs(10),
        || {
            let facts = inspection::collect();
            eprintln!(
                "Native scheduled-tool fixture setup: {}",
                serde_json::to_string(&facts).unwrap()
            );
            (facts.activity, facts.health)
        },
    )
    .expect("Native scheduled-tool fixture requires independently observed inactivity");
    // Called only by existing native package fixtures after their explicit
    // native-fixture guard. No real package or student data is touched here.
    let root = coordination::root();
    assert!(!root.join("transaction.json").exists());
    let lease = coordination::installation().unwrap();
    drop(lease.begin_transaction().unwrap());
    drop(lease);
    coordination::initialize().unwrap();
    let original = std::fs::read(root.join("transaction.json")).unwrap();
    let incident = coordination::recovery::inspect().unwrap().unwrap();
    let command = || {
        #[cfg(target_os = "linux")]
        {
            Command::new("/usr/bin/true")
        }
        #[cfg(windows)]
        {
            let mut command = Command::new(r"C:\Windows\System32\cmd.exe");
            command.args(["/d", "/c", "exit", "0"]);
            command
        }
    };
    assert_eq!(run(command()).unwrap(), 75);
    assert_eq!(
        std::fs::read(root.join("transaction.json")).unwrap(),
        original
    );
    coordination::recovery::submit(&incident.incident_id).unwrap();
    // Intent alone is not proof the earlier process lifetime has ended.
    assert_eq!(run(command()).unwrap(), 75);
    assert_eq!(
        std::fs::read(root.join("transaction.json")).unwrap(),
        original
    );
    assert!(!root.join("recovery-archive").exists());

    // Simulate *previous* restart provenance only in this disposable synthetic
    // fixture. This does not reboot a host or claim actual reboot/UAT proof.
    let context_path = root.join("recovery-context.json");
    let mut context: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&context_path).unwrap()).unwrap();
    let current = context["bootKey"]
        .as_str()
        .expect("Native restart provenance required");
    #[cfg(target_os = "linux")]
    let previous = {
        assert!(current.starts_with("linux:"));
        format!("linux:{}", uuid::Uuid::new_v4())
    };
    #[cfg(windows)]
    let previous = {
        let values: Vec<u64> = current
            .strip_prefix("windows-session-start:")
            .unwrap()
            .split(':')
            .map(|part| part.parse().unwrap())
            .collect();
        assert_eq!(values.len(), 4);
        format!(
            "windows-session-start:{}:{}:{}:{}",
            values[0] + 1,
            values[1] + 1,
            values[2] + 1,
            values[3] + 1
        )
    };
    assert_ne!(current, previous);
    context["bootKey"] = serde_json::json!(previous);
    std::fs::write(&context_path, serde_json::to_vec(&context).unwrap()).unwrap();
    // Restart proof is not consent either: remove only this synthetic fixture's
    // writable intent and require deferral until it is submitted again.
    std::fs::write(root.join("recovery-acknowledgment.json"), b"{}").unwrap();
    assert_eq!(run(command()).unwrap(), 75);
    assert_eq!(
        std::fs::read(root.join("transaction.json")).unwrap(),
        original
    );
    assert!(!root.join("recovery-archive").exists());
    coordination::recovery::submit(&incident.incident_id).unwrap();
    assert_eq!(run(command()).unwrap(), 0);
    assert!(!root.join("transaction.json").exists());
    for extension in ["journal", "retired-journal"] {
        assert_eq!(
            std::fs::read(
                root.join("recovery-archive")
                    .join(format!("{}.{}", incident.incident_id, extension))
            )
            .unwrap(),
            original
        );
    }
    assert!(root
        .join("recovery-archive")
        .join(format!("{}.receipt.json", incident.incident_id))
        .exists());
    println!("SDE_RECOVERY_SCHEDULED_TOOL_CONTRACT_OK");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fixture_wait_requires_inactivity_and_never_waives_unknown_or_timeout() {
        use sde_coordination::safety::{Activity, PackageHealth};
        use std::time::Duration;
        let mut observations = [Activity::Active, Activity::Inactive].into_iter();
        assert!(
            await_native_fixture_inactivity(Duration::from_secs(1), Duration::ZERO, || {
                (observations.next().unwrap(), PackageHealth::Unknown)
            })
            .is_ok()
        );
        for (activity, health, expected) in [
            (Activity::Active, PackageHealth::Unknown, "deadline"),
            (Activity::Unknown, PackageHealth::Unknown, "unknown"),
            (Activity::Inactive, PackageHealth::Incomplete, "incomplete"),
        ] {
            assert!(
                await_native_fixture_inactivity(Duration::ZERO, Duration::ZERO, || {
                    (activity, health)
                })
                .unwrap_err()
                .contains(expected)
            );
        }
    }
    #[test]
    fn failed_or_deferred_tools_never_authorize_application_work() {
        assert_eq!(incomplete_outcome(None), None);
        assert_eq!(incomplete_outcome(Some(0)), None);
        assert_eq!(incomplete_outcome(Some(75)), Some("deferred"));
        for code in [-1, 1, 23, 3010] {
            assert_eq!(incomplete_outcome(Some(code)), Some("failed"));
        }
    }
}
