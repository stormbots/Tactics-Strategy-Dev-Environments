# 1. Meet the project

**Goal:** Find the main parts of SDE without needing to understand every line.

A repository is a shared collection of files and their history. Start by asking what each folder is responsible for. File names give useful clues, but the contents provide the evidence.

## A map of SDE

| Location | What you will find | Why it matters |
| --- | --- | --- |
| `installer/src/` | Screens, messages and interface behavior. | This is much of what a user sees. |
| `installer/src-tauri/` | Rust code connecting the desktop app to operating-system work. | Native behavior needs checks beyond a browser preview. |
| `windows/chocolatey/tools/` | Windows setup, maintenance and validation scripts. | These can interact with installed software and settings. |
| `linux/` | Linux setup and validation scripts, helpers and deployment files. | Windows behavior does not prove Linux behavior. |
| `coordination/` | Rules for work that must take turns and for retained operation evidence. | Two competing operations must not create unsafe changes. |
| `updater/` | Code for trusted update verification and related update work. | Downloaded update data must be authenticated before use. |
| `tests/` | Backend, platform, policy and other checks. | Requirements need repeatable evidence. |
| `.github/workflows/` | Instructions for GitHub Actions. | These define automatic jobs and their dependencies. |
| `docs/` | Designs, decisions, user-testing plans and evidence records. | The reasons for a change should remain available. |

The interface is often called the **frontend**. Work behind it is often called the **backend**. These are useful labels, but a real action may cross several folders.

For startup checking, the screen behavior involves `App.tsx`, bridge calls and native validation. Reading only the headline text would miss the ordering problem.

## Read before changing

Start with `AGENTS.md` and relevant project documentation. Then find the smallest set of source files related to the task. Read nearby tests too: they often describe expected behavior more clearly than a large function does.

The repository also has architecture decision records under `docs/adr/`. These explain important choices, including why an acknowledgment cannot replace fresh safety checks. Beginners can read their context and decision sections before studying the detailed implementation.

## Practice

Browse the repository without running its installation scripts. Find one interface file, one test and one workflow. For each, write its path and one sentence explaining its purpose.

## Check your understanding

- Why is an interface test alone insufficient to prove that an installer works?
- Where would you look for the reason behind a safety rule?

**Expected idea:** Different parts have different responsibilities. A result from one layer does not automatically prove another layer works.

[Next: the development cycle](02-development-cycle.md)
