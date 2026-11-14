# 4. Plan the change

**Goal:** Decide what to do, what to preserve and how to check the result.

A plan should be small enough to review and complete. It should also identify dependencies: work that must happen before another step can begin.

In the startup fix, changing the order alone was not the entire task. Other readers using the same gate needed examination. Real external activity still had to block competing work. Old results could not overwrite newer ones.

## Four questions for a useful plan

| Question | Startup example |
| --- | --- |
| What should improve? | A normal launch completes its required check without a manual retry caused by same-window overlap. |
| What must remain true? | Genuine failures stay visible, native locks remain authoritative and installation still needs its normal review. |
| What will change? | Startup ordering and scheduling for the related readers. |
| What will prove it? | Delayed-result tests, native gate tests, platform CI and later packaged/owner evidence. |

A good plan names uncertainty. “We still need the owner's initial logs” is more useful than claiming a cause that has not been established.

## Plan the practice document

1. Read the case study and existing CI guide.
2. Draft the startup explanation in a practice file.
3. Check each statement against the implementation record.
4. Ask a reviewer to check clarity and missing next steps.
5. Record what was reviewed and what was not tested.

No app installation is needed to complete this writing task. Choose checks that fit the change.

## Make a test table before editing

| Situation | Expected result |
| --- | --- |
| Normal startup | Safety information arrives before tool validation begins. |
| Safety is delayed | The app continues to show that checking is underway. |
| Another operation is active | Validation is deferred according to the existing rules. |
| A check genuinely fails | The failure remains visible; no automatic retry loop creates a false pass. |
| User changes pages | An old result does not drag the user back. |

This is a teaching summary, not a replacement for the full acceptance criteria.

## Practice

List three steps for your practice document and one thing the document must not promise. Add one reviewer question for each acceptance criterion.

## Check your understanding

- Why should the plan say what must remain unchanged?
- Which checks could you perform locally, and which require another environment?

[Next: Git and GitHub](05-git-and-github.md)
