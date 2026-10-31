//! Non-authoritative Recovery observations and generation-bound view tokens.
//! No execution, persistence, acknowledgment or deserializable permit lives here.
use crate::{
    recovery_context::UserIncident, recovery_user::Decision as UserDecision,
    user_journal_store::GateActivity,
};
use sde_coordination::{
    observations::{Observation, RestartEvidence},
    recovery::PublicState,
    safety::{self, Activity, Decision, Trust},
};
use serde::Serialize;
use std::sync::Mutex;

#[derive(Default)]
pub struct Views {
    current: Mutex<Option<Binding>>,
}
struct Binding {
    token: String,
    id: String,
    generation: String,
}
impl Views {
    pub fn bind(&self, id: &str, generation: &str) -> Result<String, String> {
        if !canonical(id)
            || generation.len() != 64
            || !generation
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err("Recovery view identity is unavailable.".into());
        }
        let mut current = self
            .current
            .lock()
            .map_err(|_| "Recovery view is unavailable.")?;
        if let Some(binding) = current
            .as_ref()
            .filter(|binding| binding.id == id && binding.generation == generation)
        {
            return Ok(binding.token.clone());
        }
        let token = uuid::Uuid::new_v4().to_string();
        *current = Some(Binding {
            token: token.clone(),
            id: id.into(),
            generation: generation.into(),
        });
        Ok(token)
    }
    pub fn verify(&self, token: &str, id: &str, generation: &str) -> Result<(), String> {
        let current = self
            .current
            .lock()
            .map_err(|_| "Recovery view is unavailable.")?;
        if !canonical(token)
            || !current.as_ref().is_some_and(|binding| {
                binding.token == token && binding.id == id && binding.generation == generation
            })
        {
            return Err(
                "The displayed user incident is stale. Check Again before acknowledging it.".into(),
            );
        }
        Ok(())
    }
}
fn canonical(id: &str) -> bool {
    uuid::Uuid::parse_str(id).is_ok_and(|value| value.to_string() == id)
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Machine {
    pub available: bool,
    pub incident_id: Option<String>,
    pub intent_submitted: bool,
    pub acknowledged_at: Option<u64>,
}
impl Machine {
    pub fn from_public(result: sde_coordination::Result<Option<PublicState>>) -> Self {
        match result {
            Ok(Some(state)) => Self {
                available: true,
                incident_id: Some(state.incident.incident_id),
                intent_submitted: state.intent_submitted,
                acknowledged_at: state.acknowledgment.map(|ack| ack.acknowledged_at),
            },
            Ok(None) => Self {
                available: true,
                incident_id: None,
                intent_submitted: false,
                acknowledged_at: None,
            },
            Err(_) => Self {
                available: false,
                incident_id: None,
                intent_submitted: false,
                acknowledged_at: None,
            },
        }
    }
}
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct User {
    pub observed_at: u64,
    pub available: bool,
    pub incident: Option<UserIncident>,
    pub acknowledgment: Option<UserDecision>,
    pub restart: RestartEvidence,
    pub gate: GateActivity,
    pub view_token: Option<String>,
}
#[derive(Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Readiness {
    Blocked,
    NeedsAcknowledgment,
    ReadyForNativeRecheck,
}
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct State {
    pub native_safety: Observation,
    pub machine: Machine,
    pub user: User,
    pub effective_activity: Activity,
    pub decision: Decision,
    pub readiness: Readiness,
    pub can_acknowledge_machine: bool,
    pub can_acknowledge_user: bool,
    pub guidance: sde_coordination::guidance::Guidance,
}
pub fn assemble(
    native: Observation,
    machine: Machine,
    user: User,
    platform: sde_coordination::guidance::Platform,
) -> State {
    let mut trust = native.trust;
    if (!machine.available || !user.available) && trust != Trust::Untrusted {
        trust = Trust::Unknown;
    }
    let mut activity = native.activity;
    if user.gate == GateActivity::Active {
        activity = Activity::Active;
    } else if user.incident.is_some()
        && (user.gate == GateActivity::Unknown || user.restart != RestartEvidence::Confirmed)
        && activity != Activity::Active
    {
        activity = Activity::Unknown;
    }
    let machine_recorded = machine.available
        && if machine.incident_id.is_some() {
            machine.acknowledged_at.is_some()
        } else {
            !native.interrupted
        };
    let user_recorded = user.available
        && match &user.incident {
            Some(incident) => user
                .acknowledgment
                .as_ref()
                .is_some_and(|ack| ack.incident_id == incident.id),
            None => true,
        };
    // Never pass writable machine intent off as a protected receipt.
    let decision = safety::decide(
        trust,
        activity,
        native.package_health,
        native.interrupted || machine.incident_id.is_some() || user.incident.is_some(),
        machine_recorded && user_recorded,
    );
    let readiness = match decision {
        Decision::Allow | Decision::AllowWithHealthWarning => Readiness::ReadyForNativeRecheck,
        Decision::NeedsAcknowledgment if user_recorded && machine.intent_submitted => {
            Readiness::ReadyForNativeRecheck
        }
        Decision::NeedsAcknowledgment => Readiness::NeedsAcknowledgment,
        _ => Readiness::Blocked,
    };
    // Acknowledgment is a non-authoritative user choice. Unknown activity can
    // still be acknowledged/prepared, but cannot become a request to mutate.
    let can_acknowledge = activity != Activity::Active && trust != Trust::Untrusted;
    let can_acknowledge_machine = can_acknowledge
        && machine.available
        && machine.incident_id.is_some()
        && !machine.intent_submitted
        && machine.acknowledged_at.is_none();
    let can_acknowledge_user = can_acknowledge
        && user.available
        && user.incident.is_some()
        && user.view_token.is_some()
        && user.acknowledgment.is_none();
    let mut guide_observation = native.clone();
    guide_observation.decision = decision;
    let guidance = sde_coordination::guidance::for_observation(&guide_observation, platform);
    State {
        native_safety: native,
        machine,
        user,
        effective_activity: activity,
        decision,
        readiness,
        can_acknowledge_machine,
        can_acknowledge_user,
        guidance,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sde_coordination::{guidance::Platform, inspection::Reason, safety::PackageHealth};
    fn native() -> Observation {
        Observation {
            observed_at: 100,
            trust: Trust::Trusted,
            activity: Activity::Inactive,
            activity_reason: sde_coordination::observations::ActivityReason::NoPackageActivity,
            package_health: PackageHealth::Healthy,
            health_reason: Reason::PackageHealthy,
            diagnostics: vec![],
            restart: RestartEvidence::Unavailable,
            interrupted: false,
            acknowledged: false,
            decision: Decision::Allow,
        }
    }
    fn empty_user() -> User {
        User {
            observed_at: 100,
            available: true,
            incident: None,
            acknowledgment: None,
            restart: RestartEvidence::Unavailable,
            gate: GateActivity::Unknown,
            view_token: None,
        }
    }
    fn machine() -> Machine {
        Machine {
            available: true,
            incident_id: None,
            intent_submitted: false,
            acknowledged_at: None,
        }
    }
    #[test]
    fn recovery_public_source_distinguishes_absence_unavailable_and_submitted_intent() {
        assert!(Machine::from_public(Ok(None)).available);
        assert!(!Machine::from_public(Err(sde_coordination::Error::Unavailable)).available);
        let id = uuid::Uuid::new_v4().to_string();
        let incident =
            serde_json::from_value(serde_json::json!({"schema":1,"incidentId":id})).unwrap();
        let source = Machine::from_public(Ok(Some(PublicState {
            incident,
            intent_submitted: true,
            acknowledgment: None,
        })));
        assert!(source.available && source.intent_submitted);
        assert_eq!(source.incident_id.as_deref(), Some(id.as_str()));
        assert!(source.acknowledged_at.is_none());
    }
    fn user() -> User {
        let id = uuid::Uuid::new_v4().to_string();
        User {
            incident: Some(UserIncident {
                id,
                operation: "update".into(),
                stage: "profile".into(),
                started_at: 10,
                observed_at: 20,
            }),
            restart: RestartEvidence::Confirmed,
            gate: GateActivity::Inactive,
            view_token: Some(uuid::Uuid::new_v4().to_string()),
            ..empty_user()
        }
    }
    #[test]
    fn recovery_views_bind_native_generation_not_just_uuid_and_survive_read_only_refresh() {
        let views = Views::default();
        let id = uuid::Uuid::new_v4().to_string();
        let a = "a".repeat(64);
        let b = "b".repeat(64);
        let first = views.bind(&id, &a).unwrap();
        assert_eq!(views.bind(&id, &a).unwrap(), first);
        assert!(views.verify(&first, &id, &a).is_ok());
        assert!(views.verify(&first, &id, &b).is_err());
        let second = views.bind(&id, &b).unwrap();
        assert_ne!(first, second);
        assert!(views.verify(&first, &id, &b).is_err());
        assert!(Views::default().verify(&second, &id, &b).is_err());
        assert!(views.bind("../journal", &a).is_err());
    }
    #[test]
    fn recovery_absent_account_state_does_not_require_creating_a_gate() {
        let state = assemble(native(), machine(), empty_user(), Platform::Linux);
        assert_eq!(state.readiness, Readiness::ReadyForNativeRecheck);
        assert!(!state.can_acknowledge_user && !state.can_acknowledge_machine);
    }
    #[test]
    fn recovery_user_unknown_lifetime_remains_blocked_even_after_acknowledgment() {
        for restart in [RestartEvidence::SameSession, RestartEvidence::Unavailable] {
            let mut user = user();
            user.restart = restart;
            let id = user.incident.as_ref().unwrap().id.clone();
            user.acknowledgment = Some(UserDecision {
                incident_id: id,
                acknowledged_at: 50,
                report_id: None,
            });
            let state = assemble(native(), machine(), user, Platform::Linux);
            assert_eq!(state.effective_activity, Activity::Unknown);
            assert_eq!(state.readiness, Readiness::Blocked);
        }
    }
    #[test]
    fn recovery_unknown_can_acknowledge_without_becoming_permission_to_request_changes() {
        let mut user = user();
        user.restart = RestartEvidence::Unavailable;
        let state = assemble(native(), machine(), user, Platform::Linux);
        assert!(state.can_acknowledge_user);
        assert_eq!(state.readiness, Readiness::Blocked);
    }
    #[test]
    fn recovery_submitted_machine_intent_is_not_a_protected_receipt() {
        let mut native = native();
        native.interrupted = true;
        native.restart = RestartEvidence::Confirmed;
        let machine = Machine {
            incident_id: Some(uuid::Uuid::new_v4().to_string()),
            intent_submitted: true,
            ..machine()
        };
        let state = assemble(native, machine, empty_user(), Platform::Windows);
        assert_eq!(state.decision, Decision::NeedsAcknowledgment);
        assert_eq!(state.readiness, Readiness::ReadyForNativeRecheck);
        assert!(state.machine.acknowledged_at.is_none());
        assert!(!state.can_acknowledge_machine);
    }
    #[test]
    fn recovery_one_decision_cannot_suppress_the_other_incident() {
        let mut machine = machine();
        machine.incident_id = Some(uuid::Uuid::new_v4().to_string());
        machine.intent_submitted = true;
        let state = assemble(native(), machine, user(), Platform::Windows);
        assert_eq!(state.readiness, Readiness::NeedsAcknowledgment);
        assert!(state.can_acknowledge_user);
    }
    #[test]
    fn recovery_active_unknown_source_or_known_damage_cannot_become_ready() {
        let mut active = user();
        active.gate = GateActivity::Active;
        let state = assemble(native(), machine(), active, Platform::Linux);
        assert_eq!(state.decision, Decision::BlockActive);
        assert!(!state.can_acknowledge_user);
        let mut unavailable = empty_user();
        unavailable.available = false;
        assert_eq!(
            assemble(native(), machine(), unavailable, Platform::Linux).readiness,
            Readiness::Blocked
        );
        let mut facts = native();
        facts.package_health = PackageHealth::Incomplete;
        assert_eq!(
            assemble(facts, machine(), empty_user(), Platform::Linux).decision,
            Decision::BlockIncomplete
        );
        let mut unknown_gate = user();
        unknown_gate.gate = GateActivity::Unknown;
        assert_eq!(
            assemble(native(), machine(), unknown_gate, Platform::Windows).effective_activity,
            Activity::Unknown
        );
    }
    #[test]
    fn recovery_unknown_health_alone_warns_and_snapshot_never_leaks_private_binding() {
        let mut native = native();
        native.package_health = PackageHealth::Unknown;
        let state = assemble(native, machine(), empty_user(), Platform::Linux);
        assert_eq!(state.decision, Decision::AllowWithHealthWarning);
        let json = serde_json::to_string(&state).unwrap();
        for private in ["bootKey", "generation", "transactionToken", "logPath"] {
            assert!(!json.contains(private));
        }
    }
}
