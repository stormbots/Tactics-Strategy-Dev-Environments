# 10. Investigate a failed check

**Goal:** Use the failed job's evidence to explain a problem and justify the next action.

A red run tells you to investigate. It does not yet tell you whether the defect is in application code, a test helper, a dependency or the test environment.

Start with the failing job and step. Read the failure summary and nearby lines. Some tests intentionally print error messages while checking that failures are handled correctly, so the word “error” by itself is not the whole diagnosis.

## A real startup-test failure

The first startup implementation run failed the new protected regression on both platforms. These two relevant lines are shown together for teaching:

```text
test tests::startup_read_ordering_preserves_native_gate_and_external_deferral ... FAILED
assertion failed: external.wait().unwrap().success()
```

Read them this way:

| Part | What it tells us |
| --- | --- |
| Test name | Which behavior was under test. |
| `FAILED` | The test did not satisfy its expectation. |
| `external.wait()` | The test was collecting the child process's exit result. |
| `success()` | It expected a normal successful exit. |

The Linux log also reported a broken output pipe. The helper had closed the read end after receiving the child's ready signal. When the child finished, the Rust test runner could not write its final output through that pipe.

The correction retained the pipe and collected the output through exit. It kept the successful-exit assertion and every gate/activity check. The [corrected run](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/43581367274) then passed.

This is evidence that the helper needed correction. It is not a reason to disable the trust jobs.

## A repeatable investigation

1. Identify the exact run, commit, job and failed step.
2. Write what the log establishes, using its actual words where useful.
3. List a possible cause and the evidence still needed.
4. Reproduce the smallest relevant behavior in a suitable test environment.
5. Make a correction that preserves the requirement.
6. Run the affected checks and record both the old failure and new result.

An unchanged rerun is useful only when there is a reason, such as evidence of a temporary service failure. A new code defect usually needs a correction first.

## Practice

Use the workbook's investigation form with the [failed startup run](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/43568067928). Explain why removing the exit assertion would provide weaker evidence than fixing the pipe lifecycle.

## Check your understanding

- Which part of the log establishes the failed expectation?
- How would you distinguish a suspected cause from a confirmed reproduction?

[Next: review and merge](11-review-and-merge.md)
