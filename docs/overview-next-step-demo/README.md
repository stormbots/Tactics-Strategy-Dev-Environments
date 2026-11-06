# Overview next-step prototype

Open `index.html` directly in a browser. It is a self-contained offline HTML file:
no server, build, dependency install, internet connection or SDE installation is
needed. Downloading/copying just that file is sufficient. The small brand mark is
illustrative; the layout and theme colors follow the existing application.

Start with **Review setup**, then **Install development tools** and **Approve
demo**. Watch the same card move through installation, checking and Ready. The
scenario selector at the top is a review aid, not part of the proposed product.

Other scenarios show repair, optional updates, an unfinished check, active or
unknown package activity, unavailable safety records and interruption review.
Try Other actions, Details, light/dark themes and a narrow browser window. The
sidebar's secondary pages are explanatory placeholders, not redesigned screens.

All permissions, findings, report saving and progress are simulated. No native
commands, filesystem/report collection, networking, storage or SDE integration is
included. Acknowledgment demonstrates automatic summary generation but does not
make the paused scenario safe or initiate work. Reset stops only demo timers.

Design: [Overview: one clear next step](../OVERVIEW-NEXT-STEP-DESIGN.md).

Optional contributor verification, with the repository's existing frontend test
dependencies and Chromium installed:

```bash
node docs/overview-next-step-demo/verify.cjs
```

Set `DEMO_CHROMIUM` to an alternate Chromium executable if needed. These checks
exercise the prototype, not the production app or native safety implementation.
This is an owner-review artifact, not a candidate build, deployment or approval
to implement the application changes. No CI/release action is required to view it.

Local verification passed: 60 scenario/theme/viewport accessibility and reflow
cases (10 scenarios × two themes × 1280/640/390px), plus setup, simulated approval
cancellation, repair, update, acknowledgment, support and editor-placeholder flows.
No external requests or browser errors were observed. Chromium rendered the HTML
in memory because managed browser policy disallows local-file navigation; this
does not test a native application or a real package operation. Preview screenshots
were generated under `/tmp/sde-overview-demo` and are not application assets.
