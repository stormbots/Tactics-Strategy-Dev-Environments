# Part 1 implementation and verification contract

Scope: milestone 4, #11/#12/#30/#87/#90/#91. See the completion plan and UAT sheet.

## Data and operation boundaries

Initial validation requests no network tool inspection. Optional GitHub sign-in
checks run only when explicitly requesting update inspection during validation.
Application discovery has an independent 20-second total budget using the same
stable/canonical/semantic-version/official-asset selection policy as the protected
worker. It performs no staging or installation. A missing highest-version asset
fails honestly, without falling back to an older version as if the scan succeeded.

Managed-tool discovery consumes the installed versions from completed local
validation, with bounded schema/size/tool identifiers. The snapshot is advisory,
not authority for privileged changes. Fixed scripts query local APT metadata or
Chocolatey and vendor release metadata. They never refresh package indexes,
install, provision, change package ownership or remove locks. They do not take
the global operation gate while waiting for network metadata. Native query reads
can see changing metadata; their results are advisory and invalidated when an app
operation begins. Native mutation retains the existing exclusive operation gate.

The UI serializes each discovery type, retains a generation for tool snapshots,
and rejects results from before a mutating operation. A queued newer snapshot is
checked after the previous read-only request finishes. Native per-type guards
also prevent duplicate requests. Individual Chocolatey reads are bounded to 12
seconds, local metadata commands to 2 seconds, the JetBrains query to 8 seconds,
and the complete tool reader to 60 seconds. Fixed read-only helper output is
bounded to 128 KiB. These deadlines never terminate package installation work.

Only a canonical release tag and action kind cross the browser-opening boundary.
The native side constructs the official release/installer destination itself;
the webview cannot supply an arbitrary URL or command. Downloads require an
explicit click and are not described as authenticated until the existing pinned
verifier has checked the downloaded distribution.

Dismissal persists only the release tag. Discovery results are session-only;
restart/offline caching is Part 2 (#89). A failed check preserves the last
successful session timestamp without presenting that older result as current.

## Update preflight integration

The preview must finish preflight before confirmation. Known blockers prevent
Continue; unavailable/warning observations require acknowledgement. Error/Cancel
starts no operation. The backend independently runs preflight before elevation,
and the privileged helper runs it again before invoking the native Update script.
Operation gates and package-manager locks still provide final serialization;
preflight cannot eliminate every race or guarantee later downloads succeed.

Update reserves 3 GiB free on the system volume and 512 MiB on the user volume
for package staging/configuration. These conservative budgets are distinct from
fresh Install requirements and do not estimate the exact download size. Windows
checks installer/Chocolatey process state and known OS reboot markers. Linux
inspects actual kernel locks for fixed APT/dpkg lock files, dpkg audit output and
the standard reboot-required marker. An unreadable inspection is unavailable,
never a successful observation. Source HEAD probes cover representative package,
vendor and extension endpoints; a responding source is not a guarantee that every
package/CDN or custom configured mirror is reachable. Failed probes explain that
uncertainty. The broader #7 Install preflight remains separately open.

## Evidence ledger

Local checks and GitHub run/source links are recorded in the PR as they finish.
Do not infer desktop UAT, full release acceptance, signing, publication or stable
promotion from this document. Automated browser preview uses simulated data;
Windows Server/Mint userland upgrade tests establish native packaging and
preservation, not Windows 11/Cinnamon interaction or assistive-technology passes.

The ordinary source application version remains the baseline build identity;
the protected candidate recipe sets all application identity/lock inputs to
1.2.13 then 1.2.14 in disposable checkouts. The 1.2.13 package is an unpublished
same-source upgrade fixture, not a rebuild/replacement of the existing published
v1.2.13. Only new v1.2.14 candidate assets may be published by this option.
