# 3. Describe the problem

**Goal:** Write an issue that another person can investigate.

An issue records a problem or proposed improvement. Good issues explain the user's experience before guessing at the code change.

For example, “Fix startup” is too broad. “SDE shows Check not finished on ordinary launch, but Check again clears it” gives someone an observable starting point.

## Separate observation from explanation

An **observation** is something you saw or measured. A **hypothesis** is a possible explanation.

In the startup case, the owner observed the message and the successful second check. Source review suggested overlapping reads. A test then confirmed code-level overlap. Additional device evidence would still be needed to tie that overlap to the owner's exact failure.

Keep these statements separate. Otherwise, a guess can quietly become a requirement or a claimed fact.

## A practice issue

> **Title:** Explain what happens during the startup check
>
> **Problem:** A new student may not understand why SDE checks the computer when it opens.
>
> **Expected result:** A short help document explains the normal check, genuine incomplete results and a useful next action.
>
> **Proposed scope:** Write `startup-check-help.md` in the practice repository.
>
> **Acceptance criteria:**
>
> - Explain safety checking before tool validation.
> - Say that a genuinely unfinished check does not establish readiness.
> - Offer a supported next step without promising that a retry fixes every cause.
> - Use short sentences and explain unfamiliar terms.
> - Describe no automatic installation or safety override.

These criteria describe what someone can review. “Make it good” provides no clear finishing point.

## Useful report details

Record the app version, operating system, steps taken, expected result and actual result. Include an error message or screenshot when useful. Remove passwords, access tokens and unrelated personal information before sharing evidence.

Say whether the problem happens consistently. If you did not observe a condition, leave it unknown rather than filling in a likely answer.

## Practice

Use the issue form in the workbook. Write the practice issue in your own words. Have a classmate explain the expected result back to you without additional coaching.

## Check your understanding

- Which parts of your issue are observations, and which are proposals?
- Could a reviewer determine whether each acceptance criterion is satisfied?

[Next: plan the change](04-plan-a-change.md)
