# 2. Follow the development cycle

**Goal:** Explain the path from a problem to a maintained release.

A useful change begins with a person who needs something to work better. We first describe the problem and expected behavior. Then we plan, implement, test and review a focused change.

After merge, release preparation adds another set of questions: Which exact code are we shipping? Are the packages correct? Are the published files authentic? Does the candidate work for the owner?

## The same task at different stages

| Stage | Startup example | Evidence to keep |
| --- | --- | --- |
| Report | The app needs an extra click after opening. | Observation and circumstances. |
| Investigate | Two startup reads may overlap. | Source locations and a reproduction test. |
| Plan | Make the reads take turns. | Requirements, limits and test plan. |
| Implement | Add the sequence and queue its related readers. | Focused commits and tests. |
| Review | Check the code and its explanations. | PR discussion and validation results. |
| Integrate | Merge through the protected branch. | Merge commit and main CI. |
| Prepare a candidate | Identify and verify the release files. | Exact source, package identities and signatures. |
| Accept | Test the candidate on supported real computers. | UAT results and unresolved findings. |
| Maintain | Investigate new reports and plan follow-ups. | New issues and durable checkpoints. |

The completed PR does not erase later stages. A fix can be merged while packaged verification or owner testing remains outstanding.

## Who does what?

| Role | Responsibility |
| --- | --- |
| User or student tester | Describe what happened and provide useful observations. |
| Developer | Investigate, implement and explain a change. |
| Reviewer | Examine the reasoning, code and evidence. |
| Maintainer | Keep project rules and integration requirements intact. |
| Signing approver | Make the required human signing decision. |
| Owner | Test and accept the exact candidate, then separately authorize promotion when appropriate. |

One person may fill several roles. Each decision still needs its own evidence and authorization. The assistant can prepare work and review results; it cannot supply the owner's human signing approval or UAT judgment.

## Practice

Draw the development cycle in your own words. Put a person or role beside every decision. Add a return arrow showing what happens when a test finds a problem.

## Check your understanding

- Can a merged PR still have release work left to do?
- What useful information is missing from the statement “It works now”?

**Expected idea:** We need to know what was tested, which version was tested and what remains unverified.

[Next: write an issue](03-write-an-issue.md)
