# Actionable validation guidance (#6)

## Behavior

Validation lists failed checks first, followed by warnings, passes and information.
Every failed check has a plain-language problem, readiness impact and next step.
Original backend diagnostics are retained in a collapsed Technical details section.
PASS, WARNING, FAIL and INFORMATION labels and the original status counts remain.
Optional Git identity/authentication checks remain informational.

Guidance is derived from the existing Windows and Mint validation messages. Only
recognized missing-tool/setup checks offer Repair. Known runtime/command failures,
platform uncertainty, repository problems and maintenance scheduling issues direct
students to diagnostic review and self-service setup requirements. Unknown messages
get a neutral explanation and support-report fallback, not a servicing requirement.
No commands or repair diagnoses are inferred from arbitrary error text.

| Class | Examples | Suggested action |
| --- | --- | --- |
| Repair | Missing managed tool, Python venv/pip support, workspace or editor setup, standard extension, Windows development settings | Review the full Repair operation |
| Update | A passing tool check with matching, verified available-update metadata | Review the managed-tool Update operation |
| Manual step | Git defaults, File Explorer extensions, unverifiable editor customizations or desktop session | Review the specific setting/session and validate again |
| Diagnostic review | Runtime or command failure, unsupported/unverified platform, repository or schedule uncertainty, unknown failure | Review/preserve diagnostics without inferring a repair; Schedule navigation is available for maintenance checks |

Review Repair/Update selects the operation on Overview and explains its scope.
It does not invoke a native command. The student must explicitly start the chosen
operation, with the existing administrator approval flow when required. Repair
covers managed tools, workspace/editor configuration and weekly maintenance;
Update covers the managed development-tool set. These are broader workflows than
a single check. Review actions are disabled while an operation is active. View
Schedule is read-only navigation. Neither guidance nor validation changes pause
policy or the operating-system schedule.

Overview summaries no longer label every failure as needing Repair. Runtime and
unknown failures use Needs attention; missing-tool states require explicit
missing-tool diagnostics. Embedded diagnostic suffixes such as version not found
do not imply that a tool is absent. The generic failure result points to validation guidance.

## QA evidence

- Production TypeScript/Vite build and all 103 unit/model tests passed.
- The 42-check browser suite passed: the existing theme/zoom/accessibility tests
  plus four guidance scenarios covering both themes at 1040px and at 640px/150%.
- Fixture tests cover representative actual Windows/Mint messages, known manual
  steps, unavailable runtime families, unknown checks/extensions, unsupported
  platforms, matched update metadata, and preserved informational/warning states.
- Integration tests verify no native calls when reviewing Repair/Update, explicit
  starts, blocked actions during live work, and HTML-looking diagnostics displayed
  as text. Browser tests verify Schedule navigation, collapsed/expanded details,
  failed-first ordering, unchanged informational statuses, visible controls and
  explicit starts. Axe WCAG A/AA and horizontal-overflow checks passed.
- Normal and enlarged light/dark screenshots were visually reviewed. Local
  browser tests used system Chromium through a temporary launch configuration;
  operations in browser preview are simulated. Formatting and diff checks passed.

The recognition catalog is intentionally conservative. New backend message forms
need matching guidance/tests; until then, unknown checks retain diagnostic guidance.
No backend protocol, privileged operations, dependencies or release workflows change.

## Native UAT pending

Keep #6 open until the milestone test build is accepted on Windows 11/WebView2
and Linux Mint Cinnamon 22.x/WebKitGTK. Use a controlled test workstation or
existing known failures to verify:

1. Representative missing-tool/configuration, runtime, schedule, and manual-step
   cases explain the issue and next action accurately. Where an unknown failure
   is available, verify the safe fallback; otherwise record that native case as
   unexercised rather than claiming it passed.
2. Review buttons only select operations; their scope is clear and actual work
   starts only after an explicit choice. Confirm native administrator prompts and
   normal operation completion. Preserved settings/projects and schedule policy
   need actual workstation evidence.
3. Both themes and all zoom levels remain readable; keyboard focus, expandable
   diagnostics, status labels, and screen-reader reading order are understandable.
4. Optional Git identity/authentication stays informational, warnings stay warnings,
   and original diagnostics remain available without changing readiness counts.

Theme and zoom native UAT remains pending as documented separately. No release is
prepared or promoted by this change.
