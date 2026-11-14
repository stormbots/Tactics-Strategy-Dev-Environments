# How our GitHub checks work

*A student guide to Skyview Dev Setup*

Reviewed November 14, 2026

Before we share a new version of Skyview Dev Setup, we need evidence that the changes work and that our safety rules still hold. GitHub runs many of these checks for us. People then review the results and test the release on real computers.

This guide explains our main workflow, **Build Skyview Dev Setup**, in the order the work happens.

## A few words you will see

| Word | Meaning |
| --- | --- |
| **Repository**, or **repo** | The project's shared files and change history. |
| **Commit** | A saved set of changes with a unique ID. The ID helps us record exactly which code was tested. |
| **Branch** | A place to work on changes before adding them to the main project. |
| **Pull request**, or **PR** | A request to review a branch and combine its changes with another branch, usually `main`. |
| **Tag** | A label that marks a particular commit, often to identify a software version. |
| **CI** | **Continuous integration**: automatic checks that help us find problems as changes are added. |
| **GitHub Actions** | GitHub's service for running those automatic checks. |
| **Workflow** | A set of instructions for GitHub Actions. |
| **Run** | One attempt to follow a workflow for a particular set of code. |
| **Job** | A group of tasks within a run. Each job contains individual steps. |
| **Runner** | The computer that carries out a job. Our main workflow uses temporary GitHub-hosted computers. |
| **Artifact** | A file saved from a run, such as an installer, screenshot or test report. |

## 1. Prepare the change and open a pull request

**What happens:** A developer makes changes on a branch and runs useful checks locally, on the developer's computer. The developer then opens a PR. Pushing another commit to that PR starts a new check of the updated code.

**Why:** Local checks catch mistakes early. The PR gives reviewers a place to inspect the changes, discuss them and see GitHub's results.

A result belongs to the code that was tested. If the code changes, an earlier green result does not automatically cover the new code.

## 2. GitHub starts the workflow

**What happens:** GitHub creates a run. A job may first show **Queued** while it waits for a runner or another job to finish.

When a runner starts, it gets a copy of the project. Steps named **checkout** do this. Other setup steps prepare tools such as Node.js, Python and Rust.

Some steps restore a **cache**: previously downloaded tools or build files that can save time. Required checks still run.

**Why:** We need a repeatable test setup. These jobs use temporary test computers rather than changing students' laptops.

The main workflow also runs after application changes reach `main`. Approved release branches or tags and manual requests can start it too.

## 3. `scope`: decide which checks are needed

**What happens:** The `scope` job reads the changed file paths and applies the repository's CI policy. It also tests the policy itself.

A small, approved list of changes to screen layout or wording can use a shorter PR check. Changes to installation scripts, native code, dependencies or other important files require the full set. New or unrecognized files normally receive the full set too.

**Why:** Runners use time and money. We can avoid repeating expensive platform builds for changes covered by the approved shorter path, while keeping the required checks for changes that need them.

The rule uses specific file paths. A file being “only documentation” does not automatically qualify it for fewer checks.

## 4. `checks`: test the code and screens

This job runs before the more expensive platform jobs.

| Step | What happens | Why we do it |
| --- | --- | --- |
| Install project dependencies | `npm ci` gets the exact versions recorded in the project's lockfile. | Different dependency versions could produce different results. |
| Run automated tests | Tests check small pieces of behavior and how pieces work together. | We want new changes to work without breaking behavior that already worked. |
| Build the app's screens | TypeScript checks the code, and the build tools prepare the interface for use. | Code can look reasonable but still fail to build. |
| Audit dependencies | npm checks for known security problems at the configured severity level. | Problems can come from software our app depends on. |
| Check scripts and safety rules | Tools inspect Bash scripts. Other tests check the work behind the screens, including permissions, schedules and safety rules. | Installation and maintenance code must follow the project's rules. |
| Verify file checksums | GitHub compares listed Linux files with their recorded SHA-256 values. A checksum is a fingerprint of a file's contents. | Unexpected changes must be detected. A checksum alone does not prove who published a file. |
| Check the workflow instructions | A tool checks the GitHub Actions configuration for mistakes. | The instructions that run our tests need checking too. |
| Test the interface in browsers | Browser tests exercise clicks, keyboard use, accessibility and supported layouts. This workflow uses Chromium and WebKit. | Screens must be usable, including by people who navigate without a mouse. |
| Save evidence | GitHub saves screenshots and other test output as artifacts. | Reviewers need evidence they can inspect later. |

If this job fails, the expensive native and trust jobs do not start. We fix the reported problem before spending runner time on them.

## 5. Run platform and trust checks in parallel

For a full run, two groups of jobs can now run at the same time:

```text
scope → checks → native: Windows ─────────┐
               native: Linux/Mint ───────┤
               update-trust: Windows ────┼→ acceptance
               update-trust: Linux ──────┘
```

Each line has its own work to finish. One green line does not finish the whole run.

### `native`: build and test the actual application packages

**What happens:** These jobs build the parts of the app written in **Rust**, a programming language. **Cargo** is the tool that builds and tests that code. The jobs then create the Windows `.exe` installer and Linux `.deb` package.

The jobs check package contents and versions. They also run installation, recovery, permission and upgrade checks in controlled test setups. Some upgrade checks build another test version so they can exercise a real upgrade.

The Windows runner uses Windows Server 2022. The Linux runner uses Ubuntu 24.04, and required upgrade checks also run in a Linux Mint 22.3 test environment.

**Why:** A browser test cannot prove that a Windows installer works or that Linux permissions are correct. We need checks that use the operating system and installed application.

Some tests use a **fixture**, meaning a setup built to test a particular situation. A fixture can prove that a specific rule works. It does not prove that every feature works on every student's computer.

### `update-trust`: check safe coordination and trusted updates

**What happens:** These jobs check rules such as:

- Two operations that must stay apart cannot run together.
- An interrupted operation keeps its evidence.
- Acknowledging an interruption does not bypass fresh safety checks.
- Protected files and folders keep the required permissions.
- The updater rejects changed or incorrectly signed update data.

Some Linux tests run as **root**, the Linux administrator account. Other tests check what an ordinary user can do.

**Why:** SDE installs and updates software. We must test both useful behavior and the limits that prevent unsafe changes.

## 6. `acceptance`: check the complete result

**What happens:** This job examines the earlier jobs. It requires successful scope classification and a pass from every job that applies to this change.

It is configured to evaluate those results even when an earlier job fails. A required job that failed, was canceled or was unexpectedly skipped cannot produce an acceptance pass.

**Why:** GitHub needs one clear answer to “Did every required part pass?” We must not mistake several green jobs for a complete result when another required job failed.

A planned skip can be correct. For example, the approved shorter PR path can skip native jobs. `acceptance` checks whether that skip matches the policy.

## 7. Review and merge the pull request

**What happens:** Reviewers inspect the change and its evidence. GitHub's branch protection requires the configured checks to pass before a normal merge. Our current required checks include `checks` and `acceptance`.

When the requirements are satisfied, the PR can be merged into `main`.

**Why:** Automated results help people make a decision. They do not explain every design choice or replace review.

If a check fails, open its failed step and read the error. We fix the cause and test the correction. Repeating the same failed test without a reason usually wastes time.

## 8. Check the actual `main` commit

**What happens:** GitHub checks the merged code on `main`. We record that commit's ID and its run results. You may hear this called **exact-main CI**.

**Why:** The project continues to change. We need evidence for the exact shared version we plan to use, not just an earlier branch.

Related development can continue while a run is working. We still need the required final results before preparing a release. A waiting developer leaves a checkpoint with the commit, run link, completed checks and next action so someone can resume the work later.

## 9. Prepare, sign and verify a release candidate

**What happens:** After the required development and release checks, an eligible release run can reach the protected `sde-release-signing` approval step. An authorized human must approve signing.

The release job checks the installers, creates metadata describing the release, signs that metadata and verifies it. It publishes a **prerelease**, a candidate intended for testing. The exact published files and their signature must then be independently verified before owner testing.

**Why:** Tests check behavior. Checksums help detect changed contents. A digital signature helps prove that release data came from the trusted publisher. We need each kind of evidence.

On an ordinary PR run, `release` is normally **Skipped**. A green PR does not automatically publish software. An Actions artifact is saved test output; students should install the approved, verified release supplied for testing.

## 10. Complete owner UAT and approve promotion separately

**What happens:** The owner tests the exact verified candidate on supported real computers. This is **user acceptance testing**, or **UAT**.

The owner records what passed, failed, was blocked or was not observed. A problem found here may lead to another code change and another round of checks.

After the required acceptance evidence is complete, promoting the candidate to a stable release still needs separate authorization.

**Why:** Automated tests cover planned situations. Real people can find confusing wording, awkward workflows or device-specific problems that those tests missed.

## How to follow a run on GitHub

1. Open the repository's **Actions** tab, or open the checks on its PR.
2. Choose **Build Skyview Dev Setup** and the run you want to inspect.
3. Check the branch and commit so you know which code the results cover.
4. Select a job to see its steps. Open a failed step to read its log.
5. Find `acceptance` and review any required jobs that are still unfinished.
6. Use saved artifacts when you need screenshots, reports or other evidence.

| Status | What it tells you |
| --- | --- |
| **Queued** | The job is waiting to start. |
| **In progress** | The job is running. |
| **Success** | That job completed successfully. Other required jobs may still be unfinished. |
| **Failure** | Something needs investigation. The log explains where the job stopped. |
| **Canceled** | The job stopped before completion. It supplies no passing result. |
| **Skipped** | A condition kept the job from running. Check whether that was expected. |
| **Waiting for approval** | An authorized person must make the required decision. |

Runs can take time because they download tools, turn code into programs, build installers and test multiple systems. Running jobs in parallel helps, but we must still wait for every applicable result. A newer commit may replace an older run; we keep useful evidence and avoid unnecessary retries.

## Where these rules are defined

- [Main GitHub Actions workflow](../.github/workflows/build-dev-setup.yml)
- [CI validation and runner-cost policy](CI-VALIDATION-POLICY.md)
- [Rules that classify changed files](../tests/ci_scope.py)

Other workflows may appear in Actions for specific testing or maintenance tasks. Their results belong to those workflows. This guide describes the main application build process; it is not a live status report for a particular run.
