# SDE 1.2.19 — Windows recovery and clearer preflight actions

Replacement milestone 3 UAT candidate for the findings reported on v1.2.18.

- Windows Validate can inspect an idle workstation with an interrupted system
  transaction. It reports the interruption and preserves the protected record.
- Recovery also appears for interrupted machine operations without a per-user
  incident. Validation, logs and support reports remain available; Install,
  Update and Repair require mentor review while that system interruption remains.
- Failed startup validation offers Retry validation rather than Retry install.
- Preflight buttons appear as Continue, Check Again, Cancel. Continue uses the
  highlighted primary style in both themes.

Use the [focused replacement UAT guide](SAFE-OPERATIONS-UAT-1.2.19.md). Preserve
the owner's successful Mint v1.2.18 installation/validation evidence. Windows
acceptance and unreported milestone checks remain pending.

Only v1.2.19 is published as a prerelease. A rebuilt same-source v1.2.18 is an
unpublished upgrade fixture; published v1.2.18 assets remain unchanged. Application
installation enables automatic SDE updates as before. Stable promotion and fleet
rollout require separate owner decisions.
