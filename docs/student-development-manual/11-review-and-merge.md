# 11. Review and merge a pull request

**Goal:** Explain a change so someone else can assess it.

A PR is a review surface. Its title should describe the result, and its description should explain the problem, the change and the evidence. A reviewer should not need the original chat to understand it.

## A useful description

For the startup case, a good summary explains that the old app could submit safety and validation reads together. The new sequence waits for safety and coordinates related readers. It also states that owner-device causation and later candidate evidence remain separate questions.

Use the PR form in the workbook. Include:

- What the user experienced and what changes now.
- The issue or requirement being addressed.
- Checks performed and their limits.
- Outstanding work or decisions.

An increment can say **Related to #160** without declaring the whole issue complete. Closing an issue should follow its full acceptance criteria.

## Review behavior and evidence

| Review question | Why it matters |
| --- | --- |
| Does the change solve the stated problem? | A technically valid edit may solve the wrong task. |
| Does it preserve existing requirements? | A passing test should not come from removing a safety rule. |
| Are tests meaningful? | They should check behavior, not merely repeat the implementation. |
| Does the description match the final code? | Reviewers need the actual current scope. |
| Which evidence is still missing? | Local tests, native checks and owner testing have different limits. |

Comments should be specific and respectful. “This delayed result can overwrite a newer one; can we check the request identity?” gives the author something to investigate.

## Required checks and merging

Branch protection can prevent merging until required checks pass. SDE's current required checks include `checks` and `acceptance`. The aggregate acceptance check accounts for applicable native/trust work.

Check the exact PR head and current target branch. New commits can invalidate earlier evidence. Merge through the normal protected path when the requirements are met; an administrator bypass is not evidence that tests passed.

A **merge conflict** means Git cannot automatically combine some changes. Read both versions, understand their intent, resolve the conflict and check the result. Choosing one entire side without inspection can discard important work.

After merge, record the main commit and its validation. A squash merge may give that commit a different ID from the branch's commits.

## Practice

Have a partner review your help document against the issue. Record one improvement and revise it. If your mentor supplies a practice GitHub repository, follow its review and merge process there.

## Check your understanding

- Why should a PR description change when the implementation scope changes?
- What does required-check success establish, and what remains for release?

[Next: release and delivery](12-release-and-delivery.md)
