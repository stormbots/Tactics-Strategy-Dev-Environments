# 7. Make and check a change locally

**Goal:** Inspect your work and choose checks that match it.

Start by reading the current file and nearby tests. Make one focused change. Then compare your working copy with the saved version before staging it.

For the practice help document, check each sentence against the issue's acceptance criteria. A reviewer should find a clear description of normal checking, an honest explanation of incomplete results and a useful next action.

## Read the available commands

SDE's interface manifest defines these commands:

| Command | Location | What it does and changes |
| --- | --- | --- |
| `git diff` | Repository root | Displays unstaged changes; changes no project files. |
| `npm test -- src/nativeReadQueue.test.ts` | `installer/` | Runs the existing queue test file through Vitest. Test tools may create temporary or cache files. |
| `npm run build` | `installer/` | Checks TypeScript and creates build output. It does not install SDE on the computer. |
| `npm run dev` | `installer/` | Starts the browser development preview until you stop it, usually with Ctrl+C. |

Run project commands only after your mentor has prepared the approved clone and dependencies. A successful browser preview is interface evidence. It does not establish that native installation or operating-system permissions work.

## Use a short feedback loop

1. Make the smallest useful edit.
2. Inspect the diff for accidental changes.
3. Run a focused check related to the edit.
4. Read the result, including failures.
5. Run the broader required checks when the change is ready for review.

If a later edit could invalidate a result, run the affected check again. Otherwise, retain useful passing evidence rather than repeating everything without a reason.

## Record a result accurately

> **Example check record:** Ran the queue test file from `installer/` on the approved development clone. It passed. This checks queue behavior in the test environment. Native gate and packaged app behavior were not exercised by that command.

Keep the actual command, code version, environment and result. A count of passing tests is useful only when we understand what those tests checked.

## Practice

Inspect your document diff and correct one unclear sentence. Record the review criteria you used. If your class has a prepared SDE clone, run the queue test and explain one assertion to a partner.

## Check your understanding

- Which command starts a preview rather than a finished installed application?
- What would make a previously passing result outdated?

[Next: useful tests](08-testing.md)
