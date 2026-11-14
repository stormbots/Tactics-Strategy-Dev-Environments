# 9. Follow GitHub CI

**Goal:** Trace a workflow and explain each result.

Read the [CI Student Guide](../CI-STUDENT-GUIDE.md) first. It explains the main workflow's steps, including setup, scope classification, code checks, native builds, trust checks, acceptance and release gates.

Use this chapter to practice reading the evidence behind those steps.

## Read the run as a dependency map

For a full application run, `scope` classifies the work. `checks` then runs the common checks. The Windows/Linux native and trust jobs can start after those checks pass. `acceptance` evaluates every applicable result.

The workflow's `needs` fields describe these dependencies. A job that is waiting may need an earlier job's result, an available runner or a human approval, depending on its position.

The shorter presentation-only PR path comes from an explicit list of allowed file paths. A new file or a file called “documentation” does not automatically qualify for fewer checks. Read the policy instead of guessing from the extension.

## Four items to record before interpreting green checks

| Item | Why it matters |
| --- | --- |
| Workflow | A helper workflow can answer a different question from the main application workflow. |
| Commit | The result applies to particular code. |
| Required jobs | Expected skips differ from missing required work. |
| Environment | A Linux test and a Windows test establish different evidence. |

An artifact is saved output from a run. It can help with diagnosis, but it may be an unsigned test package. Release verification is a later responsibility.

## Why a run takes time

The temporary runner may need to download dependencies, restore cached build files, compile Rust code, create installers and build an upgrade fixture. Parallel jobs reduce elapsed waiting time, while each still uses runner time.

SDE starts common checks before the expensive native jobs. This avoids allocating those jobs when an earlier required check already failed. It does not remove their requirement when they apply.

A new commit can supersede an older run. A cancellation is not a pass, and useful evidence should be preserved.

## Practice with a verified run

Open [the corrected startup run](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/43581367274). Record its workflow, PR head commit, applicable job results and release-job status. Explain why release was skipped on this PR run.

The linked historical run passed its applicable checks. Use it as a fixed example rather than assuming it describes today's newest branch.

## Check your understanding

- Why can two jobs show different progress at the same time?
- Why does the aggregate `acceptance` check matter?
- What should you check before treating a gray skipped job as a problem?

[Next: investigate a failure](10-debug-ci.md)
