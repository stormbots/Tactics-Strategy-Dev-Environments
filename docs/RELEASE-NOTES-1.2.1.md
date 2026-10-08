# Skyview Dev Setup 1.2.1

This release candidate fixes Linux Mint Install and Repair stopping at the Node.js version selection step with exit 141. Scheduled updates used the same selector and receive the same correction.

The selector now consumes the complete APT version listing while selecting its first Node.js 24.x candidate. This prevents the package reader from receiving a broken pipe when the listing is large. Missing 24.x candidates and genuine package-reader failures still stop the operation; Node remains on 24.x and Python remains on 3.14.x.

A regression test executes the actual selectors from both scripts against synthetic APT output. It covers large mixed-version listings, missing candidates, and package-reader errors without provisioning the test host. The large-listing case reproduces exit 141 with the previous selector and passes with the correction.

The candidate retains the version-aware tool list, Schedule, and About pages from [1.2.0](RELEASE-NOTES-1.2.0.md). Windows is rebuilt with the matching app/package version; its provisioning behavior is unchanged. Windows code signing is not required by project decision.

Both native installers and automated checks must pass before publication. Manual acceptance remains pending; see [the 1.2.1 checklist](ACCEPTANCE-1.2.1.md). On the affected Mint machine, install this GUI package and choose **Install** or **Repair** to resume setup, then Validate. Version 1.1.5 remains stable.
