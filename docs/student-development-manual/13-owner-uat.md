# 13. Test as an owner

**Goal:** Record whether the exact candidate helps a person complete the intended tasks.

**User acceptance testing**, or **UAT**, checks the candidate from the user's point of view. A person can notice confusing wording, an awkward route through screens or behavior specific to a real computer.

The owner must receive the exact authenticated candidate and its supported instructions first. A test of an earlier version or a browser mockup cannot accept different release files.

## Record outcomes honestly

| Result | Use it when… | Example |
| --- | --- | --- |
| Pass | You performed the check and observed the expected result. | The verified candidate opens and completes its normal startup check. |
| Fail | You performed the check and observed a different result. | The app still requires an unexplained second click. |
| Blocked | A prerequisite prevents the check. | The intended candidate has not yet been authenticated or supplied. |
| Not observed | The situation did not arise during testing. | No active installer was naturally present. |

Do not turn “Not observed” into Pass. Difficult interruption and permission situations belong in controlled fixtures rather than being manufactured on an owner's working laptop.

## A sample startup walkthrough

This is a teaching outline. The actual release's approved runbook controls real testing.

1. Record the supplied candidate, operating system and account context.
2. Confirm the installed version through the supported app view.
3. Open the app normally and observe its startup check.
4. Record the actual readiness and safety findings.
5. Navigate to another page and check that delayed results do not unexpectedly redirect you.
6. Report any unclear explanation or missing next action.

A healthy computer should not need a manual retry merely because the app competed with its own reads. A real safety or collection problem must remain explained rather than being hidden to make the test pass.

## When UAT finds something new

Record the steps, expected result, actual result and useful evidence. Preserve existing work and incident records. Development can reproduce difficult cases in a disposable environment.

The real Python finding shows why this matters. The initial screenshot alone did not prove Python 3.14 was absent. Later owner evidence established that it was installed and runnable alongside 3.15. That changed the investigation from “install a missing version” to “verify the compatible installation explicitly.” It still did not prove all required pip capabilities passed.

## Practice

Use the workbook to record a review of your help document as if you were a new student. Mark any real application scenario you did not exercise **Not observed**. This practice review supplies no release acceptance.

## Check your understanding

- How is a blocked check different from an unobserved situation?
- Why must the candidate record stay tied to exact files?

[Next: maintenance and handoffs](14-maintenance-and-handoffs.md)
