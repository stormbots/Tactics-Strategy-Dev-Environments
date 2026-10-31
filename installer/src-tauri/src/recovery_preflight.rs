//! Read-only machine request admission, never a journal retirement permit.
use sde_coordination::{recovery::PublicState, safety::Decision};

pub enum Admission {
    Ready,
    Warning,
    Blocked,
}
pub fn inspect() -> Admission {
    let before = sde_coordination::recovery::inspect_public_state();
    let native = sde_coordination::observations::inspect();
    let after = sde_coordination::recovery::inspect_public_state();
    let consistent = match (&before, &after) {
        (Ok(None), Ok(None)) => true,
        (Ok(Some(before)), Ok(Some(after))) => {
            before.incident.incident_id == after.incident.incident_id
        }
        _ => false,
    };
    classify(
        native.decision,
        native.interrupted,
        after.ok().flatten().as_ref(),
        consistent,
    )
}
fn classify(
    decision: Decision,
    interrupted: bool,
    public: Option<&PublicState>,
    consistent: bool,
) -> Admission {
    if !consistent {
        return Admission::Blocked;
    }
    match decision {
        Decision::Allow if !interrupted && public.is_none() => Admission::Ready,
        Decision::Allow | Decision::AllowWithHealthWarning => {
            if interrupted && public.is_none() {
                Admission::Blocked
            } else {
                Admission::Warning
            }
        }
        Decision::NeedsAcknowledgment if public.is_some_and(|state| state.intent_submitted) => {
            Admission::Warning
        }
        _ => Admission::Blocked,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn recovery_preflight_submitted_intent_only_admits_fresh_safe_native_recheck() {
        let _: fn() -> Admission = inspect; // Fixed native observer: no caller-supplied permit.
        let public = PublicState {
            incident: serde_json::from_str(
                r#"{"schema":1,"incidentId":"256f7aea-bf4d-4d0f-a73a-68c2b74e258b"}"#,
            )
            .unwrap(),
            intent_submitted: true,
            acknowledgment: None,
        };
        assert!(matches!(
            classify(Decision::NeedsAcknowledgment, true, Some(&public), true),
            Admission::Warning
        ));
        assert!(matches!(
            classify(Decision::NeedsAcknowledgment, true, None, true),
            Admission::Blocked
        ));
        assert!(matches!(
            classify(Decision::NeedsAcknowledgment, true, Some(&public), false),
            Admission::Blocked
        ));
        for decision in [
            Decision::BlockActive,
            Decision::BlockActivityUnknown,
            Decision::BlockIncomplete,
            Decision::BlockTrustUnknown,
            Decision::BlockUntrusted,
        ] {
            assert!(matches!(
                classify(decision, true, Some(&public), true),
                Admission::Blocked
            ));
        }
        let unacknowledged = PublicState {
            intent_submitted: false,
            ..public
        };
        assert!(matches!(
            classify(
                Decision::NeedsAcknowledgment,
                true,
                Some(&unacknowledged),
                true
            ),
            Admission::Blocked
        ));
        assert!(matches!(
            classify(Decision::Allow, false, None, true),
            Admission::Ready
        ));
        assert!(matches!(
            classify(Decision::AllowWithHealthWarning, false, None, true),
            Admission::Warning
        ));
        assert!(matches!(
            classify(Decision::Allow, true, None, true),
            Admission::Blocked
        ));
    }
}
