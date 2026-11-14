# Student workbook

Copy these forms into your practice notes. Replace prompts with your own observations. Keep teaching examples and historical repo evidence separate from work you personally completed.

## 1. Repository map

| File or folder | Its purpose | How I checked |
| --- | --- | --- |
| Interface | | |
| Test | | |
| Workflow | | |
| Design or decision record | | |

## 2. Practice issue

**Title:**

**Who experiences the problem?**

**What happened?**

**What should happen?**

**Steps or circumstances:**

**Observed evidence:**

**Possible explanation, still unconfirmed:**

**Acceptance criteria:**

- [ ]
- [ ]
- [ ]

**Outside this task:**

For the continuing practice exercise, the deliverable is `startup-check-help.md`. It is a help document, not a production app modification.

## 3. Change and verification plan

| Work item | Why it is needed | Evidence that would support completion |
| --- | --- | --- |
| | | |
| | | |
| | | |

**Existing behavior or rule to preserve:**

**Environment needed:**

**Known uncertainty:**

**Dependencies before the next step:**

## 4. Local check record

| Field | Your record |
| --- | --- |
| Practice or development repository | |
| Branch and commit, if committed | |
| Operating system and relevant tools | |
| File/change inspected | |
| Command or review method | |
| Expected result | |
| Actual result | |
| What this result establishes | |
| What it does not establish | |

A document review can be an appropriate check. Do not invent an automated test result for writing you only read.

## 5. Practice PR description

**Problem and resulting behavior:**

**Related issue or exercise:**

**What changed:**

**Checks performed:**

**Evidence links:**

**Outstanding work or limits:**

Use a practice PR if a mentor has supplied the repository. Otherwise, write the description locally and have a classmate review it.

## 6. CI observation

| Field | Historical run you inspected |
| --- | --- |
| Workflow name | |
| Run URL | |
| Branch/PR | |
| Head commit | |
| `scope` result | |
| `checks` result | |
| Native results, or reason for expected skip | |
| Trust results, or reason for expected skip | |
| `acceptance` result | |
| Release result and explanation | |
| Saved artifact or useful log | |

**Was this your own practice run or a real historical example?**

**What can you conclude from it?**

## 7. Failure investigation

**Exact run, commit, job and step:**

**The failed expectation:**

**Relevant log excerpt:**

**What the evidence establishes:**

**Suspected cause:**

**Smallest suitable reproduction:**

**Proposed correction:**

**Requirement that must remain intact:**

**Verification result or next evidence needed:**

For the startup case, explain why keeping the successful-exit assertion provides stronger evidence than deleting it.

## 8. Mock candidate record — practice only

| Field | Value or evidence still needed |
| --- | --- |
| Proposed version label | Practice only — no version reserved |
| Exact source commit | |
| Applicable CI results | |
| Exact-main evidence | |
| Windows package identity | |
| Linux package identity | |
| Published-file identifiers and checksums | |
| Trusted signature verification | |
| Human signing approval | Not requested by this exercise |
| Owner UAT | Not performed by creating this form |
| Separate promotion authorization | Not requested by this exercise |

Explain what each missing field prevents you from claiming. Do not substitute an example value for real evidence in a production record.

## 9. Practice UAT record

**Candidate or document reviewed:**

**Reviewer and environment:**

| Scenario | Expected result | Observed result | Pass / Fail / Blocked / Not observed | Evidence |
| --- | --- | --- | --- | --- |
| Understand normal startup | | | | |
| Understand an incomplete check | | | | |
| Find a useful next step | | | | |

For a document-only practice review, record that fact. Real application behavior remains unobserved unless you actually tested the approved candidate under its runbook.

## 10. Handoff

**Completed work:**

**Branch, exact commit and PR, if any:**

**Completed checks and evidence:**

**Limits and unobserved behavior:**

**Pending CI or approvals:**

**Next action:**

**Who is responsible for the next decision?**

## Final exercise

Build a learning portfolio around the practice help document:

1. Map the relevant project files.
2. Write the issue and acceptance criteria.
3. Make a focused plan.
4. Use a practice branch and record meaningful commits.
5. Review the document against the requirements.
6. Inspect a real historical CI run and investigate its recorded failure.
7. Prepare a practice PR description and review.
8. Complete a mock candidate record and document review.
9. Leave a handoff someone else can follow.

A mentor-provided safe practice workflow can add a real CI run to this exercise. Production signing, package installation, release publication and promotion are outside the classroom activity.

## Reflection

- What did you initially assume that the evidence did not prove?
- Which test or review caught the most useful problem?
- What remained uncertain at the end?
- What would the next person need to continue?
