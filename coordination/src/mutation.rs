//! Privileged execution primitive; the installed GUI helper uses this guard.
//! Direct script, scheduled and application-updater integration is separate.
//! Fresh observations and retirement stay under the same handle-owned leases.
use crate::{
    inspection,
    observations::{self, Observation},
    recovery::{self, Acknowledgment, Kind},
    safety::Decision,
    Error, Lease,
};
use serde::Serialize;
use std::{
    io::Write,
    path::{Path, PathBuf},
    process::{Command, ExitStatus, Stdio},
};
use uuid::Uuid;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Scope {
    System,
    Installation,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "snake_case", tag = "kind", content = "detail")]
pub enum BeginError {
    Coordination(Error),
    Safety(Observation),
}

impl From<Error> for BeginError {
    fn from(error: Error) -> Self {
        Self::Coordination(error)
    }
}

pub(crate) struct RetirementPermit<'a> {
    _lease: &'a Lease,
    acknowledgment: &'a Acknowledgment,
}

impl RetirementPermit<'_> {
    pub(crate) fn acknowledgment(&self) -> &Acknowledgment {
        self.acknowledgment
    }
}

/// Owning this guard is not evidence of successful completion. Drop keeps the
/// new journal. Only finish_known(), after the caller proves native completion,
/// clears this guard's own record. No constructor accepts a UI-provided permit.
pub struct Mutation {
    _operation: Lease,
    _session: Lease,
    directory: PathBuf,
    id: String,
    token: String,
    active: bool,
    started: bool,
}

impl std::fmt::Debug for Mutation {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // Never expose the private nesting token in test failures or logs.
        f.debug_struct("Mutation")
            .field("active", &self.active)
            .field("started", &self.started)
            .finish_non_exhaustive()
    }
}

/// Must be called only from the existing normally privileged execution path,
/// after its independent platform/policy/signature/identity eligibility checks.
/// Old operation()/installation() APIs retain their original conservative gate.
pub fn begin(scope: Scope) -> std::result::Result<Mutation, BeginError> {
    prepare(scope)?.begin()
}

/// Holds the ordinary operation/session leases for eligibility, signature and
/// staging checks, without acknowledging/retiring evidence or creating a new
/// transaction. This is NOT permission to execute a system/package mutation.
pub struct Preparation {
    operation: Lease,
    session: Lease,
    directory: PathBuf,
    scope: Scope,
    interrupted: bool,
}

pub fn prepare(scope: Scope) -> crate::Result<Preparation> {
    let preparation = prepare_at(&crate::root(), scope)?;
    if scope == Scope::Installation {
        crate::compatible_maintenance()?;
    }
    Ok(preparation)
}

pub(crate) fn prepare_at(dir: &Path, scope: Scope) -> crate::Result<Preparation> {
    let operation = crate::acquire_at(dir, "operations.gate", false)?;
    let session = crate::acquire_at(dir, "sessions.gate", scope == Scope::System)?;
    let interrupted = match crate::no_interruption(dir) {
        Ok(()) => false,
        Err(Error::Interrupted) => {
            // Validate protected storage without publishing or changing it.
            recovery::read_journal(dir)?;
            true
        }
        Err(error) => return Err(error),
    };
    Ok(Preparation {
        operation,
        session,
        directory: dir.into(),
        scope,
        interrupted,
    })
}

impl Preparation {
    /// Non-authoritative snapshot under these leases. Never prune older staging
    /// while an uncertain installation might still need its original inputs.
    pub fn interrupted(&self) -> bool {
        self.interrupted
    }

    /// Called only after the trusted caller has established all independent
    /// installation eligibility. Reuses both leases with no release/reacquire
    /// gap; fresh native checks and actual durable consent are still mandatory.
    pub fn begin(self) -> std::result::Result<Mutation, BeginError> {
        self.begin_with_probe(inspection::collect)
    }

    pub(crate) fn begin_with_probe(
        self,
        probe: impl FnMut() -> inspection::NativeFacts,
    ) -> std::result::Result<Mutation, BeginError> {
        begin_leased_at(
            &self.directory,
            self.scope,
            self.operation,
            self.session,
            probe,
        )
    }
}

fn allowed(observation: &Observation) -> bool {
    matches!(
        observation.decision,
        Decision::Allow | Decision::AllowWithHealthWarning
    )
}

pub(crate) fn begin_at(
    dir: &Path,
    scope: Scope,
    probe: impl FnMut() -> inspection::NativeFacts,
) -> std::result::Result<Mutation, BeginError> {
    prepare_at(dir, scope)?.begin_with_probe(probe)
}

fn begin_leased_at(
    dir: &Path,
    scope: Scope,
    operation: Lease,
    session: Lease,
    mut probe: impl FnMut() -> inspection::NativeFacts,
) -> std::result::Result<Mutation, BeginError> {
    let interrupted = match crate::no_interruption(dir) {
        Ok(()) => false,
        Err(Error::Interrupted) => true,
        Err(error) => return Err(error.into()),
    };
    if interrupted {
        recovery::prepare_locked(dir)?;
        let first = observations::collect_locked(dir, true, probe())?;
        // Passing true here only asks whether safety would permit acknowledgment;
        // it never substitutes for validating/committing the actual private receipt.
        if !allowed(&first) {
            return Err(BeginError::Safety(first));
        }
        let acknowledgment =
            recovery::acknowledgment::record_locked(dir, |_| Ok(()))?.ok_or(Error::Interrupted)?;
        // Recheck after persistence I/O, not just before showing the UI or report.
        let final_check = observations::collect_locked(dir, true, probe())?;
        if !allowed(&final_check) {
            return Err(BeginError::Safety(final_check));
        }
        let permit = RetirementPermit {
            _lease: &operation,
            acknowledgment: &acknowledgment,
        };
        recovery::acknowledgment::retire_locked(dir, &permit)?;
    } else {
        let observation = observations::collect_locked(dir, false, probe())?;
        if !allowed(&observation) {
            return Err(BeginError::Safety(observation));
        }
    }
    let id = Uuid::new_v4().to_string();
    let token = Uuid::new_v4().to_string();
    let record = serde_json::json!({"schema":1,"id":id,"token":token,"pid":std::process::id(),
        "kind":if scope == Scope::System {"system"} else {"installation"}});
    let mut file = recovery::open(dir, "transaction.json", Kind::Private, true, true)?;
    file.write_all(record.to_string().as_bytes())
        .and_then(|_| file.sync_all())
        .map_err(|_| Error::Unavailable)?;
    drop(file);
    crate::sync_directory(dir)?;
    recovery::prepare_locked(dir)?;
    Ok(Mutation {
        _operation: operation,
        _session: session,
        directory: dir.into(),
        id,
        token,
        active: true,
        started: false,
    })
}

impl Mutation {
    #[cfg(all(test, unix))]
    pub(crate) fn test_lease_fds(&self) -> [std::os::fd::RawFd; 2] {
        use std::os::fd::AsRawFd;
        [
            self._session._file.as_raw_fd(),
            self._operation._file.as_raw_fd(),
        ]
    }

    fn owns_current(&self) -> crate::Result<()> {
        let (bytes, _) = recovery::read_journal(&self.directory)?.ok_or(Error::Interrupted)?;
        let value: serde_json::Value =
            serde_json::from_slice(&bytes).map_err(|_| Error::Untrusted)?;
        if value.get("schema").and_then(|v| v.as_u64()) != Some(1)
            || value.get("id").and_then(|v| v.as_str()) != Some(self.id.as_str())
            || value.get("token").and_then(|v| v.as_str()) != Some(self.token.as_str())
        {
            return Err(Error::Interrupted);
        }
        Ok(())
    }

    /// One supervised, trusted backend/installer command. Never applies a timeout
    /// or kills package children. Output inherits the caller's existing streaming
    /// log channel. The caller must use fixed approved entry points, not IPC paths.
    pub fn run(&mut self, command: Command) -> std::result::Result<ExitStatus, BeginError> {
        self.run_with_probe(command, inspection::collect)
    }

    /// Trusted synchronous runner adapter, e.g. the installed helper's existing
    /// redacted streaming logger. It must spawn/wait this command, preserve its
    /// real exit status, and never detach/kill package work. This callback is
    /// Rust-only, not an IPC command/path/permit. Completion remains explicit.
    pub fn run_supervised(
        &mut self,
        command: Command,
        runner: impl FnOnce(Command) -> std::io::Result<ExitStatus>,
    ) -> std::result::Result<ExitStatus, BeginError> {
        self.run_using(command, inspection::collect, runner)
    }

    pub(crate) fn run_with_probe(
        &mut self,
        command: Command,
        probe: impl FnOnce() -> inspection::NativeFacts,
    ) -> std::result::Result<ExitStatus, BeginError> {
        self.run_using(command, probe, |mut command| command.status())
    }

    pub(crate) fn run_using(
        &mut self,
        mut command: Command,
        probe: impl FnOnce() -> inspection::NativeFacts,
        runner: impl FnOnce(Command) -> std::io::Result<ExitStatus>,
    ) -> std::result::Result<ExitStatus, BeginError> {
        if !self.active || self.started {
            return Err(Error::Interrupted.into());
        }
        self.owns_current()?;
        // This is our not-yet-started transaction, not an earlier interruption.
        // The fresh native check still blocks external package activity/unknowns.
        let facts = probe();
        let decision = crate::safety::decide(
            crate::safety::Trust::Trusted,
            facts.activity,
            facts.health,
            false,
            false,
        );
        if !matches!(decision, Decision::Allow | Decision::AllowWithHealthWarning) {
            // No child was launched. This known aborted attempt needs no future
            // recovery acknowledgment; the previous incident is already archived.
            self.clear_own()?;
            return Err(BeginError::Coordination(
                if facts.activity == crate::safety::Activity::Active {
                    Error::Busy
                } else {
                    Error::Unavailable
                },
            ));
        }
        command
            .stdin(Stdio::null())
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit());
        #[cfg(windows)]
        command.env("SKYVIEW_TRANSACTION_TOKEN", &self.token);
        #[cfg(unix)]
        {
            use std::os::{fd::AsRawFd, unix::process::CommandExt};
            let session = self._session._file.as_raw_fd();
            let operation = self._operation._file.as_raw_fd();
            command
                .env("SKYVIEW_SESSION_FD", session.to_string())
                .env("SKYVIEW_OPERATION_FD", operation.to_string());
            // Clear CLOEXEC only in the child. No global parent-fd mutation or
            // unrelated-thread inheritance race. Guard borrow covers this wait.
            unsafe {
                command.pre_exec(move || {
                    for fd in [session, operation] {
                        let flags = libc::fcntl(fd, libc::F_GETFD);
                        if flags < 0
                            || libc::fcntl(fd, libc::F_SETFD, flags & !libc::FD_CLOEXEC) < 0
                        {
                            return Err(std::io::Error::last_os_error());
                        }
                    }
                    Ok(())
                });
            }
        }
        self.started = true;
        // Neither a spawn/wait error nor a nonzero/zero exit automatically means
        // native completion. Keep the record until the trusted caller certifies it.
        runner(command).map_err(|_| Error::Unavailable.into())
    }

    fn clear_own(&mut self) -> crate::Result<()> {
        self.owns_current()?;
        std::fs::remove_file(self.directory.join("transaction.json"))
            .map_err(|_| Error::Unavailable)?;
        crate::sync_directory(&self.directory)?;
        self.active = false;
        Ok(())
    }

    /// Explicit known outcome only, after all native children and postchecks are
    /// accounted for. Validation passing or a primary child exit alone is not
    /// sufficient. A failed/unknown attempt drops the guard and retains intent.
    pub fn finish_known(mut self) -> crate::Result<()> {
        self.clear_own()
    }
}
