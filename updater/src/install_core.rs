//! Shared application installation state machine. No discovery, tools, privilege
//! launch, locks acquisition, package command or caller-supplied executor here.
//! Native backends retain the platform trust/installer/postcheck implementation.
use crate::{observation::Phase, Result};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Scope {
    ScheduledMaintenance,
    AppOnly,
}

/// Scheduled callers preserve their existing tool-result handling. An app-only
/// request never invokes the callback, including on error paths.
pub(crate) fn tools_for(
    scope: Scope,
    tools: impl FnOnce() -> Result<Option<i32>>,
) -> Result<Option<i32>> {
    match scope {
        Scope::ScheduledMaintenance => tools(),
        Scope::AppOnly => Ok(None),
    }
}

pub(crate) trait Journal {
    fn complete(self) -> Result<()>;
}
impl Journal for sde_coordination::Transaction<'_> {
    fn complete(self) -> Result<()> {
        sde_coordination::Transaction::complete(self).map_err(|e| e.to_string())
    }
}

/// Only production implementation is an already-held Installation. The generic
/// boundary permits memory-only ownership/journal fakes in local unit checks.
pub(crate) trait Ownership {
    type Intent<'a>: Journal
    where
        Self: 'a;
    fn begin(&self) -> Result<Self::Intent<'_>>;
}
impl Ownership for sde_coordination::Installation {
    type Intent<'a> = sde_coordination::Transaction<'a>;
    fn begin(&self) -> Result<Self::Intent<'_>> {
        self.begin_transaction().map_err(|e| e.to_string())
    }
}

/// Borrowing keeps the caller's installation lease alive through all native
/// work and postchecks. Construction does not acquire/release/reenter a gate.
/// Authorization/admission/capability/deadline checks belong to the later worker;
/// this internal context is NOT an authorization receipt or a public API.
pub(crate) struct Context<'a, O: Ownership = sde_coordination::Installation> {
    owner: &'a O,
    scope: Scope,
}
impl<'a> Context<'a> {
    pub(crate) fn scope(&self) -> Scope {
        self.scope
    }
    pub(crate) fn scheduled(owner: &'a sde_coordination::Installation) -> Self {
        Self {
            owner,
            scope: Scope::ScheduledMaintenance,
        }
    }
    #[allow(dead_code)] // Internal app-only caller is added in a later authorized phase.
    pub(crate) fn app_only(owner: &'a sde_coordination::Installation) -> Self {
        Self {
            owner,
            scope: Scope::AppOnly,
        }
    }
}

/// No tool-maintenance hook exists in the installation backend. Verification
/// returns a typed value retained through intent/launch; scope cannot skip it.
pub(crate) trait Backend {
    type Verified;
    fn target_version(&self) -> &str;
    fn phase(&mut self, phase: Phase);
    fn paused(&mut self) -> Result<bool>;
    fn installed_version(&mut self) -> Result<String>;
    fn mark_paused(&mut self);
    fn record_paused_intent(&mut self) -> Result<()>;
    fn mark_current(&mut self);
    fn mark_failed(&mut self);
    fn authenticate(&mut self) -> Result<Self::Verified>;
    /// false means a platform-specific safe deferral, already recorded.
    fn preflight(&mut self, verified: &Self::Verified) -> Result<bool>;
    fn record_intent(&mut self, before: &str, verified: &Self::Verified) -> Result<()>;
    fn launch(&mut self) -> Result<i32>;
    /// Record actual exit/reboot and reject non-success, preserving the journal.
    fn native_finished(&mut self, before: &str, code: i32) -> Result<()>;
    fn postcheck(&mut self) -> Result<()>;
    fn record_success(&mut self, before: &str, code: i32) -> Result<()>;
    fn mark_updated(&mut self);
}

pub(crate) fn install<O: Ownership, B: Backend>(
    context: Context<'_, O>,
    backend: &mut B,
) -> Result<()> {
    backend.phase(Phase::Verification);
    if backend.paused()? {
        backend.mark_paused();
        return Ok(());
    }
    let before = backend.installed_version()?;
    if semver::Version::parse(backend.target_version()).map_err(|_| "Invalid candidate")?
        <= semver::Version::parse(&before).map_err(|_| "Invalid installed version")?
    {
        backend.mark_current();
        return Ok(());
    }
    backend.mark_failed();
    let verified = backend.authenticate()?;
    if !backend.preflight(&verified)? {
        return Ok(());
    }
    // Preserve scheduled maintenance's existing post-intent pause handling.
    // Manual app-only commitment instead performs the approved final policy read
    // before intent. No network/user interaction is allowed past this boundary.
    if context.scope == Scope::AppOnly && backend.paused()? {
        backend.mark_paused();
        return Ok(());
    }
    let journal = context.owner.begin()?;
    backend.record_intent(&before, &verified)?;
    if context.scope == Scope::ScheduledMaintenance && backend.paused()? {
        backend.record_paused_intent()?;
        journal.complete()?;
        backend.mark_paused();
        return Ok(());
    }
    backend.phase(Phase::Installer);
    let code = backend.launch()?;
    backend.native_finished(&before, code)?;
    backend.phase(Phase::Postcheck);
    backend.postcheck()?;
    backend.record_success(&before, code)?;
    journal.complete()?;
    backend.mark_updated();
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{cell::RefCell, collections::VecDeque, rc::Rc};

    #[derive(Default)]
    struct State {
        events: Vec<String>,
        intent: bool,
        fail_begin: bool,
        fail_complete: bool,
    }
    type Shared = Rc<RefCell<State>>;
    struct Owner(Shared);
    struct Intent(Shared);
    impl Ownership for Owner {
        type Intent<'a> = Intent;
        fn begin(&self) -> Result<Intent> {
            let mut state = self.0.borrow_mut();
            state.events.push("begin".into());
            // Model uncertain publication: even an error may leave intent.
            state.intent = true;
            if state.fail_begin { return Err("begin uncertain".into()); }
            Ok(Intent(self.0.clone()))
        }
    }
    impl Journal for Intent {
        fn complete(self) -> Result<()> {
            let mut state = self.0.borrow_mut();
            state.events.push("complete".into());
            if state.fail_complete { return Err("complete uncertain".into()); }
            state.intent = false;
            Ok(())
        }
    }
    // Drop deliberately never clears intent; mirrors production Transaction.
    struct Verified(&'static str);
    struct Fake {
        state: Shared,
        target: String,
        installed: String,
        policy: VecDeque<bool>,
        policy_reads: usize,
        fail_policy_read: Option<usize>,
        fail: Option<&'static str>,
        busy: bool,
        code: i32,
        outcome: &'static str,
    }
    impl Fake {
        fn new(state: Shared) -> Self {
            Self { state, target: "1.2.10".into(), installed: "1.2.9".into(),
                policy: VecDeque::from([false,false]), policy_reads: 0, fail_policy_read: None, fail: None, busy: false,
                code: 0, outcome: "unavailable" }
        }
        fn step(&mut self, name: &'static str) -> Result<()> {
            self.state.borrow_mut().events.push(name.into());
            if self.fail == Some(name) { Err(name.into()) } else { Ok(()) }
        }
    }
    impl Backend for Fake {
        type Verified = Verified;
        fn target_version(&self) -> &str {
            &self.target
        }
        fn phase(&mut self, phase: Phase) { self.state.borrow_mut().events.push(format!("phase:{phase:?}")); }
        fn paused(&mut self) -> Result<bool> {
            self.step("policy")?;
            self.policy_reads += 1;
            if self.fail_policy_read == Some(self.policy_reads) {
                return Err("policy read failed".into());
            }
            Ok(self.policy.pop_front().expect("unexpected extra policy read"))
        }
        fn installed_version(&mut self) -> Result<String> {
            self.step("identity")?; Ok(self.installed.clone())
        }
        fn mark_paused(&mut self) {
            self.outcome = "paused";
        }
        fn record_paused_intent(&mut self) -> Result<()> {
            self.step("paused-intent")
        }
        fn mark_current(&mut self) {
            self.outcome = "current";
        }
        fn mark_failed(&mut self) {
            self.outcome = "failed";
        }
        fn authenticate(&mut self) -> Result<Verified> {
            self.step("authenticate")?; Ok(Verified("signed-bytes"))
        }
        fn preflight(&mut self, verified: &Verified) -> Result<bool> {
            assert_eq!(verified.0,"signed-bytes");
            self.step("preflight")?;
            if self.busy { self.outcome = "deferred"; }
            Ok(!self.busy)
        }
        fn record_intent(&mut self, before: &str, verified: &Verified) -> Result<()> {
            assert_eq!(before,"1.2.9"); assert_eq!(verified.0,"signed-bytes"); self.step("record-intent")
        }
        fn launch(&mut self) -> Result<i32> {
            self.step("launch")?; Ok(self.code)
        }
        fn native_finished(&mut self, before: &str, code: i32) -> Result<()> {
            assert_eq!(before,"1.2.9"); self.step("native-result")?;
            if code != 0 { return Err(format!("native exit {code}")); }
            Ok(())
        }
        fn postcheck(&mut self) -> Result<()> {
            self.step("postcheck")
        }
        fn record_success(&mut self, before: &str, code: i32) -> Result<()> {
            assert_eq!(before,"1.2.9"); assert_eq!(code,0); self.step("success-receipt")
        }
        fn mark_updated(&mut self) {
            self.state.borrow_mut().events.push("updated".into()); self.outcome = "updated";
        }
    }
    fn fixture() -> (Shared, Owner, Fake) {
        let state = Shared::default();
        (state.clone(),Owner(state.clone()),Fake::new(state))
    }
    fn run(scope: Scope, owner: &Owner, backend: &mut Fake) -> Result<()> {
        install(Context { owner, scope }, backend)
    }
    const SCOPES: [Scope;2] = [Scope::ScheduledMaintenance,Scope::AppOnly];

    #[test]
    fn app_only_never_calls_tools_even_when_callback_would_fail() {
        assert_eq!(tools_for(Scope::AppOnly,|| panic!("app-only ran tools")).unwrap(),None);
    }
    #[test]
    fn scheduled_tools_keep_exact_result_and_error() {
        for result in [None,Some(0),Some(75),Some(1)] {
            let mut calls = 0;
            assert_eq!(tools_for(Scope::ScheduledMaintenance,|| { calls += 1; Ok(result) }).unwrap(),result);
            assert_eq!(calls,1);
        }
        assert_eq!(tools_for(Scope::ScheduledMaintenance,|| Err("tools failed".into())),Err("tools failed".into()));
    }
    #[test]
    fn both_scopes_use_same_verified_install_and_completion_pipeline() {
        for scope in SCOPES {
            let (state,owner,mut backend) = fixture();
            run(scope,&owner,&mut backend).unwrap();
            assert_eq!(backend.outcome,"updated");
            assert!(!state.borrow().intent);
            let events = &state.borrow().events;
            let phases: Vec<_> = events.iter().filter(|e| e.starts_with("phase:")).map(String::as_str).collect();
            assert_eq!(phases,["phase:Verification","phase:Installer","phase:Postcheck"]);
            let core: Vec<_> = events.iter().filter(|e| !e.starts_with("phase:") && *e != "policy").map(String::as_str).collect();
            assert_eq!(core,["identity","authenticate","preflight","begin","record-intent","launch","native-result","postcheck","success-receipt","complete","updated"]);
            assert_eq!(events.iter().filter(|e| *e == "begin").count(),1);
            assert_eq!(events.iter().filter(|e| *e == "policy").count(),2);
        }
    }
    #[test]
    fn initial_pause_skips_identity_authentication_and_intent() {
        for scope in SCOPES {
            let (state,owner,mut backend) = fixture(); backend.policy = VecDeque::from([true]);
            run(scope,&owner,&mut backend).unwrap();
            assert_eq!(backend.outcome,"paused");
            assert_eq!(state.borrow().events,["phase:Verification","policy"]);
            assert!(!state.borrow().intent);
        }
    }
    #[test]
    fn current_or_downgrade_never_authenticates_or_creates_intent() {
        for scope in SCOPES {
            for version in ["1.2.9","1.2.8"] {
                let (state,owner,mut backend) = fixture(); backend.target = version.into();
                run(scope,&owner,&mut backend).unwrap();
                assert_eq!(backend.outcome,"current");
                assert_eq!(state.borrow().events,["phase:Verification","policy","identity"]);
                assert!(!state.borrow().intent);
            }
        }
    }
    #[test]
    fn malformed_versions_stop_before_authentication() {
        for scope in SCOPES {
            for candidate_bad in [true,false] {
                let (state,owner,mut backend) = fixture();
                if candidate_bad { backend.target = "bad".into(); } else { backend.installed = "bad".into(); }
                assert!(run(scope,&owner,&mut backend).is_err());
                assert!(!state.borrow().intent);
                assert!(!state.borrow().events.iter().any(|e| e == "authenticate"));
            }
        }
    }
    #[test]
    fn preflight_busy_defers_without_intent_or_native_effect() {
        for scope in SCOPES {
            let (state,owner,mut backend) = fixture(); backend.busy = true;
            run(scope,&owner,&mut backend).unwrap();
            assert_eq!(backend.outcome,"deferred");
            assert!(!state.borrow().intent);
            assert!(!state.borrow().events.iter().any(|e| e == "launch"));
        }
    }
    #[test]
    fn app_only_final_pause_is_before_intent() {
        let (state,owner,mut backend) = fixture(); backend.policy = VecDeque::from([false,true]);
        run(Scope::AppOnly,&owner,&mut backend).unwrap();
        assert_eq!(backend.outcome,"paused");
        assert_eq!(state.borrow().events,["phase:Verification","policy","identity","authenticate","preflight","policy"]);
        assert!(!state.borrow().intent);
    }
    #[test]
    fn scheduled_final_pause_preserves_legacy_intent_cleanup_order() {
        let (state,owner,mut backend) = fixture(); backend.policy = VecDeque::from([false,true]);
        run(Scope::ScheduledMaintenance,&owner,&mut backend).unwrap();
        assert_eq!(backend.outcome,"paused");
        let events = &state.borrow().events;
        assert_eq!(&events[events.len()-5..],["begin","record-intent","policy","paused-intent","complete"]);
        assert!(!state.borrow().intent);
    }
    #[test]
    fn app_only_has_no_post_intent_policy_read_or_external_preparation() {
        let (state,owner,mut backend) = fixture();
        run(Scope::AppOnly,&owner,&mut backend).unwrap();
        let events = &state.borrow().events;
        let start = events.iter().position(|e| e == "begin").unwrap();
        assert_eq!(&events[start..start+4],["begin","record-intent","phase:Installer","launch"]);
        assert!(!events[start..].iter().any(|e| ["policy","authenticate","preflight"].contains(&e.as_str())));
    }
    #[test]
    fn pre_intent_failures_stop_both_scopes_without_launch() {
        for scope in SCOPES {
            for failure in ["policy","identity","authenticate","preflight"] {
                let (state,owner,mut backend) = fixture(); backend.fail = Some(failure);
                assert_eq!(run(scope,&owner,&mut backend),Err(failure.into()));
                assert!(!state.borrow().intent);
                assert!(!state.borrow().events.iter().any(|e| e == "launch"));
                assert_ne!(backend.outcome,"updated");
            }
        }
    }
    #[test]
    fn uncertain_begin_retains_intent_and_never_launches() {
        for scope in SCOPES {
            let (state,owner,mut backend) = fixture(); state.borrow_mut().fail_begin = true;
            assert!(run(scope,&owner,&mut backend).is_err());
            assert!(state.borrow().intent);
            assert!(!state.borrow().events.iter().any(|e| e == "launch" || e == "complete"));
        }
    }
    #[test]
    fn every_post_intent_failure_preserves_intent_and_never_marks_updated() {
        for scope in SCOPES {
            for failure in ["record-intent","launch","native-result","postcheck","success-receipt"] {
                let (state,owner,mut backend) = fixture(); backend.fail = Some(failure);
                assert_eq!(run(scope,&owner,&mut backend),Err(failure.into()));
                assert!(state.borrow().intent);
                assert!(!state.borrow().events.iter().any(|e| e == "complete" || e == "updated"));
                assert_eq!(backend.outcome,"failed");
            }
        }
    }
    #[test]
    fn native_non_success_including_reboot_code_never_clears_intent() {
        for scope in SCOPES {
            for code in [1,75,3010] {
                let (state,owner,mut backend) = fixture(); backend.code = code;
                assert!(run(scope,&owner,&mut backend).is_err());
                assert!(state.borrow().intent);
                assert!(!state.borrow().events.iter().any(|e| e == "postcheck" || e == "complete" || e == "updated"));
            }
        }
    }
    #[test]
    fn failed_completion_never_reports_updated_or_repairs_uncertainty() {
        for scope in SCOPES {
            let (state,owner,mut backend) = fixture(); state.borrow_mut().fail_complete = true;
            assert!(run(scope,&owner,&mut backend).is_err());
            assert!(state.borrow().intent);
            assert_eq!(backend.outcome,"failed");
            assert!(!state.borrow().events.iter().any(|e| e == "updated"));
        }
    }
    #[test]
    fn scheduled_paused_cleanup_failure_is_failed_not_paused() {
        let (state,owner,mut backend) = fixture(); backend.policy = VecDeque::from([false,true]);
        state.borrow_mut().fail_complete = true;
        assert!(run(Scope::ScheduledMaintenance,&owner,&mut backend).is_err());
        assert!(state.borrow().intent);
        assert_eq!(backend.outcome,"failed");
    }
    #[test]
    fn final_policy_read_failure_is_before_manual_intent_but_after_scheduled_intent() {
        for scope in SCOPES {
            let (state, owner, mut backend) = fixture();
            backend.fail_policy_read = Some(2);
            assert_eq!(run(scope, &owner, &mut backend), Err("policy read failed".into()));
            let state = state.borrow();
            assert_eq!(state.intent, scope == Scope::ScheduledMaintenance);
            assert!(!state.events.iter().any(|event| event == "launch" || event == "complete"));
            assert_eq!(backend.outcome, "failed");
        }
    }

    #[test]
    fn failed_scheduled_pause_receipt_preserves_intent_without_launch_or_completion() {
        let (state, owner, mut backend) = fixture();
        backend.policy = VecDeque::from([false, true]);
        backend.fail = Some("paused-intent");
        assert_eq!(run(Scope::ScheduledMaintenance, &owner, &mut backend), Err("paused-intent".into()));
        let state = state.borrow();
        assert!(state.intent);
        assert!(!state.events.iter().any(|event| event == "launch" || event == "complete"));
        assert_eq!(backend.outcome, "failed");
    }

    #[test]
    fn app_only_pause_never_uses_the_legacy_paused_receipt_hook() {
        let (state, owner, mut backend) = fixture();
        backend.policy = VecDeque::from([false, true]);
        backend.fail = Some("paused-intent");
        run(Scope::AppOnly, &owner, &mut backend).unwrap();
        assert_eq!(backend.outcome, "paused");
        let state = state.borrow();
        assert!(!state.intent);
        assert!(!state.events.iter().any(|event| event == "paused-intent" || event == "begin"));
    }

}
