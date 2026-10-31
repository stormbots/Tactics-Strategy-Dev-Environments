//! Native launch evidence only. Neither an exit code nor missing output alone
//! proves a non-start. Never deserialize these variants from the frontend.
#[derive(Debug)]
pub enum Failure {
    NotStarted(String),
    Uncertain(String),
}
impl Failure {
    pub fn message(&self) -> &str {
        match self {
            Self::NotStarted(message) | Self::Uncertain(message) => message,
        }
    }
    pub fn proven_not_started(&self) -> bool {
        matches!(self, Self::NotStarted(_))
    }
}
impl From<String> for Failure {
    fn from(message: String) -> Self {
        Self::Uncertain(message)
    }
}

/// Only for our fixed pkexec -> installed helper contract. The helper must
/// flush its session marker before entering any backend work; capture must have
/// drained both streams reliably and the actual process must have terminated.
#[cfg(any(not(windows), test))]
pub fn polkit_failure(code: i32, helper_entered: bool, capture_complete: bool) -> Failure {
    let message =
        "Administrator authentication was cancelled or denied. Retry explicitly when ready.".into();
    if [126, 127].contains(&code) && !helper_entered && capture_complete {
        Failure::NotStarted(message)
    } else {
        Failure::Uncertain(
            "The privileged helper outcome is uncertain. Keep recovery evidence and Check Again."
                .into(),
        )
    }
}
/// Called only after ShellExecuteExW returned FALSE, never for child exit codes.
#[cfg(any(windows, test))]
pub fn windows_failure(error: u32, process_handle_present: bool) -> Failure {
    if error == 1223 && !process_handle_present {
        Failure::NotStarted(
            "Administrator approval was cancelled. Retry explicitly when ready.".into(),
        )
    } else {
        Failure::Uncertain(
            "The authorization launch could not be confirmed; keep recovery evidence.".into(),
        )
    }
}

#[cfg(any(not(windows), test))]
pub struct HelperCapture {
    expected: String,
    pub entered: bool,
    pub valid: bool,
}
#[cfg(any(not(windows), test))]
impl HelperCapture {
    pub fn new(session: &str) -> Self {
        Self {
            expected: format!("SDE_HELPER_ENTERED|{session}"),
            entered: false,
            valid: true,
        }
    }
    pub fn observe(&mut self, line: &str) -> bool {
        if !line.starts_with("SDE_HELPER_ENTERED|") {
            return false;
        }
        if line == self.expected {
            self.entered = true;
        } else {
            self.valid = false;
        }
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn launch_cancellation_requires_exit_plus_complete_capture_and_no_helper_entry() {
        for code in [0, 1, 75, 126, 127, 1223] {
            for entered in [false, true] {
                for complete in [false, true] {
                    assert_eq!(
                        polkit_failure(code, entered, complete).proven_not_started(),
                        [126, 127].contains(&code) && !entered && complete
                    );
                }
            }
        }
    }
    #[test]
    fn windows_cancellation_is_only_an_os_launch_failure_without_a_process_handle() {
        for error in [0, 5, 87, 1223] {
            for handle in [false, true] {
                assert_eq!(
                    windows_failure(error, handle).proven_not_started(),
                    error == 1223 && !handle
                );
            }
        }
    }
    #[test]
    fn wrong_session_helper_entry_is_uncertain_not_absence_of_execution() {
        let mut capture = HelperCapture::new("expected");
        assert!(capture.observe("SDE_HELPER_ENTERED|different"));
        assert!(!polkit_failure(126, capture.entered, capture.valid).proven_not_started());
        let mut capture = HelperCapture::new("expected");
        assert!(!capture.observe("an ordinary log line"));
        assert!(capture.observe("SDE_HELPER_ENTERED|expected"));
        assert!(!polkit_failure(126, capture.entered, capture.valid).proven_not_started());
    }
    #[test]
    fn ordinary_errors_are_uncertain_not_a_clearance() {
        let error: Failure = "could not confirm completion".to_string().into();
        assert!(!error.proven_not_started());
        assert!(error.message().contains("confirm"));
    }
}
