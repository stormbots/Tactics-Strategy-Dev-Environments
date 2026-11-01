//! Test-only isolation for process creation and live gate fixtures. A foreign
//! fork inherits every open descriptor until exec, including CLOEXEC leases.
//! Intentional child contention remains inside each fixture and is not skipped.
use std::sync::{Mutex, MutexGuard};
static FIXTURES: Mutex<()> = Mutex::new(());
pub fn lock(mutex: &Mutex<()>) -> MutexGuard<'_, ()> {
    mutex
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}
pub fn isolate() -> MutexGuard<'static, ()> {
    lock(&FIXTURES)
}

#[cfg(target_os = "linux")]
#[test]
fn foreign_fork_keeps_a_cloexec_lease_busy_until_exec() {
    use std::{
        fs,
        os::fd::{AsRawFd, FromRawFd, OwnedFd},
    };
    let _isolation = isolate();
    let path = std::env::temp_dir().join(format!("sde-foreign-fork-ci-{}", uuid::Uuid::new_v4()));
    fs::create_dir(&path).unwrap();
    let gate_path = path.join("synthetic.gate");
    let gate = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .create_new(true)
        .open(&gate_path)
        .unwrap();
    assert_ne!(
        unsafe { libc::fcntl(gate.as_raw_fd(), libc::F_GETFD) } & libc::FD_CLOEXEC,
        0
    );
    assert_eq!(
        unsafe { libc::flock(gate.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) },
        0
    );
    fn pipe() -> [OwnedFd; 2] {
        let mut descriptors = [0; 2];
        assert_eq!(
            unsafe { libc::pipe2(descriptors.as_mut_ptr(), libc::O_CLOEXEC) },
            0
        );
        unsafe {
            [
                OwnedFd::from_raw_fd(descriptors[0]),
                OwnedFd::from_raw_fd(descriptors[1]),
            ]
        }
    }
    let ready = pipe();
    let release = pipe();
    let child = unsafe { libc::fork() };
    assert!(child >= 0);
    if child == 0 {
        // The forked multi-threaded child uses only async-signal-safe calls.
        // A bounded handshake prevents a failed parent assertion hanging CI.
        unsafe {
            let mut byte = 1u8;
            if libc::write(ready[1].as_raw_fd(), (&byte as *const u8).cast(), 1) != 1 {
                libc::_exit(2);
            }
            let mut event = libc::pollfd {
                fd: release[0].as_raw_fd(),
                events: libc::POLLIN,
                revents: 0,
            };
            if libc::poll(&mut event, 1, 5000) != 1
                || libc::read(release[0].as_raw_fd(), (&mut byte as *mut u8).cast(), 1) != 1
            {
                libc::_exit(3);
            }
            libc::execl(
                c"/bin/true".as_ptr(),
                c"true".as_ptr(),
                std::ptr::null::<libc::c_char>(),
            );
            libc::_exit(4);
        }
    }
    let mut event = libc::pollfd {
        fd: ready[0].as_raw_fd(),
        events: libc::POLLIN,
        revents: 0,
    };
    let ready_result = unsafe { libc::poll(&mut event, 1, 5000) };
    let mut byte = 0u8;
    if ready_result == 1 {
        unsafe {
            libc::read(ready[0].as_raw_fd(), (&mut byte as *mut u8).cast(), 1);
        }
    }
    drop(gate);
    let probe = fs::File::open(&gate_path).unwrap();
    let held = unsafe { libc::flock(probe.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) };
    let held_error = std::io::Error::last_os_error().raw_os_error();
    let released = unsafe { libc::write(release[1].as_raw_fd(), (&byte as *const u8).cast(), 1) };
    let mut status = 0;
    let waited = unsafe { libc::waitpid(child, &mut status, 0) };
    let after_exec = unsafe { libc::flock(probe.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) };
    drop(probe);
    fs::remove_file(gate_path).unwrap();
    fs::remove_dir(path).unwrap();
    assert_eq!(ready_result, 1);
    assert_eq!(released, 1);
    assert_eq!(waited, child);
    assert!(libc::WIFEXITED(status));
    assert_eq!(libc::WEXITSTATUS(status), 0);
    assert_eq!(held, -1);
    assert_eq!(held_error, Some(libc::EWOULDBLOCK));
    assert_eq!(after_exec, 0);
}
