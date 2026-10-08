# Skyview Dev Setup 1.2.1

This release fixes Linux Mint Install and Repair stopping at the Node.js version selection step with exit 141. Scheduled updates used the same selector and receive the same correction.

The selector now consumes the complete APT version listing while selecting its first Node.js 24.x candidate. This prevents the package reader from receiving a broken pipe when the listing is large. Missing 24.x candidates and genuine package-reader failures still stop the operation; Node remains on 24.x and Python remains on 3.14.x.

A regression test executes the actual selectors from both scripts against synthetic APT output. It covers large mixed-version listings, missing candidates, and package-reader errors without provisioning the test host. The large-listing case reproduces exit 141 with the previous selector and passes with the correction.

The release retains the version-aware tool list, Schedule, and About pages from [1.2.0](RELEASE-NOTES-1.2.0.md). Windows is rebuilt with the matching app/package version; its provisioning behavior is unchanged. Windows code signing is not required by project decision.

Both native installers and automated checks passed. On **2026-10-08**, the project owner accepted all checklist items and authorized merge and stable publication; see [the 1.2.1 acceptance record](ACCEPTANCE-1.2.1.md). The supplied Mint 22.3 installation and subsequent validation logs each show **35 passed, 0 warnings, 0 failed**. Acceptance includes the known PowerShell same-version reporting limitation, which remains a future correction.

Stable promotion preserves tag `v1.2.1` at source commit `40c2177c5916002db2e8da45143784b1ac6ad114` and its tested installer/checksum assets. Downloaded assets matched the published SHA-256 manifest and GitHub digests. Version **1.2.1** is the current stable release; earlier releases remain available.

On a Mint machine that encountered the earlier failure, install this GUI package and choose **Install** or **Repair** to resume setup, then Validate.
