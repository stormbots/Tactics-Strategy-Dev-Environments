# Glossary

Use this page as a reference. You do not need to memorize every term before starting.

| Term | Meaning in this manual |
| --- | --- |
| Acceptance criteria | Specific results used to decide whether a task is complete. |
| Acceptance check | SDE's aggregate CI job that verifies every applicable automated job has the required result. It does not replace owner UAT. |
| Action | A reusable task or command setup used in GitHub Actions. |
| Administrator / root | An account or privilege level with broad operating-system authority. Linux calls its administrator account root. |
| Architecture decision record / ADR | A document explaining an important technical choice and its reasons. |
| Artifact | Output saved from a workflow run, such as a screenshot, report or installer. |
| Assertion | A statement in a test that compares a result with an expectation. |
| Authentication | Checking whether something comes from the source we trust. |
| Authorization | Permission to perform an action. A successful test alone does not grant it. |
| Backend | The work behind the interface, including native operations and supporting services or scripts. |
| Branch | A pointer to a line of work in Git. |
| Branch protection | GitHub rules that control how changes can enter a branch. |
| Build | The process of preparing source code and resources as usable program output. |
| Cache | Saved downloads or build files reused to reduce repeated work. |
| Candidate | The exact version and files proposed for release testing. |
| Cargo | The Rust tool used to manage packages, build code and run tests. |
| Checksum / hash | A fingerprint calculated from file contents. It helps detect changed contents when compared with a trusted expected value. |
| CI / continuous integration | Regularly integrate changes and check them automatically. |
| Continuous delivery | A repeatable process for preparing software for release, with approval where needed. |
| Continuous deployment | Automatically deploy changes that satisfy the configured requirements. |
| Clone | A local copy of a Git repository and its history. |
| Commit | A saved change record with a unique ID. |
| Compile | Turn source code into another form that can be checked or executed. |
| Conflict | Changes that Git cannot combine automatically. A person must resolve their intended result. |
| Contract | An agreed rule between components or parts of a system. |
| Dependency | Software or work another component relies on. |
| Deploy | Put software into its intended operating environment. |
| Diff | A comparison showing changes between versions. |
| Digital signature | Data used to verify authenticity with a trusted public key. |
| Environment | The computer, tools, accounts and settings in which work runs. |
| Exact-head CI | Checks tied to the specific PR head commit being reviewed. |
| Exact-main CI | Checks tied to the actual merged main commit. |
| Fixture | A controlled setup for exercising a particular situation. |
| Frontend | The interface a user sees and interacts with. |
| Gate | A rule or mechanism that controls whether work may proceed. Different gates control different things. |
| Git | The version-control tool that records file history. |
| GitHub | The service hosting this repo, its issues, PRs and Actions runs. |
| Head | The latest commit on the branch being discussed. |
| Issue | A record of a problem, requirement or proposed improvement. |
| Job | A group of workflow steps carried out by a runner. |
| Lock / operation gate | A mechanism coordinating work that must not happen at the same time. |
| Lockfile | A dependency record that pins resolved package versions. It is unrelated to an operation gate. |
| Log | Output recorded while a command, test or job runs. |
| Main | This project's shared integration branch. |
| Manifest | A file describing a package's properties, dependencies or scripts. |
| Merge | Combine changes into a target branch. |
| Mock | Controlled behavior used in place of a component during a test. |
| Native | Working through the actual operating-system application and APIs rather than only a browser simulation. |
| npm | The tool used for JavaScript dependencies and named project scripts. |
| Package | Software files and associated information prepared for distribution or installation. |
| PATH | A list of locations the shell searches for commands. |
| pip | Python's package-management tool. |
| Prerelease | A published release marked for testing before stable use. |
| Promotion | The authorized step that makes an accepted candidate a stable release. It is separate from publishing a testing candidate. |
| Pull request / PR | A request to review and merge a branch's changes. |
| Regression | A previously working behavior broken by a change, or a fixed problem that returns. |
| Remote | A repository address used to exchange Git commits. |
| Repository / repo | Project files and their version history. |
| Review | Examination of a change, its reasons and its evidence. |
| Rollback | A controlled return to an earlier version, subject to the project's recovery rules. |
| Run | One execution of a workflow for particular code. |
| Runner | The computer carrying out a workflow job. |
| Script | A file containing commands or program instructions. |
| Secret | Protected data, such as a signing credential, that must not be exposed in source or logs. |
| Snapshot | A record of state at a particular moment or code version. |
| Squash merge | Combine a PR's changes into a single new commit on the target branch. |
| Stage | Select changes to include in a Git commit. |
| Step | An individual task inside a workflow job. |
| Tag | A Git label attached to a particular commit, often identifying a version. |
| Terminal / shell | A command interface and the program interpreting commands. |
| Test coverage | The behavior or code exercised by tests. A count alone does not describe its completeness. |
| Toolchain | Related tools that must work together, such as Node.js and its npm. |
| UAT | User acceptance testing of the exact verified candidate. |
| Virtual environment / venv | An isolated Python environment for a project or a controlled check. |
| Workflow | The instructions defining Actions triggers, jobs and steps. |
| Working tree | The project files currently checked out on your computer. |

For important project safety decisions, use the repository's ADRs and current requirements. This learning glossary explains terms; it does not replace those rules.
